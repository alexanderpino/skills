# Animation and Character Systems

## Table of Contents
1. Animation Graph Architecture
2. Motion Matching
3. Inverse Kinematics
4. Procedural Animation
5. Cloth & Hair
6. Facial Animation
7. Skinning Methods
8. Animation Compression
9. Crowd Animation
10. See Also

---

## 1. Animation Graph Architecture

The animation graph is the single most-touched subsystem in a AAA character pipeline. It runs N characters × M layers × K bones every frame. Budget it like you budget rendering: 1.5ms for 100 characters at full rig, 0.3ms for the hero.

**Hierarchical state machines.** Parent state contains a child FSM. Locomotion = parent; idle/walk/run/sprint = children. Reload = parent; magazine-out/magazine-in/slide-release = children. Transitions are named, not numbered — data drives everything. Each state owns local variables and sync group affiliation.

**Layers.** Lower body = locomotion. Upper body = aiming/reload. Face = facial rig. Each layer is additive or override. Blend weight per layer is the output of gameplay code. Masking per-bone with a compact `std::bitset<256>` mask.

**Blend trees.** 1D for speed-driven locomotion (idle/walk/jog/run/sprint). 2D Cartesian for strafe (x=lateral, y=forward). 2D freeform for directional blends. Additive branches for breathing, weapon sway, damage reactions. Compute barycentric weights per tick; cache from previous tick and only recompute when inputs change by >1e-3.

**Sync groups.** All locomotion anims of the same cycle share a phase `[0,1)`. Blending between them uses phase-matched sampling — you never sample walk at 0.23 against run at 0.81. Normalize time across group members by their native duration.

```cpp
struct AnimNode {
    virtual std::expected<Pose, AnimError>
    evaluate(EvalContext& ctx, float phase) noexcept = 0;
};

struct BlendTree1D final : AnimNode {
    std::span<const BlendSample> samples; // sorted by param
    float param{};

    std::expected<Pose, AnimError>
    evaluate(EvalContext& ctx, float phase) noexcept override {
        const auto [lo, hi, t] = find_span(samples, param);
        Pose a = samples[lo].node->evaluate(ctx, phase).value_or(Pose::identity());
        Pose b = samples[hi].node->evaluate(ctx, phase).value_or(Pose::identity());
        return blend(a, b, t, ctx.scratch);
    }
};
```

All pose allocations come from the frame-scratch tier. Zero heap traffic per frame.

---

## 2. Motion Matching

Motion matching (Ubisoft La Forge, EA Frostbite) replaces hand-authored blend trees with a database of motion clips queried per tick by a feature vector. Retires the animation graph for locomotion but doesn't eliminate it — you still need it for combat and gameplay states.

**Feature vector.** Typical 27-32 floats per frame:
- Future trajectory positions (t+0.33s, t+0.66s, t+1.0s): 3 × 2 floats
- Future trajectory facing (same timestamps): 3 × 2 floats
- Foot positions (L+R) in character space: 2 × 3 floats
- Foot velocities: 2 × 3 floats
- Hip velocity: 3 floats

**Query.** Every 10-15 frames (not every frame — overkill), build the desired feature vector from user input + gameplay, then nearest-neighbor search the pose database. KD-tree with L2 distance weights tuned per feature (trajectory weighted ~3x foot position).

**Inertialization.** Use a damped blend on position and velocity deltas between old and new poses. Matching velocity gives C1 continuity and avoids visible pops; it does not imply continuous acceleration.

```cpp
struct Inertializer {
    Pose delta0;      // offset at transition
    Pose dPose_dt0;   // velocity at transition
    float t = 0.f;

    Pose apply(const Pose& target, float dt) noexcept {
        t += dt;
        const float halflife = 0.15f;
        const float y = std::log(2.0f) / halflife;
        const float a = std::exp(-y * t);
        // critically damped IIR on each bone
        return blend_additive(target, decay(delta0, dPose_dt0, y, t, a));
    }
};
```

**Compression.** Raw pose database for a 200k-frame capture is ~200MB. Compress with PCA on quaternion joints (keep top 32 principal components) or k-means cluster poses (1024 centroids). Lookup returns index + residual; reconstruct at eval time. 8-12x compression, <1% perceptible error.

---

## 3. Inverse Kinematics

