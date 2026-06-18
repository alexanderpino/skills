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
// engine_c_api.h — stable across editor/runtime, C linkage, no exceptions
extern "C" {
    typedef struct EngineHandle EngineHandle;
    typedef struct WorldHandle  WorldHandle;

    // Returns nullptr on failure, error in out-param.
    EngineHandle* engine_create(const EngineConfig* cfg, EngineError* err);
    void          engine_destroy(EngineHandle*);

    WorldHandle*  engine_create_world(EngineHandle*, const char* name);
    int32_t       world_tick(WorldHandle*, float dt);   // 0 = ok, <0 = error code
}
```

No `std::string` across the boundary, no RAII types, no virtual methods. POD and opaque pointers only. This is Frostbite, id Tech, and RE Engine orthodoxy — and it's why those editors can be rewritten without touching the engine.

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
            _position = value;
            _bridge.SetPosition(_id, value);  // marshalled to C ABI
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
class ICommand {
public:
    virtual ~ICommand() = default;
    virtual std::expected<void, EditError> execute() = 0;
    virtual std::expected<void, EditError> undo()    = 0;
    virtual std::string_view name() const = 0;
    virtual void serialize(BinaryWriter&) const = 0;   // for collab
};

class UndoStack {
    std::vector<std::unique_ptr<ICommand>> undo_;
    std::vector<std::unique_ptr<ICommand>> redo_;
public:
    std::expected<void, EditError> push(std::unique_ptr<ICommand> cmd) {
        auto r = cmd->execute();
        if (!r) return r;
        redo_.clear();                    // branching invalidates redo
        undo_.push_back(std::move(cmd));
        return {};
    }
    std::expected<void, EditError> undo();
    std::expected<void, EditError> redo();
};
```

**Transaction grouping:** drag operations generate hundreds of incremental commands; wrap them in a `CompoundCommand` that executes/undoes atomically. Start the transaction on mouse down, commit on mouse up.

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

**Override storage is a delta:** list of `(entity_path, field_path, value)` tuples. Everything not overridden follows the template. When the template changes, non-overridden fields update automatically — this is the whole point.

**Nested prefabs:** prefab A contains prefab B. Changes to B propagate to A and to all instances of A. Enforce depth limit (typical: 8) to catch infinite recursion authored by accident.

**JSON serialization** with explicit version field:

```json
{
  "$schema_version": 3,
  "prefab_ref": "guid:7a2c-...",
  "overrides": [
    { "path": "Root/Transform.position", "value": [10, 0, 5] },
    { "path": "Bulb/PointLight.intensity", "value": 400 }
  ]
}
```

Write a migration per schema version bump; run on load. Never delete a migration — old saves outlive your patience.

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

**Hot-reload via snapshot+diff:**
1. On asset change, editor cooks the new payload.
2. Runtime receives manifest `{asset_guid, new_payload_ref}`.
3. At the next barrier, runtime serializes current state referencing the asset, swaps the asset pointer, deserializes.
4. Handles keyed on GUID see the new data seamlessly.

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
# gen_reflection.py — run as a CMake custom command pre-build
import clang.cindex
from pathlib import Path

def emit_traits(cls: clang.cindex.Cursor, out: Path) -> None:
    with out.open("w") as f:
        f.write(f"template<> struct ComponentTraits<{cls.spelling}> {{\n")
        f.write(f'    static constexpr std::string_view name = "{cls.spelling}";\n')
        f.write( "    static constexpr auto fields = std::tuple{\n")
        for field in cls.get_children():
            if field.kind == clang.cindex.CursorKind.FIELD_DECL:
                f.write(f'        Field{{"{field.spelling}", '
                        f'&{cls.spelling}::{field.spelling}}},\n')
        f.write( "    };\n};\n")
```

---

## See also

- `ASSET_PIPELINE_AND_COOKER.md` — hot-reload pipeline, DDC, cook orchestration that the editor drives.
- `TESTING_ERROR_HANDLING_AND_BUILD.md` — `std::expected` patterns used across the C ABI, editor integration tests.
- `CPP23_26_AND_MODERN_PATTERNS.md` — reflection strategy (codegen today, static reflection horizon), Handle<Tag> for editor-runtime object identity.
