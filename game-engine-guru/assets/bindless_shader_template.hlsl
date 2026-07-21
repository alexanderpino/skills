// =============================================================================
// bindless_shader_template.hlsl
//
// Bindless forward pass scaffold. Target: Shader Model 6.6 (DX12) with
// ResourceDescriptorHeap / SamplerDescriptorHeap direct heap indexing.
// Builds to SPIR-V via DXC (-spirv) for Vulkan parity - see porting notes below.
//
// -----------------------------------------------------------------------------
// Root signature (authored in C++ / D3D12 via D3D12SerializeRootSignature)
// -----------------------------------------------------------------------------
// RootFlags:
//     ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT
//   | CBV_SRV_UAV_HEAP_DIRECTLY_INDEXED    // SM 6.6 bindless
//   | SAMPLER_HEAP_DIRECTLY_INDEXED
//   | DENY_HULL_SHADER_ROOT_ACCESS
//   | DENY_DOMAIN_SHADER_ROOT_ACCESS
//   | DENY_GEOMETRY_SHADER_ROOT_ACCESS
//   // In the pixel-only pass reuse of this RS, also add:
//   // | DENY_VERTEX_SHADER_ROOT_ACCESS
//
// Slot table:
//   b0 : RootConstants(num32BitConstants = 4)   // PushConstants
//        [0] MaterialIndex
//        [1] MeshIndex
//        [2] InstanceIndex
//        [3] FrameIndex
//   b1 : RootCBV (per-frame constants, view/proj/time)
//
// No bound textures / samplers / SRVs in the root signature. All resources are
// reached via ResourceDescriptorHeap[uint] and SamplerDescriptorHeap[uint]
// using indices carried in push constants or material structs.
//
// -----------------------------------------------------------------------------
// Vulkan equivalence
// -----------------------------------------------------------------------------
//   Extension:   VK_EXT_descriptor_indexing (core in Vulkan 1.2)
//   Feature bits (VkPhysicalDeviceDescriptorIndexingFeatures):
//     - runtimeDescriptorArray                           : REQUIRED
//     - shaderSampledImageArrayNonUniformIndexing        : REQUIRED
//     - shaderStorageBufferArrayNonUniformIndexing       : REQUIRED for SSBOs
//     - descriptorBindingPartiallyBound                  : REQUIRED
//     - descriptorBindingVariableDescriptorCount         : RECOMMENDED
//   Pipeline layout:
//     set 0 binding 0 : unbounded array of sampled images (matches
//                       ResourceDescriptorHeap textures)
//     set 0 binding 1 : unbounded array of samplers (SamplerDescriptorHeap)
//     set 0 binding 2 : MaterialParams buffer array
//     set 0 binding 3 : InstanceData buffer array
//     set 0 binding 4 : MeshVertex buffer array
//     set 0 binding 5 : per-frame uniform buffer
//   Push constants: the 16-byte PushConstants struct from shader_interop_template.h.
//   Compile with DXC: -D SI_VULKAN=1 -T ps_6_6 -spirv -fvk-use-dx-layout -Zpr
//                     -fspv-target-env=vulkan1.3
//
// -----------------------------------------------------------------------------
// Metal equivalence
// -----------------------------------------------------------------------------
//   Requires Argument Buffers Tier 2 (all Apple Silicon, A13+, macOS 10.15+).
//   The heap-index access pattern maps to an MTLArgumentBuffer populated with
//   useResource: for all referenced textures. Convert via spirv-cross --msl
//   --msl-argument-buffers or DirectX Shader Compiler's -T lib_6_6 + spirv-cross.
// =============================================================================

//------------------------------------------------------------------------------
// Shared CPU<->GPU layouts. PushConstants, PerFrameCB, MaterialParams,
// InstanceData and the descriptor-slot constants come from ONE header compiled
// by both C++ and HLSL — no hand-mirrored duplicate to drift. See
// shader_interop_template.h (it carries the 16-byte packing rules and the C++
// size/alignment/offset static_asserts).
//------------------------------------------------------------------------------

#include "shader_interop_template.h"