Pick the solver that matches the problem. Don't reach for full-body IK when two-bone analytic ships.

**Two-bone analytic.** Law of cosines. 40 cycles on x64. Use for legs, arms, finger grips. Constrained to the plane of the pole vector; pole must be set or you get arbitrary rotation.

```text
// Pseudocode: two-bone analytic IK, chain root -> joint -> end.
// l1=|root..joint|, l2=|joint..end|; target T and pole point P in root space.
solve_two_bone(root, currentJoint, l1, l2, T, P, cachedBendNormal):
    targetVector = T - root
    rawDistance = length(targetVector)
    if rawDistance < eps:
        targetDirection = safe_normalize(currentJoint - root, fallbackForward)
    else:
        targetDirection = targetVector / rawDistance
    d = clamp(rawDistance, abs(l1 - l2) + eps, l1 + l2 - eps)
    reachableTarget = root + targetDirection * d
    // interior (knee/elbow) angle; clamp cosine to kill FP drift outside [-1,1] -> NaN acos
    kneeAngle     = acos(clamp((l1*l1 + l2*l2 - d*d) / (2*l1*l2), -1, 1))
    shoulderAngle = acos(clamp((l1*l1 + d*d - l2*l2) / (2*l1*d), -1, 1))
    axis = cross(targetDirection, P - root)           // bend plane normal
    if length(axis) < eps: axis = cachedBendNormal
    axis = safe_normalize(axis, any_perp(targetDirection))
    rotate root by shoulderAngle about axis, aim root->joint toward reachableTarget
    rotate joint by (π - kneeAngle) about axis        // then FK the end effector onto T
```

**CCD.** Cyclic coordinate descent. Iterative, O(joints × iterations). Cheap per iteration (~10 cycles), typically converges in 4-8 iterations. Use for short chains (tail, tentacle) where root lock is acceptable.

**FABRIK.** Forward and Backward Reaching IK. Position-based, handles length constraints cleanly, allows rotation constraints after the fact. 2-4 iterations for most cases. Use for long chains and cable/rope rigs.

**Full-body IK.** Unity FBIK / RootMotion Final IK / Unreal Control Rig. Balanced pelvis motion, foot plant preservation, hand reach without pulling the torso. Budget 80μs per character.

**Foot IK.** Raycast down from footstep anim-predicted position, adjust ankle height + rotate foot to match ground normal. Blend weight down during air phase via curve in the anim asset. Ground conform slerp capped at 30° to avoid broken ankles on cliffs.

**Hand IK for grip.** Target = weapon grip socket. Solver = two-bone + CCD wrist. Enable only when the hand is visibly close to the weapon — skip when upper body is idling.

**Look-at / aim constraint.** Split across head (60%), neck (30%), spine (10%). Per-bone max-angle clamps prevent Exorcist. Update on animation graph output, before skinning.

---

## 4. Procedural Animation

**Active ragdoll.** PD controller per joint: `τ = kp * (θ_target - θ) - kd * ω`. Target pose comes from the animation graph; PD torques push the physics-driven ragdoll toward it. Stiffness profile per bone (spine stiffer than fingers). Blend weight between full animation and full ragdoll driven by impact, damage, or state.

**Euphoria-style behaviors (NaturalMotion).** State-machine of PD targets: stagger, catch-fall, shielding head, weapon reach. Each behavior overrides a bone subset. Expensive — 2-4ms per actor — reserve for hero NPCs and cinematic deaths.

**Motion warping.** Root motion from an anim asset is retargeted at runtime to hit a world target (ledge, interaction point). Scale translation in the sampling phase so that the final root position equals the target at the anim's end time. Rotation is slerped. Essential for Assassin's Creed-style parkour.

---

## 5. Cloth & Hair

**Cloth (XPBD).** Constraints: distance (edges), bending (dihedral or hinge), collision (body capsules). 10-20 iterations for a shirt, 40+ for a cape with self-collision. GPU dispatch per character, compute shader 64-thread groups. Budget: 0.4ms per character on GPU.

**Strand hair.** TressFX/HairWorks-style strands can be simulated as short chains with FTL-style constraints. Render with triangle/ribbon geometry or platform-specific curve/linear-swept-sphere ray-tracing extensions where available; DXR 1.1 itself did not add curve primitives.

