// -----------------------------------------------------------------------------
// editor_bridge_template.cs
//
// C# 12 / .NET 8 scaffold for the editor-side bridge into the native engine.
// Responsibilities:
//   * P/Invoke into the engine's C ABI (engine_core.dll / libengine_core.so).
//   * SafeHandle-wrapped owning World lifetime; EntityId is a non-owning value.
//   * MVVM primitives (ViewModelBase, RelayCommand) for the editor shell.
//   * Undo/Redo command stack driving native edits.
//   * Reflection-driven PropertyInspector that emits per-type editor widgets.
//
// Project requirements (this file is intentionally not a project scaffold):
//   <TargetFramework>net8.0</TargetFramework>
//   <LangVersion>12.0</LangVersion>
//   <Nullable>enable</Nullable>
//   <AllowUnsafeBlocks>true</AllowUnsafeBlocks>
// LibraryImport uses the .NET SDK's built-in source generator; no NuGet package
// or WPF project is required for the ICommand interface used below.
//
// Design rules:
//   * Never marshal exceptions across the C ABI. Native errors are surfaced as
//     EngineError codes translated to EngineException on the managed side.
//   * SafeHandle guarantees a constrained-execution release attempt during finalization.
//   * No static mutable state; the editor wires a single EngineSession per window.
// -----------------------------------------------------------------------------

using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Diagnostics.CodeAnalysis;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Windows.Input;

namespace Engine.Editor.Bridge;

// =============================================================================
// 1. Native error codes (mirror of engine::core::EngineError).
// =============================================================================

public enum EngineError : uint
{
    Ok                   = 0,
    OutOfMemory          = 1,
    InvalidHandle        = 2,
    InvalidArgument      = 3,
    InvalidState         = 4,
    AlreadyInitialized   = 5,
    NotInitialized       = 6,
    IoError              = 7,
    UnsupportedPlatform  = 8,
    Unknown              = 0xFFFFFFFFu
}

public sealed class EngineException : Exception
{
    public EngineError Code { get; }
    public EngineException(EngineError code, string message) : base(message) => Code = code;

    internal static void ThrowIfError(EngineError code, string context)
    {
        if (code != EngineError.Ok)
            throw new EngineException(code, $"{context} failed: {code}");
    }
}

// =============================================================================
// 2. P/Invoke surface. The C ABI lives in `engine_core` and is plain C.
//    Keep signatures small and stable; version-bump the DLL on ABI change.
// =============================================================================

internal static partial class NativeMethods
{
    private const string Lib = "engine_core";

    /// <summary>Creates a new ECS world. Out handle is owned by caller.</summary>
    [LibraryImport(Lib, EntryPoint = "engine_world_create")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(System.Runtime.CompilerServices.CallConvCdecl) })]
    internal static partial EngineError engine_world_create(out IntPtr outWorld);

    /// <summary>Destroys a world handle. Safe to call with IntPtr.Zero (no-op).</summary>
    [LibraryImport(Lib, EntryPoint = "engine_world_destroy")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(System.Runtime.CompilerServices.CallConvCdecl) })]
    internal static partial EngineError engine_world_destroy(IntPtr world);

    /// <summary>Spawns an entity in the world and returns its opaque 64-bit id.</summary>
    [LibraryImport(Lib, EntryPoint = "engine_entity_spawn")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(System.Runtime.CompilerServices.CallConvCdecl) })]
    internal static partial EngineError engine_entity_spawn(WorldHandle world, out ulong outEntityId);

    /// <summary>Copies `byteCount` bytes from `data` into the component of type `componentTypeId`
    /// on the entity. Component must exist; use engine_component_add first if not.</summary>
    [LibraryImport(Lib, EntryPoint = "engine_component_set")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(System.Runtime.CompilerServices.CallConvCdecl) })]
    internal static unsafe partial EngineError engine_component_set(
        WorldHandle world,
        ulong entityId,
        uint componentTypeId,
        void* data,
        nuint byteCount);

    /// <summary>Returns the native ABI contract for one generated component type.</summary>
    [LibraryImport(Lib, EntryPoint = "engine_component_get_abi")]
    [UnmanagedCallConv(CallConvs = new[] { typeof(System.Runtime.CompilerServices.CallConvCdecl) })]
    internal static partial EngineError engine_component_get_abi(
        uint componentTypeId,
        out NativeComponentAbi outAbi);
}

