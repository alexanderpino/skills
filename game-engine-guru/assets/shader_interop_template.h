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
// The trick is a thin macro/alias prelude that supplies scalar-layout POD types
// in C++, leaves vector types native in HLSL, and remaps them to vec*/mat* in
// GLSL. Everything below the prelude is written ONCE.
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
//   4. Matrices: this file declares every matrix row-major. Also compile DXC
//      with `-Zpr` (including SPIR-V), declare GLSL consuming blocks with
//      `layout(row_major, scalar)`, and use row-major CPU uploads. A build
//      without those settings is unsupported; mismatched majorness transposes.
//   5. Vertex layouts are shared too, but under DIFFERENT rules — see the
//      "Vertex layouts (packed)" section. They are NOT cbuffer-packed: vertex
//      data is tightly packed (4-byte scalar alignment, no 16-byte rows), so
//      they use the `packed_*` types (align-4) and `SI_VERTEX`, never the
//      alignas(16) `SI_STRUCT`. A SIMD-aligned vector would silently misalign a
//      vertex struct. The packed struct is the source of truth for the
//      vertex-pulling path; for the input-assembler path, derive the
//      D3D12_INPUT_ELEMENT_DESC / VkVertexInputAttributeDescription offsets from
//      `offsetof` so the IA layout can't drift from it either.
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
    #include <bit>
    #include <climits>
    #include <limits>
    #include <type_traits>
    namespace engine::gpu {

    using uint     = std::uint32_t;
    // Interop types are deliberately independent of SIMD math-library types.
    // Their scalar alignment exactly matches HLSL scalar layout: 8/12/16-byte
    // vectors with 4-byte alignment and a row-major 64-byte matrix.
    struct float2   { float x, y; };
    struct float3   { float x, y, z; };
    struct float4   { float x, y, z, w; };
    struct float4x4 { float m[4][4]; };

    using packed_float2 = float2;
    using packed_float3 = float3;
    using packed_float4 = float4;

    #define SI_STRUCT(name) struct alignas(16) name   // cbuffer: honor 16-byte rule
    #define SI_VERTEX(name) struct name               // vertex: tight, align-4
    #define SI_CONST        inline constexpr uint
    #define SI_ROW_MAJOR

#elif defined(__HLSL_VERSION)
    // -------- HLSL (DXC) -----------------------------------------------------
    // float2/3/4, float4x4, uint are native. No remapping needed.
    #define packed_float2 float2
    #define packed_float3 float3
    #define packed_float4 float4
    #define SI_STRUCT(name) struct name
    #define SI_VERTEX(name) struct name
    #define SI_CONST        static const uint
    #define SI_ROW_MAJOR    row_major

#else
    // -------- GLSL (glslang) -------------------------------------------------
    // Compile shared UBOs with `layout(scalar)` (GL_EXT_scalar_block_layout) so
    // vec3 packing matches HLSL/C++ — see rule 3.
    #define float2   vec2
    #define float3   vec3
    #define float4   vec4
    #define float4x4 mat4
    #define packed_float2 vec2
    #define packed_float3 vec3
    #define packed_float4 vec4
    // `uint` is native in GLSL (>= 1.30) — no remap needed.
    #define SI_STRUCT(name) struct name
    #define SI_VERTEX(name) struct name
    #define SI_CONST        const uint
    // GLSL applies row_major on the consuming interface block; unlike HLSL,
    // a portable shared struct member cannot carry this storage qualifier.
    #define SI_ROW_MAJOR
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
    SI_ROW_MAJOR float4x4 ViewProj;     // @0
    SI_ROW_MAJOR float4x4 InvViewProj;  // @64
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
    float4 BaseColor;          // @16 linear tint; convert authored sRGB on import
    float  Metallic;           // @32
    float  Roughness;          // @36
    float  NormalScale;        // @40
    float  EmissiveIntensity;  // @44
    float4 EmissiveColor;      // @48
};

// One element of StructuredBuffer<InstanceData>.
SI_STRUCT(InstanceData)
{
    SI_ROW_MAJOR float4x4 World;    // @0
    SI_ROW_MAJOR float4x4 WorldIT;  // @64 inverse-transpose normal transform
};