#if defined(SI_VULKAN)
[[vk::push_constant]]
ConstantBuffer<PushConstants> g_PC;
[[vk::binding(0, 0)]] Texture2D<float4>                 g_Textures[];
[[vk::binding(1, 0)]] SamplerState                      g_Samplers[];
[[vk::binding(2, 0)]] StructuredBuffer<MaterialParams>  g_MaterialBuffers[];
[[vk::binding(3, 0)]] StructuredBuffer<InstanceData>    g_InstanceBuffers[];
[[vk::binding(4, 0)]] StructuredBuffer<MeshVertex>      g_MeshVertexBuffers[];
[[vk::binding(5, 0)]] ConstantBuffer<PerFrameCB>         g_Frame;
#else
ConstantBuffer<PushConstants> g_PC    : register(b0);
ConstantBuffer<PerFrameCB>    g_Frame : register(b1);
#endif

// MeshVertex (the vertex-pulling layout) is also defined in the shared header,
// under packed rules — see its "Vertex layouts (packed)" section.

//------------------------------------------------------------------------------
// Stage I/O
//------------------------------------------------------------------------------

struct VSInput
{
    uint VertexID   : SV_VertexID;
};

struct VSOutput
{
    float4 Position     : SV_Position;
    float3 WorldPos     : TEXCOORD0;
    float3 WorldNormal  : TEXCOORD1;
    float4 WorldTangent : TEXCOORD2;
    float2 UV0          : TEXCOORD3;
    nointerpolation uint MaterialIndex : TEXCOORD4;
};

//------------------------------------------------------------------------------
// Vertex Shader
//------------------------------------------------------------------------------

VSOutput VSMain(VSInput input)
{
    // Pull instance transform from the bindless instance buffer.
#if defined(SI_VULKAN)
    StructuredBuffer<InstanceData> instances =
        g_InstanceBuffers[NonUniformResourceIndex(kInstanceBufferSlot)];
#else
    StructuredBuffer<InstanceData> instances =
        ResourceDescriptorHeap[kInstanceBufferSlot];
#endif
    InstanceData inst = instances[g_PC.InstanceIndex];

    // Pull the mesh vertex buffer via NonUniformResourceIndex because the
    // MeshIndex can differ across waves (instanced draws over multiple meshes).
    const uint meshIndex = NonUniformResourceIndex(kMeshVertexSlotBase + g_PC.MeshIndex);
#if defined(SI_VULKAN)
    StructuredBuffer<MeshVertex> mesh = g_MeshVertexBuffers[meshIndex];
#else
    StructuredBuffer<MeshVertex> mesh = ResourceDescriptorHeap[meshIndex];
#endif
    MeshVertex v = mesh[input.VertexID];

    float4 worldPos = mul(inst.World, float4(v.Position, 1.0f));

    VSOutput o;
    o.Position      = mul(g_Frame.ViewProj, worldPos);
    o.WorldPos      = worldPos.xyz;
    o.WorldNormal   = normalize(mul((float3x3)inst.WorldIT, v.Normal));
    // Reflection (negative determinant) flips tangent-space handedness.
    const float orientationSign =
        determinant((float3x3)inst.World) < 0.0f ? -1.0f : 1.0f;
    o.WorldTangent  = float4(
        normalize(mul((float3x3)inst.World, v.Tangent.xyz)),
        v.Tangent.w * orientationSign);
    o.UV0           = v.UV0;
    o.MaterialIndex = g_PC.MaterialIndex;
    return o;
}

//------------------------------------------------------------------------------
// Helpers
//------------------------------------------------------------------------------

float3 UnpackNormalMap(float3 sampled, float scale)
{
    // Assumes a BC5 / RG normal map: reconstruct Z.
    float3 n = float3(sampled.rg * 2.0f - 1.0f, 0.0f);
    n.xy    *= scale;
    n.z      = sqrt(saturate(1.0f - dot(n.xy, n.xy)));
    return n;
}

float3 ApplyNormalMap(float3 N, float4 T, float3 mapN)
{
    float3 Ntan = normalize(N);
    float3 Ttan = normalize(T.xyz - Ntan * dot(T.xyz, Ntan));
    float3 Btan = cross(Ntan, Ttan) * T.w;
    return normalize(mapN.x * Ttan + mapN.y * Btan + mapN.z * Ntan);
}