[StructLayout(LayoutKind.Sequential, Pack = 8)]
internal struct NativeComponentAbi
{
    internal uint ComponentTypeId;
    internal uint AbiVersion;
    internal nuint Size;
    internal nuint Alignment;
    internal ulong LayoutHash;
}

// =============================================================================
// 3. SafeHandle wrappers. Guarantee release of native resources.
// =============================================================================

/// <summary>RAII wrapper for an engine World handle.</summary>
public sealed class WorldHandle : SafeHandle
{
    private WorldHandle() : base(IntPtr.Zero, ownsHandle: true) { }

    public override bool IsInvalid =>
        handle == IntPtr.Zero || handle == new IntPtr(-1);

    public static WorldHandle Create()
    {
        var err = NativeMethods.engine_world_create(out var raw);
        if (err != EngineError.Ok)
        {
            if (raw != IntPtr.Zero && raw != new IntPtr(-1))
                _ = NativeMethods.engine_world_destroy(raw);
            EngineException.ThrowIfError(err, nameof(NativeMethods.engine_world_create));
        }
        if (raw == IntPtr.Zero || raw == new IntPtr(-1))
            throw new EngineException(
                EngineError.InvalidHandle,
                "engine_world_create returned success with an invalid handle");
        var h = new WorldHandle();
        h.SetHandle(raw);
        return h;
    }

    protected override bool ReleaseHandle()
    {
        // ReleaseHandle runs on the finalizer thread; never throw.
        if (IsInvalid) return true;
        return NativeMethods.engine_world_destroy(handle) == EngineError.Ok;
    }
}

/// <summary>Value-type wrapper for an entity id. Entities do not own native memory
/// directly; the owning World's handle controls their lifetime.</summary>
public readonly record struct EntityId(ulong Value)
{
    public static EntityId Invalid => new(0UL);
    public bool IsValid => Value != 0UL;
}

// =============================================================================
// 4. MVVM: ViewModelBase + RelayCommand.
// =============================================================================

public abstract class ViewModelBase : INotifyPropertyChanged
{
    public event PropertyChangedEventHandler? PropertyChanged;

    /// <summary>Raises PropertyChanged. Callers pass [CallerMemberName] or a literal.</summary>
    protected void OnPropertyChanged([CallerMemberName] string? propertyName = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));

    /// <summary>Assigns field and raises PropertyChanged only on change.</summary>
    protected bool SetField<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value)) return false;
        field = value;
        OnPropertyChanged(propertyName);
        return true;
    }
}

public sealed class RelayCommand : ICommand
{
    private readonly Action<object?> _execute;
    private readonly Predicate<object?>? _canExecute;

    public RelayCommand(Action<object?> execute, Predicate<object?>? canExecute = null)
    {
        _execute    = execute ?? throw new ArgumentNullException(nameof(execute));
        _canExecute = canExecute;
    }

    public event EventHandler? CanExecuteChanged;
    public bool CanExecute(object? parameter) => _canExecute?.Invoke(parameter) ?? true;
    public void Execute(object? parameter)    => _execute(parameter);

    /// <summary>Fire this when the underlying predicate's inputs change.</summary>
    public void RaiseCanExecuteChanged() => CanExecuteChanged?.Invoke(this, EventArgs.Empty);
}

// =============================================================================
// 5. Undo / Redo command pattern. Commands are domain-specific edits that are
//    reversible; Execute() applies, Undo() reverses. Kept separate from ICommand
//    (WPF binding) to avoid conflating UI invocation with editable history.
// =============================================================================

public interface IEditorCommand
{
    string Description { get; }
    void Execute();
    void Undo();
}

public sealed class UndoRedoStack
{
    private readonly Stack<IEditorCommand> _undo = new();
    private readonly Stack<IEditorCommand> _redo = new();

    public event EventHandler? HistoryChanged;

    public bool CanUndo => _undo.Count > 0;
    public bool CanRedo => _redo.Count > 0;

    /// <summary>Executes the command and pushes it onto the undo stack.
    /// Clears the redo stack (standard linear-history semantics).</summary>
    public void Execute(IEditorCommand cmd)
    {
        ArgumentNullException.ThrowIfNull(cmd);
        cmd.Execute();
        _undo.Push(cmd);
        _redo.Clear();
        HistoryChanged?.Invoke(this, EventArgs.Empty);
    }