**Marschner shading.** Three lobes — R (primary reflection), TT (transmission), TRT (secondary highlight). Dual-scattering approximation for multi-bounce. Cost: 1.2x standard skin shader. Ship it on hero characters.

**LOD.** Full strand sim inside camera frustum within 8m. Card-based hair beyond that. Transition hidden by camera distance.

---

## 6. Facial Animation

**FACS.** 46 Action Units (Ekman). Pose library maps AU combinations to blend shapes or bone rigs. This is the standard vocabulary — performance capture, retargeting, and blend shape libraries are all expressed in AUs.

**Blend shapes.** 50-200 morph targets per hero face. Per-vertex deltas stored as sparse arrays (most vertices move for most shapes, sparse only for localized shapes). Evaluate on compute shader — one thread per vertex, sum all active shape deltas scaled by weight.

**Bone-driven face.** 60-120 joints for cheaper characters. Cheaper at runtime, worse quality. Use for crowd NPCs and non-hero speakers.

**Lip sync.** Oculus LipSync provides 15 visemes from audio input (30fps). JALI (Edwards 2016) is the AAA standard — two axes (jaw, lip) plus phoneme triggers. Drives AU subset for mouth.

**Wrinkle maps.** Normal maps blended by AU weight. Authored per-region (brow, nasolabial, crow's feet). Blended additively with base normal map before lighting.

---

## 7. Skinning Methods

**Linear Blend Skinning (LBS).** Four bone influences per vertex is standard. Weight sum = 1. Fast, cache-friendly, GPU-native. Artifact: candy-wrapper at twisting joints.

**Dual quaternion skinning.** Reduces candy-wrapper artifacts at higher per-vertex ALU cost than LBS. Its 8-float palette can reduce palette bandwidth relative to a 12-float affine matrix; benchmark the complete pass.

**Compute shader skinning.** 64-thread groups, one thread per vertex. Output to a vertex buffer bound for subsequent passes (shadow pass, main pass). Essential for ray tracing — BLAS rebuild/refit needs skinned positions in buffer memory, not in the vertex stage.

```hlsl
[numthreads(64, 1, 1)]
void SkinCS(uint3 tid : SV_DispatchThreadID) {
    const uint vid = tid.x;
    if (vid >= gVertexCount) return;
    const SkinVertex v = gInput[vid];
    float4x4 M = 0;
    [unroll] for (int i = 0; i < 4; ++i) {
        M += gBoneMatrices[v.indices[i]] * v.weights[i];
    }
    gOutput[vid].pos = mul(M, float4(v.pos, 1)).xyz;
    gOutput[vid].nrm = mul((float3x3)M, v.nrm);
}
```

**ML corrective deformers.** Train a compact model against simulation or sculpted ground truth and evaluate it through a capability-gated backend. GPU compute is the broadly available shipping path; NPU offload is optional where hardware, synchronization, and latency measurements justify it.

---

## 8. Animation Compression

Raw 30Hz motion capture at 200 bones: 200 bones × (4+3) floats × 4 bytes × 30 Hz = 168 KB/s. A 2-hour cutscene ships at 1.2 GB uncompressed. Unacceptable.

**ACL (Animation Compression Library, Nicholas Frechette).** Open-source, battle-tested (Uncharted 4, The Last of Us Part II, hundreds of ships). Use it. Don't write your own.

**Smallest-three quaternion.** Store the three smallest components and reconstruct the largest from the unit-length constraint. Encode the index of the largest in 2 bits. Per stored component 16-bit quantization → **2 + 3×16 = 50 bits** per quat vs 128. Reconstruction is one sqrt.

```cpp
// Smallest-three: 2-bit index of the largest (dropped) component + three 16-bit
// components = 50 bits total. The three stored components each lie in
// [-1/√2, +1/√2] (the largest has magnitude ≥ 1/2, so it is never stored).
// Canonicalize the sign so the dropped component is non-negative; it is then
// reconstructed as +sqrt(1 - a² - b² - c²). Bit layout in the low 50 bits:
//   [1:0] idx | [17:2] a | [33:18] b | [49:34] c
inline constexpr float kInvSqrt2 = 0.70710678118654752f;
inline constexpr float kQuatMax  = float((1u << 16) - 1); // 65535, the 16-bit span

struct QuantQuat { uint64_t packed; };   // only the low 50 bits are used

// map [-1/√2, +1/√2] -> [0, 65535]
inline uint16_t quant_component(float v) noexcept {
    const float n = (v + kInvSqrt2) / (2.0f * kInvSqrt2);
    const float c = n < 0.f ? 0.f : (n > 1.f ? 1.f : n);
    return static_cast<uint16_t>(c * kQuatMax + 0.5f);
}
// inverse map [0, 65535] -> [-1/√2, +1/√2]
inline float dequant_component(uint16_t u) noexcept {
    return (static_cast<float>(u) / kQuatMax) * (2.0f * kInvSqrt2) - kInvSqrt2;
}

inline QuantQuat pack(Quat q) noexcept {
    const float c[4] = { q.x, q.y, q.z, q.w };
    uint32_t idx = 0;                                   // largest-magnitude component
    for (uint32_t i = 1; i < 4; ++i)
        if (std::fabs(c[i]) > std::fabs(c[idx])) idx = i;
    const float s = c[idx] < 0.f ? -1.f : 1.f;          // make dropped component ≥ 0
    const uint16_t a = quant_component(s * c[(idx + 1) & 3]);
    const uint16_t b = quant_component(s * c[(idx + 2) & 3]);
    const uint16_t d = quant_component(s * c[(idx + 3) & 3]);
    return { uint64_t(idx) | (uint64_t(a) << 2)
           | (uint64_t(b) << 18) | (uint64_t(d) << 34) };
}

inline Quat unpack(QuantQuat q) noexcept {
    const uint32_t idx = uint32_t(q.packed & 0x3);
    const float a = dequant_component(uint16_t((q.packed >> 2)  & 0xFFFF));
    const float b = dequant_component(uint16_t((q.packed >> 18) & 0xFFFF));
    const float c = dequant_component(uint16_t((q.packed >> 34) & 0xFFFF));
    const float d2 = 1.f - (a*a + b*b + c*c);
    const float d  = d2 > 0.f ? std::sqrt(d2) : 0.f;    // reconstructed largest, ≥ 0
    std::array<float, 4> xyzw{};
    xyzw[(idx + 1) & 3] = a;
    xyzw[(idx + 2) & 3] = b;
    xyzw[(idx + 3) & 3] = c;
    xyzw[idx]           = d;
    return Quat{xyzw[0], xyzw[1], xyzw[2], xyzw[3]};
}
```

**Variable bit rate per track.** A finger curl might need 8 bits; a spine swing needs 16. Per-track analysis during compression picks the minimum bit rate that preserves error under a threshold (typically 0.01 radians). Often cuts total size 2x beyond uniform quantization.

**SoA decompression layout.** Decompress into struct-of-arrays pose (separate rotation, translation, scale buffers) so downstream skinning / IK can SIMD-load 4 bones at a time. Not array-of-structs.

---

## 9. Crowd Animation

10,000 visible characters on a battlefield, 60Hz, 5ms budget. You are not skinning all of them every frame.

**LOD tick reduction.** Near crowd (≤10m): skin every frame. Mid (≤40m): every 2 frames. Far (≤100m): every 4-8 frames. Distant: imposter (baked animation textures). Phase-staggered so not every distant character ticks on the same frame.

**Instanced animation via vertex texture fetch.** Bake bone palettes for N poses into a texture array (Y=bone, X=frame). Each instance samples at a per-instance time offset. Zero CPU skinning cost, zero per-instance state, 40-100k crowd extras at negligible GPU cost.

**Crowd LOD hierarchy:**
- L0: full rig, DQS, facial, cloth — hero radius
- L1: full rig, LBS, no cloth — mid
- L2: half rig (30 bones), LBS — far
- L3: VAT imposter with 4 cycles — very far
- L4: billboard — off-screen reserve

**Navigation.** Group navmesh queries (ORCA / flowfield for large groups). Per-agent RVO only for <50 visible agents.

Budget per L2 character: <5μs CPU, <2μs GPU. Multiply by 1000 and it still fits the frame.

---

## See Also
- `PHYSICS_MATH_AND_SIMULATION.md` — dual quaternion math, cloth XPBD integration, ragdoll
- `AUDIO_AND_SPATIAL.md` — footstep audio hooks from foot IK
- `NETWORKING_AND_MULTIPLAYER.md` — pose replication, compressed quat over the wire
