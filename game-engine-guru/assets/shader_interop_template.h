#ifndef ENGINE_SHADER_INTEROP_H
#define ENGINE_SHADER_INTEROP_H
// =============================================================================
// shader_interop_template.h
//
// ONE definition of the CPU<->GPU data structs, compiled by BOTH the C++ engine
// and the shader compiler (HLSL via DXC, GLSL via glslang). There is a single
// source of truth, so a layout change cannot silently desync the two sides the
// way hand-mirrored structs do. Constants and trivial helpers can be shared the
// same way (see SI_CONST below).
//
//   C++ :  #include "shader_interop_template.h"   // sees engine::gpu::PerFrameCB ...
//   HLSL:  #include "shader_interop_template.h"   // DXC -I <dir>; native float4 etc.
//   GLSL:  #include "shader_interop_template.h"   // glslang -I or
//                                                 // GL_GOOGLE_include_directive
//
// The trick is a thin macro/alias prelude that maps shader vector types to the
// engine math types in C++, leaves them native in HLSL, and remaps them to
// vec*/mat* in GLSL. Everything below the prelude is written ONCE.
//
// -----------------------------------------------------------------------------
// HARD RULES for anything placed in a SHARED cbuffer / uniform block. Read these
// or you will ship a silent layout bug that only shows up on one API:
//   1. 16-byte rule (HLSL cbuffer): a field never straddles a 16-byte boundary;
//      cbuffers pack into 16-byte rows. Lay fields out so this holds, or pad.
//   2. NEVER use `bool` in a shared struct. HLSL cbuffer bool = 4 bytes, C++
//      bool = 1 byte. Use `uint` (0/1) and convert in-shader.
//   3. float3 / vec3 is the classic desync: HLSL packs vec3 as 12 bytes (the
//      next scalar fills the slot), but GLSL **std140** rounds vec3 up to 16.
//      They DISAGREE. Either avoid vec3 in shared blocks, OR compile the GLSL
//      side with GL_EXT_scalar_block_layout and `layout(scalar)` so it matches
//      HLSL/C++. PerFrameCB below intentionally uses the float3+float pattern to
//      demonstrate the rule — its GLSL UBO MUST be scalar-layout.
//   4. Matrices: force one majorness everywhere (HLSL `-Zpr` / `row_major`;
//      GLSL `layout(row_major)`). Mismatched majorness transposes silently.
//   5. Vertex-input structs are NOT shared here. engine::Vec4 is alignas(16),
//      which misaligns inside a tightly-packed vertex struct; vertex layouts use
//      packed (align-4) scalar types and live in a separate definition.
//   6. Pad explicitly. If a struct's last 16-byte row is only partially filled
//      and no real field completes it, add a NAMED pad field (`float _padN;` /
//      `float2 _padN;`) — never rely on the compiler to insert it. Make padding
//      visible, and assert it (see the static_asserts at the bottom).
//
// The C++ side carries static_assert guards on size, **alignment**, AND key
// field offsets (compiled out elsewhere) so any drift fails the C++ build. The
// GLSL std140/scalar choice has no such guard — rule 3 is the discipline that
// replaces it.
// =============================================================================