    public void Undo()
    {
        if (!_undo.TryPeek(out var cmd)) return;
        cmd.Undo();
        _undo.Pop();
        _redo.Push(cmd);
        HistoryChanged?.Invoke(this, EventArgs.Empty);
    }

    public void Redo()
    {
        if (!_redo.TryPeek(out var cmd)) return;
        cmd.Execute();
        _redo.Pop();
        _undo.Push(cmd);
        HistoryChanged?.Invoke(this, EventArgs.Empty);
    }

    public void Clear()
    {
        _undo.Clear();
        _redo.Clear();
        HistoryChanged?.Invoke(this, EventArgs.Empty);
    }
}

// =============================================================================
// 6. Reflection-driven PropertyInspector.
//    Walks a target's public instance properties, classifies them, and emits
//    editor descriptors that the UI layer (WPF/Avalonia/ImGui) turns into
//    concrete widgets.
// =============================================================================

public enum EditorWidgetKind { Text, Number, Checkbox, Color, Vector3, Enum, AssetRef, Nested }

public sealed record PropertyDescriptor(
    string Name,
    Type Type,
    EditorWidgetKind Widget,
    Func<object?> Getter,
    Action<object?> Setter,
    bool ReadOnly);

/// <summary>Decorate properties to control inspector behavior.</summary>
[AttributeUsage(AttributeTargets.Property)]
public sealed class InspectorAttribute : Attribute
{
    public string? DisplayName { get; init; }
    public bool Hidden { get; init; }
    public bool ReadOnly { get; init; }
}

public static class PropertyInspector
{
    /// <summary>Reflects over `target` and returns a descriptor per editable property.</summary>
    public static IReadOnlyList<PropertyDescriptor> Inspect(object target)
    {
        ArgumentNullException.ThrowIfNull(target);

        var type  = target.GetType();
        var props = type.GetProperties(BindingFlags.Public | BindingFlags.Instance);
        var list  = new List<PropertyDescriptor>(props.Length);

        foreach (var p in props)
        {
            var attr = p.GetCustomAttribute<InspectorAttribute>();
            if (attr?.Hidden == true) continue;
            if (p.GetIndexParameters().Length > 0) continue; // skip indexers
            if (p.GetMethod?.IsPublic != true) continue;     // require a readable public property

            var readOnly = attr?.ReadOnly == true || p.SetMethod?.IsPublic != true;
            var widget   = ClassifyWidget(p.PropertyType);
            var name     = attr?.DisplayName ?? p.Name;

            list.Add(new PropertyDescriptor(
                Name: name,
                Type: p.PropertyType,
                Widget: widget,
                Getter: () => p.GetValue(target),
                Setter: v =>
                {
                    if (readOnly)
                        throw new InvalidOperationException($"{type.Name}.{p.Name} is read-only");
                    if (v is null && p.PropertyType.IsValueType &&
                        Nullable.GetUnderlyingType(p.PropertyType) is null)
                        throw new ArgumentException($"{p.Name} does not accept null", nameof(v));
                    if (v is not null && !p.PropertyType.IsInstanceOfType(v))
                        throw new ArgumentException(
                            $"{p.Name} requires {p.PropertyType.FullName}", nameof(v));
                    p.SetValue(target, v);
                },
                ReadOnly: readOnly));
        }

        return list;
    }

    private static EditorWidgetKind ClassifyWidget(Type t)
    {
        if (t == typeof(bool))   return EditorWidgetKind.Checkbox;
        if (t == typeof(string)) return EditorWidgetKind.Text;
        if (t.IsEnum)            return EditorWidgetKind.Enum;
        if (IsNumeric(t))        return EditorWidgetKind.Number;
        if (t.Name is "Vector3" or "Vec3" or "Float3") return EditorWidgetKind.Vector3;
        if (t.Name is "Color"   or "LinearColor")       return EditorWidgetKind.Color;
        if (typeof(IAssetReference).IsAssignableFrom(t)) return EditorWidgetKind.AssetRef;
        return EditorWidgetKind.Nested;
    }