// =============================================================================
// Vertex layouts (packed) — DIFFERENT rules from the cbuffer structs above.
// Tightly packed (4-byte scalar alignment, NO 16-byte rows), so use packed_*
// + SI_VERTEX, never SI_STRUCT. This struct is the single source of truth for
// the vertex-PULLING path (StructuredBuffer<MeshVertex> indexed by SV_VertexID).
// For the input-ASSEMBLER path, build the input-element descriptors from these
// offsets via offsetof(MeshVertex, Field) so the IA layout can't drift either.
// GLSL caveat: an SSBO of these needs layout(scalar) — std140/std430 both round
// vec3 up to 16B and would desync (same family as rule 3).
// =============================================================================
SI_VERTEX(MeshVertex)
{
    packed_float3 Position;  // @0  (12B)
    packed_float3 Normal;    // @12 (12B)
    packed_float4 Tangent;   // @24 (16B)  .w = bitangent sign
    packed_float2 UV0;       // @40 ( 8B)
};                           // stride = 48B, tight

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
    static_assert(CHAR_BIT == 8, "interop ABI requires 8-bit bytes");
    static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559,
                  "interop ABI requires IEEE-754 binary32");
    static_assert(sizeof(uint) == 4, "interop ABI requires a 32-bit uint");
    static_assert(std::endian::native == std::endian::little,
                  "this upload format is little-endian; byte-swap on other hosts");
    static_assert(sizeof(float2) == 8 && alignof(float2) == 4, "float2 must use scalar layout");
    static_assert(sizeof(float3) == 12 && alignof(float3) == 4, "float3 must use scalar layout");
    static_assert(sizeof(float4) == 16 && alignof(float4) == 4, "float4 must use scalar layout");
    static_assert(sizeof(float4x4) == 64 && alignof(float4x4) == 4,
                  "float4x4 must be a tightly packed row-major matrix");
    static_assert(std::is_trivial_v<float2> && std::is_standard_layout_v<float2>);
    static_assert(std::is_trivial_v<float3> && std::is_standard_layout_v<float3>);
    static_assert(std::is_trivial_v<float4> && std::is_standard_layout_v<float4>);
    static_assert(std::is_trivial_v<float4x4> && std::is_standard_layout_v<float4x4>);

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
    static_assert(std::is_trivially_copyable_v<PushConstants> &&
                  std::is_standard_layout_v<PushConstants>);
    static_assert(std::is_trivially_copyable_v<PerFrameCB> &&
                  std::is_standard_layout_v<PerFrameCB>);
    static_assert(std::is_trivially_copyable_v<MaterialParams> &&
                  std::is_standard_layout_v<MaterialParams>);
    static_assert(std::is_trivially_copyable_v<InstanceData> &&
                  std::is_standard_layout_v<InstanceData>);
    static_assert(std::is_trivially_copyable_v<MeshVertex> &&
                  std::is_standard_layout_v<MeshVertex>);

    // Offset guards: pin the fields most likely to shift a row.
    static_assert(offsetof(PerFrameCB, Time)   == 140, "PerFrameCB.Time moved — check the float3+float row");
    static_assert(offsetof(PerFrameCB, Jitter) == 144, "PerFrameCB.Jitter moved — check explicit padding");
    static_assert(offsetof(MaterialParams, EmissiveColor) == 48, "MaterialParams float4 misaligned");

    // Vertex layout: tight packing. alignof MUST be 4 (not 16) — a 16-aligned
    // member would force padding and desync the vertex stride.
    static_assert(alignof(MeshVertex) == 4,  "MeshVertex must be tightly packed (align 4) — did a SIMD type leak in?");
    static_assert(sizeof(MeshVertex)  == 48, "MeshVertex stride drift");
    static_assert(offsetof(MeshVertex, Normal)  == 12, "MeshVertex.Normal offset");
    static_assert(offsetof(MeshVertex, Tangent) == 24, "MeshVertex.Tangent offset");
    static_assert(offsetof(MeshVertex, UV0)     == 40, "MeshVertex.UV0 offset");

    } // namespace engine::gpu
#endif

// Keep the macros local to this header so they don't leak into shader bodies.
#undef SI_STRUCT
#undef SI_VERTEX
#undef SI_CONST
#undef SI_ROW_MAJOR

#endif // ENGINE_SHADER_INTEROP_H