#if defined(__cplusplus)
    // -------- C++ ------------------------------------------------------------
    #include <cstddef>   // offsetof
    #include <cstdint>
    #include <engine/math/Math.h>   // engine::Vec2/Vec3/Vec4 (alignas 16), engine::Mat4

    namespace engine::gpu {

    using uint     = std::uint32_t;
    using float2   = engine::Vec2;
    using float3   = engine::Vec3;
    using float4   = engine::Vec4;
    using float4x4 = engine::Mat4;

    #define SI_STRUCT(name) struct alignas(16) name   // honor the 16-byte rule
    #define SI_CONST        inline constexpr uint

#elif defined(__HLSL_VERSION)
    // -------- HLSL (DXC) -----------------------------------------------------
    // float2/3/4, float4x4, uint are native. No remapping needed.
    #define SI_STRUCT(name) struct name
    #define SI_CONST        static const uint

#else
    // -------- GLSL (glslang) -------------------------------------------------
    // Compile shared UBOs with `layout(scalar)` (GL_EXT_scalar_block_layout) so
    // vec3 packing matches HLSL/C++ — see rule 3.
    #define float2   vec2
    #define float3   vec3
    #define float4   vec4
    #define float4x4 mat4
    // `uint` is native in GLSL (>= 1.30) — no remap needed.
    #define SI_STRUCT(name) struct name
    #define SI_CONST        const uint
#endif

// =============================================================================
// Shared constant-buffer / structured-buffer layouts (single source of truth)
// =============================================================================

// Root/push constants (HLSL b0 / VK push constants). 16 bytes.
SI_STRUCT(PushConstants)
{
    uint MaterialIndex;
    uint MeshIndex;
    uint InstanceIndex;
    uint FrameIndex;
};

// Per-frame CBV (HLSL b1). Demonstrates both the float3+float pattern (rule 3)
// and explicit named padding (rule 6).
SI_STRUCT(PerFrameCB)
{
    float4x4 ViewProj;     // @0
    float4x4 InvViewProj;  // @64
    float3   CameraPos;    // @128 (12B)  — Time fills the rest of this 16B row,
    float    Time;         // @140 ( 4B)    so no pad is needed *here* (std140 would
                           //               disagree on vec3 — compile GLSL scalar).
    float2   Jitter;       // @144 ( 8B)  TAA sub-pixel jitter (real field)
    float2   _pad0;        // @152 ( 8B)  EXPLICIT pad completing the 16B row
};

// One element of StructuredBuffer<MaterialParams>. All float4s land on 16B.
SI_STRUCT(MaterialParams)
{
    uint   AlbedoTex;          // @0  descriptor-heap index of a Texture2D
    uint   NormalTex;          // @4
    uint   OrmTex;             // @8  packed Occlusion/Roughness/Metallic
    uint   EmissiveTex;        // @12
    float4 BaseColor;          // @16 sRGB tint, multiplied against AlbedoTex
    float  Metallic;           // @32
    float  Roughness;          // @36
    float  NormalScale;        // @40
    float  EmissiveIntensity;  // @44
    float4 EmissiveColor;      // @48
};

// One element of StructuredBuffer<InstanceData>.
SI_STRUCT(InstanceData)
{
    float4x4 World;    // @0
    float4x4 WorldIT;  // @64  inverse-transpose for normal transform
};

// Global bindless descriptor indices baked by the engine at startup — shared so
// C++ and shaders agree on the slots without a second hand-edited copy.
SI_CONST kMaterialBufferSlot = 1;   // StructuredBuffer<MaterialParams>
SI_CONST kInstanceBufferSlot = 2;   // StructuredBuffer<InstanceData>
SI_CONST kMeshVertexSlotBase = 16;  // per-mesh base; add PushConstants.MeshIndex
SI_CONST kLinearWrapSampler  = 0;   // SamplerDescriptorHeap[0]
SI_CONST kPointClampSampler  = 1;

// =============================================================================
// C++-only layout guards. A field reorder / type change fails the build instead
// of silently corrupting GPU reads. (Compiled only on the C++ side.)
// =============================================================================
#if defined(__cplusplus)
    // Alignment guards (rule 6): every shared block aligns to 16 so it can drop
    // straight into a cbuffer/UBO. Catches a stray non-16-aligned member type.
    static_assert(alignof(PushConstants)  == 16, "PushConstants must be 16B aligned");
    static_assert(alignof(PerFrameCB)     == 16, "PerFrameCB must be 16B aligned");
    static_assert(alignof(MaterialParams) == 16, "MaterialParams must be 16B aligned");
    static_assert(alignof(InstanceData)   == 16, "InstanceData must be 16B aligned");

    // Size guards: total must be a whole number of 16B rows, with no surprise
    // compiler padding (rule 6 says padding is explicit and named).
    static_assert(sizeof(PushConstants)  == 16,  "PushConstants layout drift");
    static_assert(sizeof(PerFrameCB)     == 160, "PerFrameCB layout drift");
    static_assert(sizeof(MaterialParams) == 64,  "MaterialParams layout drift");
    static_assert(sizeof(InstanceData)   == 128, "InstanceData layout drift");

    // Offset guards: pin the fields most likely to shift a row.
    static_assert(offsetof(PerFrameCB, Time)   == 140, "PerFrameCB.Time moved — check the float3+float row");
    static_assert(offsetof(PerFrameCB, Jitter) == 144, "PerFrameCB.Jitter moved — check explicit padding");
    static_assert(offsetof(MaterialParams, EmissiveColor) == 48, "MaterialParams float4 misaligned");

    } // namespace engine::gpu
#endif

// Keep the macros local to this header so they don't leak into shader bodies.
#undef SI_STRUCT
#undef SI_CONST

#endif // ENGINE_SHADER_INTEROP_H