    private static bool IsNumeric(Type t) =>
        t == typeof(byte)   || t == typeof(sbyte)  ||
        t == typeof(short)  || t == typeof(ushort) ||
        t == typeof(int)    || t == typeof(uint)   ||
        t == typeof(long)   || t == typeof(ulong)  ||
        t == typeof(float)  || t == typeof(double) ||
        t == typeof(decimal);
}

/// <summary>Marker interface so the inspector can recognize asset-reference types.</summary>
public interface IAssetReference
{
    Guid AssetGuid { get; }
}

// =============================================================================
// 7. Example session tying it all together.
// =============================================================================

public sealed class EngineSession : IDisposable
{
    public WorldHandle World { get; }
    public UndoRedoStack History { get; } = new();

    public EngineSession() { World = WorldHandle.Create(); }

    public EntityId Spawn()
    {
        ObjectDisposedException.ThrowIf(World.IsClosed, World);
        var err = NativeMethods.engine_entity_spawn(World, out var id);
        EngineException.ThrowIfError(err, nameof(NativeMethods.engine_entity_spawn));
        if (id == 0)
            throw new EngineException(
                EngineError.InvalidHandle,
                "engine_entity_spawn returned success with a null entity id");
        return new EntityId(id);
    }

    public unsafe void SetComponent<T>(EntityId entity, uint componentTypeId, in T data)
        where T : unmanaged
    {
        ObjectDisposedException.ThrowIf(World.IsClosed, World);
        if (World.IsInvalid)
            throw new InvalidOperationException("World handle is invalid");
        if (!entity.IsValid)
            throw new ArgumentException("Entity id must be nonzero", nameof(entity));
        if (componentTypeId == 0)
            throw new ArgumentOutOfRangeException(nameof(componentTypeId));

        ComponentAbi<T>.Validate(componentTypeId);
        T copy = data;
        var err = NativeMethods.engine_component_set(
            World, entity.Value, componentTypeId, &copy, (nuint)sizeof(T));
        EngineException.ThrowIfError(err, nameof(NativeMethods.engine_component_set));
    }

    public void Dispose() => World.Dispose();
}

[AttributeUsage(AttributeTargets.Struct, AllowMultiple = false, Inherited = false)]
public sealed class EngineComponentAbiAttribute(
    uint componentTypeId,
    int nativeSize,
    int nativeAlignment,
    uint abiVersion,
    ulong layoutHash) : Attribute
{
    public uint ComponentTypeId { get; } = componentTypeId;
    public int NativeSize { get; } = nativeSize;
    public int NativeAlignment { get; } = nativeAlignment;
    public uint AbiVersion { get; } = abiVersion;
    public ulong LayoutHash { get; } = layoutHash;
}

internal static class ComponentAbi<T> where T : unmanaged
{
    internal static void Validate(uint componentTypeId)
    {
        var abi = typeof(T).GetCustomAttribute<EngineComponentAbiAttribute>()
            ?? throw new InvalidOperationException(
                $"{typeof(T).FullName} must declare EngineComponentAbiAttribute");
        var structLayout = typeof(T).StructLayoutAttribute;
        var layout = structLayout?.Value ?? LayoutKind.Auto;
        if (layout is not (LayoutKind.Sequential or LayoutKind.Explicit) ||
            structLayout is null || structLayout.Pack == 0)
            throw new InvalidOperationException(
                $"{typeof(T).FullName} must declare StructLayout with an explicit Pack");
        if (abi.ComponentTypeId != componentTypeId)
            throw new InvalidOperationException(
                $"{typeof(T).FullName} component type id does not match the native call");

        var err = NativeMethods.engine_component_get_abi(componentTypeId, out var native);
        EngineException.ThrowIfError(err, nameof(NativeMethods.engine_component_get_abi));
        if (abi.AbiVersion == 0 || abi.LayoutHash == 0 ||
            native.ComponentTypeId != abi.ComponentTypeId ||
            native.AbiVersion != abi.AbiVersion ||
            native.Size != (nuint)abi.NativeSize ||
            native.Alignment != (nuint)abi.NativeAlignment ||
            native.LayoutHash != abi.LayoutHash ||
            abi.NativeSize != Unsafe.SizeOf<T>() ||
            Marshal.SizeOf<T>() != Unsafe.SizeOf<T>())
            throw new InvalidOperationException(
                $"{typeof(T).FullName} has incompatible native ABI metadata");
    }
}