//------------------------------------------------------------------------------
// Pixel Shader
//------------------------------------------------------------------------------

float4 PSMain(VSOutput input) : SV_Target0
{
    // Material lookup: nointerpolation so MaterialIndex is uniform per triangle,
    // but NonUniformResourceIndex is still legal and required across wave lanes
    // of different primitives within a draw (draw-indirect, mesh shaders).
    const uint materialBufferIndex = NonUniformResourceIndex(kMaterialBufferSlot);
#if defined(SI_VULKAN)
    StructuredBuffer<MaterialParams> materials = g_MaterialBuffers[materialBufferIndex];
#else
    StructuredBuffer<MaterialParams> materials = ResourceDescriptorHeap[materialBufferIndex];
#endif
    MaterialParams mat = materials[NonUniformResourceIndex(input.MaterialIndex)];

    // Texture fetches: every index goes through NonUniformResourceIndex because
    // the wave can contain lanes from different materials.
#if defined(SI_VULKAN)
    Texture2D<float4> albedoTex   = g_Textures[NonUniformResourceIndex(mat.AlbedoTex)];
    Texture2D<float4> normalTex   = g_Textures[NonUniformResourceIndex(mat.NormalTex)];
    Texture2D<float4> ormTex      = g_Textures[NonUniformResourceIndex(mat.OrmTex)];
    Texture2D<float4> emissiveTex = g_Textures[NonUniformResourceIndex(mat.EmissiveTex)];
    SamplerState samp             = g_Samplers[NonUniformResourceIndex(kLinearWrapSampler)];
#else
    Texture2D albedoTex   = ResourceDescriptorHeap[NonUniformResourceIndex(mat.AlbedoTex)];
    Texture2D normalTex   = ResourceDescriptorHeap[NonUniformResourceIndex(mat.NormalTex)];
    Texture2D ormTex      = ResourceDescriptorHeap[NonUniformResourceIndex(mat.OrmTex)];
    Texture2D emissiveTex = ResourceDescriptorHeap[NonUniformResourceIndex(mat.EmissiveTex)];
    SamplerState samp     = SamplerDescriptorHeap[kLinearWrapSampler];
#endif

    // AlbedoTex must use an sRGB SRV/image format, so Sample returns linear
    // RGB. BaseColor is uploaded in linear space; alpha remains linear.
    float4 albedo = albedoTex.Sample(samp, input.UV0) * mat.BaseColor;
    // Alpha-test clip gate; masked materials should define ALPHA_MASKED=1.
#if defined(ALPHA_MASKED) && ALPHA_MASKED
    clip(albedo.a - 0.5f);
#endif

    float3 orm      = ormTex.Sample(samp, input.UV0).rgb;
    float  occ      = orm.r;
    float  rough    = saturate(orm.g * mat.Roughness);
    float  metal    = saturate(orm.b * mat.Metallic);

    float3 mapN     = UnpackNormalMap(normalTex.Sample(samp, input.UV0).rgb, mat.NormalScale);
    float3 N        = ApplyNormalMap(input.WorldNormal, input.WorldTangent, mapN);
    float3 V        = normalize(g_Frame.CameraPos - input.WorldPos);

    // Minimal analytic lit term. Replace with the engine's shared BRDF include
    // (forward+ / clustered). Kept local here so the scaffold compiles standalone.
    // For the actual GGX/Smith/Fresnel + energy-conserving BSDF math, see the
    // `physically-based-rendering` skill (references/realtime-rasterization.md).
    float3 L        = normalize(float3(0.3f, 1.0f, 0.2f));
    float  NdotL    = saturate(dot(N, L));
    float3 diffuse  = albedo.rgb * (1.0f - metal);
    float3 lit      = diffuse * NdotL * occ;

    float3 emissive = emissiveTex.Sample(samp, input.UV0).rgb
                    * mat.EmissiveColor.rgb * mat.EmissiveIntensity;

    // Suppress unused warnings for rough/V in this minimal scaffold.
    lit += 0.0f * rough * dot(V, N);

    return float4(lit + emissive, albedo.a);
}
