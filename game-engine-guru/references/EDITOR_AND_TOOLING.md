# Editor and Tooling

The editor is a consumer of the engine, not a peer. Every editor feature that requires a special code path inside the runtime is a future bug. Treat the editor as an application that embeds the engine DLL through a narrow, stable C ABI.

## Table of Contents
- [Editor Architecture](#editor-architecture)
- [UI Frameworks](#ui-frameworks)
- [Property Inspector](#property-inspector)
- [Undo/Redo System](#undoredo-system)
- [Prefab System](#prefab-system)
- [Live Editing](#live-editing)
- [Gizmos & Viewport](#gizmos--viewport)
- [Python Tooling](#python-tooling)
- [See also](#see-also)

---

## Editor Architecture

**The editor is the top-layer consumer of the engine.** The engine is a shared library (engine.dll / libengine.so / engine.dylib); the editor links against a C ABI shim. This forces the runtime to be re-entrant, pure, and serializable — which is exactly what you want for ship builds, too.

```cpp
// engine_c_api.h — valid C11 and C++; exported implementations catch all C++
// exceptions and translate them to EngineStatus.
#include <stddef.h>
#include <stdint.h>

#if defined(_WIN32)
#  if defined(ENGINE_CORE_BUILD)
#    define ENGINE_API __declspec(dllexport)
#  else
#    define ENGINE_API __declspec(dllimport)
#  endif
#  define ENGINE_CALL __cdecl
#else
#  define ENGINE_API __attribute__((visibility("default")))
#  define ENGINE_CALL
#endif
#ifdef __cplusplus
extern "C" {
#endif

typedef struct EngineHandle EngineHandle;
typedef struct WorldHandle WorldHandle;
typedef uint32_t EngineStatus; // fixed-width ABI; constants, not a C enum
enum {
    ENGINE_API_VERSION = 1u,
    ENGINE_OK = 0u,
    ENGINE_INVALID_ARGUMENT = 1u,
    ENGINE_ABI_MISMATCH = 2u,
    ENGINE_INTERNAL_ERROR = 3u
};

typedef struct EngineConfig {
    uint32_t struct_size; // caller sets sizeof(EngineConfig)
    uint32_t api_version;
    uint32_t flags;
    uint32_t reserved;
} EngineConfig;

ENGINE_API EngineStatus ENGINE_CALL engine_create(
    const EngineConfig* config, EngineHandle** out_engine);
ENGINE_API EngineStatus ENGINE_CALL engine_destroy(EngineHandle* engine);
// UTF-8 bytes; name_length excludes any trailing NUL.
ENGINE_API EngineStatus ENGINE_CALL engine_create_world(
    EngineHandle* engine, const char* name, size_t name_length,
    WorldHandle** out_world);
ENGINE_API EngineStatus ENGINE_CALL world_tick(WorldHandle* world, float dt);

#ifdef __cplusplus
} // extern "C"
#endif
```

No `std::string`, references, templates, exceptions, compiler-dependent enums, RAII types, or virtual methods cross the boundary. Every out handle is set to null before work begins; destroy functions accept null; ownership is documented per function. Version and size every extensible struct, pin calling convention/export visibility, define string encoding and lengths, and test the public header with both a C and C++ compiler.

```cpp
// PSEUDOCODE implementation pattern. ENGINE_C_ABI_SHIM_EXCEPTIONS is fixed per
// shim binary; preprocessor removal keeps try/catch out of -fno-exceptions builds.
extern "C" ENGINE_API EngineStatus ENGINE_CALL
engine_create(const EngineConfig* config, EngineHandle** out_engine) noexcept {
    if (out_engine == nullptr) return ENGINE_INVALID_ARGUMENT;
    *out_engine = nullptr;
    if (config == nullptr || config->struct_size < sizeof(EngineConfig) ||
        config->api_version != ENGINE_API_VERSION)
        return ENGINE_ABI_MISMATCH;
#if ENGINE_C_ABI_SHIM_EXCEPTIONS
    try {
        return create_engine_internal(*config, *out_engine);
    } catch (...) {
        report_current_exception();
        *out_engine = nullptr;
        return ENGINE_INTERNAL_ERROR;
    }
#else
    static_assert(noexcept(create_engine_internal(*config, *out_engine)));
    return create_engine_internal(*config, *out_engine);
#endif
}
```

Compile an exception-enabled shim only when it must contain throwing third-party
boundaries. Otherwise keep the entire C ABI path `noexcept`; do not paste an
unconditional `try`/`catch` into an exceptions-disabled target.

**Language split:**
- Engine / runtime — C++23.
- Editor UI — C# (WPF/MAUI for Windows tooling) or Qt/C++ for cross-platform standalone editors.
- Scripting / batch — Python for pipeline, Lua/C# for gameplay.

**MVVM in C#:** ViewModels hold observable state (`INotifyPropertyChanged`), Views bind one-way or two-way. Model layer marshals to/from the engine C ABI. Never let the View touch the engine directly — when the engine refactors, only the Model layer breaks.

```csharp
public sealed class EntityViewModel : INotifyPropertyChanged {
    private readonly EngineBridge _bridge;
    private readonly EntityId     _id;

    private Vector3 _position;
    public Vector3 Position {
        get => _position;
        set {
            if (_position == value) return;
            _bridge.SetPosition(_id, value);  // may fail; local state is unchanged
            _position = value;
            OnPropertyChanged();
        }
    }

    public event PropertyChangedEventHandler? PropertyChanged;
    private void OnPropertyChanged([CallerMemberName] string? n = null)
        => PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(n));
}
```

---

## UI Frameworks

Three tiers, pick per-task:

| Tier                | Framework       | Use                                                    |
|---------------------|-----------------|--------------------------------------------------------|
| In-engine overlay   | **Dear ImGui**  | Debug HUDs, profiler, console, programmer tools        |
| Embedded editor     | **ImGui / Qt**  | DCC-integrated plugins, engine tool tabs               |
| Standalone editor   | **Qt / WPF**    | Main editor app, asset browsers, dedicated tools       |

**ImGui** — immediate mode, zero persistent state, 15 min to add a new panel. The entire UI redraws per frame; cost is ~1ms even for complex layouts. This is the right answer for 80% of tools that ship to developers. Bind with `ImGui::Begin`, make widgets, `ImGui::End`. Do not try to build a retained scene graph on top.

**Qt** — the standard for heavy cross-platform C++ tooling: CryEngine 5.x's Sandbox, O3DE, and many in-house DCC-adjacent tools. Heavy, industrial, correct. Picks up accessibility, localization, and docking for free. QML for styling, C++ for logic. License carefully (LGPL/commercial obligations). (Accuracy note: Frostbite's FrostEd is WPF/.NET and Unreal's editor was wxWidgets historically, Slate today — neither is Qt; don't cite them as Qt precedent.)

**WPF / MAUI** — Windows-only but mature; MAUI opens macOS/Linux if you need it. XAML + MVVM is productive for data-heavy editors (asset browsers, sequencers, state machine editors).

**Hard rule:** never cross streams. Don't embed ImGui windows in Qt, don't render WPF into the engine's swapchain. When you need data out of the engine, it crosses the C ABI.

---

## Property Inspector

Auto-generated property UIs are worth a month of engine engineer time. Hand-written inspectors rot.

**Reflection via `ComponentTraits`:** every reflected type publishes compile-time metadata, either via a code-gen step (until C++26 static reflection lands) or a macro:

```cpp
struct Transform {
    Vec3 position;
    Quat rotation;
    Vec3 scale;
};

template<> struct ComponentTraits<Transform> {
    static constexpr std::string_view name = "Transform";
    static constexpr auto fields = std::tuple{
        Field{"position", &Transform::position, Attr::Range{-10000.f, 10000.f}},
        Field{"rotation", &Transform::rotation},
        Field{"scale",    &Transform::scale,    Attr::Range{0.001f, 1000.f},
                                                Attr::Tooltip{"Non-uniform allowed"}},
    };
};
```

The editor walks `fields`, dispatches on field type → widget:
- `float`  → drag float, optional range.
- `Vec3`   → three drag floats.
- `Color`  → color picker (RGBA float or LDR/HDR mode).
- `Handle<Texture2D>` → asset picker, thumbnail drag target.
- `enum`   → combo box.
- `std::vector<T>` → collapsible list, per-element recursion.

**Attributes drive customization:** `Range`, `Tooltip`, `Category("Lighting")`, `EditCondition("bCastShadows")`, `HideInInspector`. Pile them into the `Field` variadic. The editor's inspector is a single `inspect(void* obj, const ComponentTraits& t)` function.

**Custom editors per type:** register a `IPropertyDrawer` for types that need it (Curve, Gradient, AnimationClip). Falls through to auto-drawer otherwise.

---

## Undo/Redo System

Command pattern, two stacks, serializable commands. This is non-negotiable for any editor your team will use for more than a week.

```cpp
// PSEUDOCODE — UNDO/REDO: FallibleHistory is fixed-capacity or explicitly
// fallible; reserve_one() never mutates command state.
class ICommand {
public:
    virtual ~ICommand() = default;
    virtual std::expected<void, EditError> execute() = 0;
    virtual std::expected<void, EditError> undo()    = 0;
    virtual std::string_view name() const = 0;
    virtual void serialize(BinaryWriter&) const = 0;   // for collab
};

class UndoStack {
    FallibleHistory<std::unique_ptr<ICommand>> undo_;
    FallibleHistory<std::unique_ptr<ICommand>> redo_;
public:
    std::expected<void, EditError> push(std::unique_ptr<ICommand> cmd) {
        if (!cmd) return std::unexpected(EditError::InvalidCommand);
        if (!undo_.reserve_one()) return std::unexpected(EditError::HistoryFull);
        if (auto r = cmd->execute(); !r) return r;
        redo_.clear();
        undo_.push_reserved(std::move(cmd));
        return {};
    }
    std::expected<void, EditError> undo() {
        if (undo_.empty()) return std::unexpected(EditError::EmptyHistory);
        if (!redo_.reserve_one()) return std::unexpected(EditError::HistoryFull);
        auto& cmd = undo_.back();
        if (auto r = cmd->undo(); !r) return r; // stacks unchanged on failure
        redo_.push_reserved(std::move(cmd));
        undo_.pop_back();
        return {};
    }
    std::expected<void, EditError> redo() {
        if (redo_.empty()) return std::unexpected(EditError::EmptyHistory);
        if (!undo_.reserve_one()) return std::unexpected(EditError::HistoryFull);
        auto& cmd = redo_.back();
        if (auto r = cmd->execute(); !r) return r;
        undo_.push_reserved(std::move(cmd));
        redo_.pop_back();
        return {};
    }
};
```

**Transaction grouping:** drag operations generate hundreds of incremental commands; wrap them in a `CompoundCommand`. Its `execute()` applies children in order and, on failure, undoes already-applied children in reverse. Its `undo()` reverses children and, on failure, re-executes those already undone. If compensation itself fails, poison the history, stop accepting edits, and reload the last consistent snapshot—do not pretend the transaction was atomic. Start on mouse down, commit one command on mouse up, and discard a no-op transaction.

```cpp
// PSEUDOCODE — TRANSACTIONAL UNDO/REDO: compensation failure poisons history.
expected<void, EditError> CompoundCommand::execute() {
    size_t applied = 0;
    for (; applied < children.size(); ++applied) {
        if (auto r = children[applied]->execute(); !r) {
            while (applied != 0)
                if (auto rollback = children[--applied]->undo(); !rollback)
                    return unexpected(EditError::HistoryPoisoned);
            return unexpected(r.error());
        }
    }
    return {};
}

expected<void, EditError> CompoundCommand::undo() {
    size_t remaining = children.size();
    while (remaining != 0) {
        if (auto r = children[remaining - 1]->undo(); !r) {
            for (size_t i = remaining; i < children.size(); ++i)
                if (auto restore = children[i]->execute(); !restore)
                    return unexpected(EditError::HistoryPoisoned);
            return unexpected(r.error());
        }
        --remaining;
    }
    return {};
}
```

**Serializable commands** are the foundation of collaborative editing — stream the command bytes to other clients, they replay deterministically. Google Docs for level design. Requires: every command references entities by stable GUID, not pointer.

---

## Prefab System

Prefabs are **templates with instance overrides**. A prefab is a reusable sub-hierarchy; an instance is that hierarchy stamped into a world with a delta layer of overrides.

```
Prefab "Lamppost"
  ├── Entity "Root"     (Transform)
  ├── Entity "Pole"     (StaticMeshRenderer, MaterialRef: Metal_Brushed)
  └── Entity "Bulb"     (PointLight, color=(1,0.8,0.5), intensity=800)

Instance in World:
  PrefabRef: Lamppost (v3)
  Overrides:
    - Root.Transform.position = (x,y,z)   // unique per instance
    - Bulb.PointLight.intensity = 400     // this lamp is dimmer
```

**Override storage is a delta:** list of `(stable_node_guid, stable_component_type_id, stable_field_id, value)` tuples. Display names and hierarchy paths are metadata, not identity: renaming or reparenting an entity must not orphan overrides. Everything not overridden follows the template.

**Nested prefabs:** prefab A contains prefab B. Changes to B propagate to A and to all instances of A. Enforce depth limit (typical: 8) to catch infinite recursion authored by accident.

**JSON serialization** with explicit version field:

```json
{
  "$schema_version": 3,
  "prefab_ref": "guid:7a2c-...",
  "overrides": [
    { "node": "guid:root-...", "component": "transform/v1", "field": "position", "value": [10, 0, 5] },
    { "node": "guid:bulb-...", "component": "point-light/v2", "field": "intensity_lm", "value": 400 }
  ]
}
```

Write a deterministic `vN -> vN+1` migration for each bump. Preserve unknown fields, migrate a copy, validate stable IDs and value types, then atomically publish the new document; retain the original on any error. Never key migrations on localized/display names and never delete a migration—old saves outlive your patience.

```cpp
// PSEUDOCODE — PREFAB MIGRATION: JSON/value API abbreviated.
expected<Document, MigrationError> migrate(Document input) {
    while (input.version < kCurrentVersion) {
        auto step = migration_for(input.version);
        if (!step) return unexpected(MigrationError::UnsupportedVersion);
        auto next = step(input);              // must not mutate input on failure
        if (!next || next->version != input.version + 1)
            return unexpected(MigrationError::InvalidStep);
        input = std::move(*next);
    }
    if (!validate_prefab(input)) return unexpected(MigrationError::InvalidDocument);
    return input; // caller writes temp + fsync + atomic rename
}
```

---

## Live Editing

Safe mutation points: **between system ticks**, never mid-tick. The editor queues mutations to a per-frame command buffer, the runtime drains at the barrier.

```cpp
void World::tick(float dt) noexcept {
    // Structural-change barrier 1: before systems
    drain_editor_commands();
    
    for (auto& system : systems_) system.update(*this, dt);
    
    // Structural-change barrier 2: after systems
    drain_editor_commands();
}
```

**ECS structural changes** (entity create/destroy, component add/remove) reshape archetype memory. Running them concurrent with a system iterating that archetype is undefined behavior. Deferred command buffers are the solution — every AAA ECS (Flecs, EnTT's group mode, Unity DOTS) does this.

**Hot-reload via immutable publication and deferred retirement:**
1. On asset change, editor cooks the new payload.
2. Runtime receives manifest `{asset_guid, new_payload_ref}`.
3. Load and validate an immutable replacement without touching the live slot.
4. At the next barrier, atomically publish the new version for the GUID. Readers acquire one version for the entire job; they never reload the slot mid-job.
5. Retire the old CPU version after all reader references/epochs drain. Retire its GPU resources only after the last submitted fence that can reference them completes.
6. If load, validation, state migration, or publication fails, keep the old version live and report the error.

```cpp
// PSEUDOCODE — HOT-RELOAD PUBLICATION/RETIREMENT: queue APIs are abbreviated.
struct AssetSlot {
    std::atomic<std::shared_ptr<const AssetVersion>> current;
};

auto acquire(const AssetSlot& slot) {
    return slot.current.load(std::memory_order_acquire);
}

void publish(AssetSlot& slot, std::shared_ptr<const AssetVersion> replacement,
             GpuRetirementQueue& retire) {
    auto old = slot.current.exchange(std::move(replacement),
                                     std::memory_order_acq_rel);
    retire.after_last_use_fence(std::move(old)); // queue also holds CPU lifetime
}
```

For code hot-reload (gameplay DLL), unload → recompile → reload, restore state via serialization boundary. Live++ or a home-grown equivalent for native code; C# AssemblyLoadContext for managed. Not free — architect the code/data boundary so runtime state lives in data and code is pure behavior.

---

## Gizmos & Viewport

**ImGuizmo** is the default for translate/rotate/scale handles — Cedric Guillemet's library, battle-tested, trivially embeddable. Gizmo modes: local vs. world, screen-aligned vs. axis-aligned, snap on/off.

**Snap configuration:**
- Translate snap: 0.01, 0.1, 0.5, 1.0, 5.0 m (configurable).
- Rotate snap: 1°, 5°, 15°, 45°, 90°.
- Scale snap: 0.1x steps or power-of-2.
- Hold Ctrl to temporarily toggle snap.

**Camera controls:**
- Maya-style: Alt + LMB orbit, Alt + MMB pan, Alt + RMB dolly, F to frame selection.
- UE-style: RMB-hold for fly mode, WASD + QE, scroll for speed, Shift for sprint.
- Support both — bind in a profile file, let users pick.

**Selection:**
- Click: single-pick via GPU ID buffer (render entity IDs to R32_UINT target, read pixel under cursor).
- Marquee: frustum cull against selection rectangle.
- Shift-click: add to set. Ctrl-click: toggle. Alt-click: subtract.
- Outline in post-process: Jump Flood Algorithm for crisp 1-2 pixel stroke.

**Multi-viewport:** 4-pane (top / front / side / perspective) is expected for level design. Orthographic views share camera target; perspective has its own. Each viewport is a full render pipeline with its own swapchain / offscreen target — budget 4x GPU cost, use lower-res for non-focused.

---

## Python Tooling

Python is the glue. Every content team has Python users already. Use it.

**Pipeline scripts:**
```python
# cook_level.py — invoked by CI or designer
from engine_tools import Cooker, DDC, TargetPlatform

def cook_level(level_guid: str, platforms: list[TargetPlatform]) -> int:
    ddc = DDC.open("//depot/ddc")
    cooker = Cooker(ddc)
    for p in platforms:
        result = cooker.cook_asset(level_guid, p)
        if not result.ok:
            print(f"FAIL {p}: {result.error}", file=sys.stderr)
            return 1
    return 0
```

**Batch processing:** resize all textures tagged `UI` to 1024 max, regenerate all character LODs with new quality settings, re-bake lightmaps on a specific sub-level. Python orchestrates, C++ does the work.

**CI/CD automation:** build promotion, test result aggregation, Slack/Teams notifications, P4/Git tagging. Python + `subprocess` + REST is enough; don't bring in Bazel unless you're Google.

**Code generation:** reflection tables (pre-C++26), network serialization boilerplate (RPC descriptors), component registration. A Python pass over parsed headers (via libclang) emits `.generated.cpp` files that the build compiles. This replaces UnrealHeaderTool for bespoke engines. Once C++26 static reflection lands in ship toolchains, delete these generators — until then, they're mandatory.

```python
# PSEUDOCODE emission core; AST discovery/annotation policy is omitted.
import clang.cindex
import json
import os
from pathlib import Path
import tempfile

def qualified_name(cursor: clang.cindex.Cursor) -> str:
    parts: list[str] = []
    while cursor and cursor.kind != clang.cindex.CursorKind.TRANSLATION_UNIT:
        if cursor.spelling:
            parts.append(cursor.spelling)
        cursor = cursor.semantic_parent
    return "::".join(reversed(parts))

def emit_traits(classes: list[clang.cindex.Cursor], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(dir=out.parent, prefix=out.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write("// generated; do not edit\n#pragma once\n")
            f.write("#include <string_view>\n#include <tuple>\n")
            for cls in sorted(classes, key=qualified_name):
                qname = qualified_name(cls)
                if not qname:
                    raise ValueError("reflected class has no qualified name")
                f.write(f"template<> struct ComponentTraits<{qname}> {{\n")
                f.write(f"  static constexpr std::string_view name = {json.dumps(qname)};\n")
                f.write("  static constexpr auto fields = std::tuple{\n")
                seen: set[str] = set()
                for field in cls.get_children():
                    if field.kind != clang.cindex.CursorKind.FIELD_DECL:
                        continue
                    if field.is_bitfield():
                        raise ValueError(f"bit-field is not reflectable: {qname}::{field.spelling}")
                    if field.spelling in seen:
                        raise ValueError(f"duplicate reflected field: {qname}::{field.spelling}")
                    seen.add(field.spelling)
                    f.write(f"    Field{{{json.dumps(field.spelling)}, "
                            f"&{qname}::{field.spelling}}},\n")
                f.write("  };\n};\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_name, out)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise
```

The omitted discovery pass must fail on libclang diagnostics, select only explicitly reflected definitions from project headers, reject private/inaccessible or anonymous members, deduplicate canonical declarations/USRs, and list every parsed header plus the generator binary/version as build dependencies. Generate one file once and replace it atomically; never reopen the same output with `"w"` for each class.

---

## See also

- `ASSET_PIPELINE_AND_COOKER.md` — hot-reload pipeline, DDC, cook orchestration that the editor drives.
- `TESTING_ERROR_HANDLING_AND_BUILD.md` — `std::expected` patterns used across the C ABI, editor integration tests.
- `CPP23_26_AND_MODERN_PATTERNS.md` — reflection strategy (codegen today, static reflection horizon), Handle<Tag> for editor-runtime object identity.
