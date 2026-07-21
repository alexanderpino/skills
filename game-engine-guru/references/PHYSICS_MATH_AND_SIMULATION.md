# Physics, Math, and Simulation

## Table of Contents
1. Math Library Design
2. Spatial Data Structures
3. Frustum Culling
4. Physics Engine Integration
5. Collision Detection Pipeline
6. Advanced Simulation
7. Interpolation & Curves
8. Dual Quaternions
9. Deterministic Simulation
10. See Also

---

## 1. Math Library Design

Math is the pilot light of the engine. Every frame touches it millions of times. Miss the SIMD lane width and you pay for it forever. Build it once, build it right, and never call into scalar fallbacks on hot paths.

**Targets.** Select the x64 baseline per shipping platform and dispatch AVX2/AVX-512 by CPUID plus measured benefit. NEON is the ARM64 baseline; gate SVE by runtime vector length. Legacy Intel AVX-512 downclock behavior is microarchitecture-specific and does not justify a blanket consumer ban.

**Type design.** `Vec4`, `Mat4`, `Quat` wrap a `__m128` / `float32x4_t` / native fallback via a `Simd4f` alias. Use `deducing this` (C++23) to eliminate const/non-const overload duplication:

```cpp
struct alignas(16) Vec4 {
    Simd4f v;

    template <class Self>
    auto&& operator[](this Self&& self, std::size_t i) noexcept {
        // Propagate const from the explicit object parameter. std::copy_cvref_t
        // is not part of the C++23 standard library; this conditional is the
        // portable equivalent for the const/non-const case we need here.
        using Elem = std::conditional_t<
            std::is_const_v<std::remove_reference_t<Self>>, const float, float>;
        return reinterpret_cast<Elem*>(&self.v)[i];
    }

    [[nodiscard]] std::expected<Vec4, MathError>
    normalized() const noexcept {
        const float len2 = dot(*this, *this);
        if (len2 < 1e-30f) [[unlikely]] return std::unexpected(MathError::DegenerateVector);
        return *this * rsqrt_nr(len2); // approximate; NOT for deterministic sim (§9)
    }
};

// Approximate reciprocal square root: hardware estimate + one Newton-Raphson
// refinement. This is the RENDER / general-math path — ~1-2 ULP after refining,
// but NOT bit-reproducible across vendors because the seed table differs.
// Deterministic simulation must use a strict sqrt/division path instead (§9).
inline float rsqrt_nr(float x) noexcept {
#if defined(__SSE__)
    float y = _mm_cvtss_f32(_mm_rsqrt_ss(_mm_set_ss(x))); // ~12-bit seed estimate
    y = y * (1.5f - 0.5f * x * y * y);                    // one NR step: y ≈ 1/√x
    return y;
#elif defined(__ARM_NEON)
    const float32x2_t vx = vdup_n_f32(x);
    float32x2_t vy = vrsqrte_f32(vx);
    vy = vmul_f32(vy, vrsqrts_f32(vmul_f32(vx, vy), vy)); // one NR step
    return vget_lane_f32(vy, 0);
#else
    return 1.0f / std::sqrt(x);                            // scalar platform fallback
#endif
}
```

**Half-precision (fp16).** Use `__fp16` / `_Float16` for GPU interop and packed vertex data. Half a meter of position error at 1km is fine for distant vegetation but unacceptable for sim. Keep fp16 on the mesh pipeline, fp32 on the CPU sim. Convert at upload time with `F16C` intrinsics (`_mm_cvtps_ph` / `_mm_cvtph_ps`). Cost: one instruction per four floats.

**Fixed-point (Q16.16).** A strong option for cross-architecture lockstep when its range and precision fit. Integer/fixed simulation is not required for every rollback design; same-platform or carefully controlled floating-point simulation can be deterministic within a declared support matrix. Use explicit saturation and test overflow boundaries.

```cpp
struct Fixed16_16 {
    int32_t raw;
    static constexpr int32_t kShift = 16;

    // Wrapping multiply: fast, but silently overflows when the true Q31.16
    // result exceeds int32. Use only where inputs are provably in range.
    constexpr Fixed16_16 operator*(Fixed16_16 r) const noexcept {
        return { static_cast<int32_t>((static_cast<int64_t>(raw) * r.raw) >> kShift) };
    }

    // Saturating multiply: clamps to [INT32_MIN, INT32_MAX] instead of wrapping.
    // Lockstep determinism needs a defined overflow result — a silent wrap
    // desyncs peers. The 64-bit product cannot itself overflow (|raw| < 2^31,
    // so |product| < 2^62), and the >>16 of a negative value is an arithmetic
    // shift (guaranteed since C++20). Clamp after the shift.
    constexpr Fixed16_16 mul_sat(Fixed16_16 r) const noexcept {
        const int64_t p = (static_cast<int64_t>(raw) * r.raw) >> kShift;
        constexpr int64_t lo = std::numeric_limits<int32_t>::min();
        constexpr int64_t hi = std::numeric_limits<int32_t>::max();
        return { static_cast<int32_t>(p < lo ? lo : (p > hi ? hi : p)) };
    }
};
```

**mdspan for tensors.** Use `std::mdspan` for contiguous storage with strided views when `__cpp_lib_mdspan` is available; otherwise keep an equivalent engine view. Verify code generation on each compiler rather than assuming parity.

**C++26 gates.** Linalg (`<linalg>`) and SIMD (`<simd>`) are horizon features. Gate with `__cpp_lib_linalg` / `__cpp_lib_simd` and keep the hand-rolled fallback. Don't bet the engine on them yet.

---

## 2. Spatial Data Structures

Wrong structure, wrong perf. Right structure, linear scaling to a million actors.

| Structure     | Build  | Query     | Best for                          | Avoid for                 |
|---------------|--------|-----------|-----------------------------------|---------------------------|
| BVH (SAH)     | O(n log n) | O(log n) | Static meshes, raycasts          | High-churn dynamics       |
| Loose octree  | O(n log n) | O(log n) | Mixed static/dynamic, VFX        | Deep non-uniform scenes   |
| k-d tree      | O(n log n) | O(log n) | Raytracing, point queries         | Frequent inserts          |
| Uniform grid  | O(n)   | O(1) avg  | Uniform density, particle soup   | Sparse / large worlds     |
| DBVT          | O(n)   | O(log n) | Dynamic physics broad-phase       | Static geometry           |

**BVH with SAH.** Surface Area Heuristic builds in O(n log n) via binned partitioning (16 bins, Wald 2007). Target a leaf cost of 4 primitives. Refit per frame for small motions (O(n)), rebuild every ~60 frames or when SAH degrades by 1.8x.

**Loose octree.** Each node's bounds are 2x its natural extent. Eliminates the "object straddles boundary" problem with zero re-insertion cost for sub-node-sized actors. Depth cap at 8 for a 16km world (final nodes ~62m).

**Decision rule.** Static geometry on disk = BVH. Dynamic actors = DBVT (Bullet-style). Particles / VFX = uniform grid sized to kernel radius. RTS units = loose octree with 4-deep LOD hierarchy for selection queries.

---

## 3. Frustum Culling

Target 2 million AABBs culled per ms on a single Zen2 core. Non-negotiable.

**Plane extraction.** Pull six planes from the view-projection matrix (Gribb-Hartmann). Normalize once. Cache per frame in persistent tier allocator (zero allocation during traversal).

**AABB vs plane.** Use the "center + extents" form. Compute signed distance from center; compare against projected extent along plane normal. SIMD 4 AABBs per iteration:

```cpp
// 4 AABBs, 6 planes -> 24 tests, ~18 cycles on AVX2
inline uint32_t cull_aabb_x4(const AABB* __restrict aabbs,
                             const Plane (&planes)[6]) noexcept {
    uint32_t inside_mask = 0xF;
    for (int p = 0; p < 6; ++p) { /* SIMD dot + cmp */ }
    return inside_mask;
}
```

**Hierarchical.** Traverse BVH top-down. If a node is fully inside, short-circuit (no per-leaf tests). If fully outside, prune. Partial — recurse. Parallelize with TBB `parallel_for` over top-level nodes; per-thread output in frame-scratch allocator, merged at the barrier.

**GPU compute culling.** For >500k instances, move to compute shader. Indirect draw via `ExecuteIndirect` / `vkCmdDrawIndirectCount`. CPU culling wins below ~50k instances due to dispatch overhead. Measure.

---

## 4. Physics Engine Integration

**Jolt.** A strong CPU rigid-body default with an island-parallel solver and broad-phase body layers. Jolt provides `JPH_CROSS_PLATFORM_DETERMINISTIC` and determinism diagnostics, but applications must still use the documented build flags and verify every supported architecture/compiler pair with replay hashes.

**PhysX 5.** GPU rigid bodies use a CUDA TGS path; PhysX also provides soft bodies, particles, vehicles, and articulations. Platform availability and licensing are SDK-specific—verify them rather than inferring support from the public PC distribution.

**Havok.** Historical gold standard. Licensing cost is real. Use on shipped franchises with existing content pipelines — don't start here in 2026.

**Integration rule.** Wrap the physics world behind a thin interface. Expose only `step(dt)`, `raycast`, `overlap`, and body handles. Never leak engine types into gameplay. Budget: 2.5ms for 2000 active rigid bodies on Zen2.

---

## 5. Collision Detection Pipeline

**Broad-phase.** Sweep-and-prune for low-churn scenes (buildings, statics). DBVT for high-churn (ragdolls, VFX). Output is candidate pairs into a frame-scratch `std::span<PairIndex>`.

**Narrow-phase.** GJK for convex-convex distance and contact; EPA for penetration depth (minimum translation vector). SAT for box-box (5-10x faster than GJK/EPA on pure OBBs). Sphere-X pairs are analytic — never invoke GJK. Production GJK/EPA is **delegated to the physics SDK** (Jolt/PhysX, §4), not hand-rolled here: the hard part is numerical robustness (degenerate/near-flat simplices, EPA polytope expansion termination, contact-point caching), which the SDK has already hardened. This file specifies the pipeline shape, not a from-scratch solver — so no incomplete GJK/EPA sketch is given.

**Contact manifold.** After narrow-phase, generate contact points via face-face clip (Sutherland-Hodgman), reduce to 4 points max (deepest + 3 maximizing area). Persistent manifold across frames via warm-starting: cache λ (Lagrange multiplier) per contact, re-apply as initial guess next tick. Solver convergence doubles.

**CCD.** Conservative advancement for fast movers (bullets, vehicles >80 km/h). Binary search TOI (time of impact) to tolerance 1e-4s. Only enable per-body flag — blanket CCD murders perf. Budget: 5% of bodies should have CCD on.

---

## 6. Advanced Simulation

**Cloth (XPBD).** Müller's Extended Position-Based Dynamics. Distance + bending + collision constraints. Stiffness as compliance `α = 1/k` (SI units, stable under dt changes). 10-20 solver iterations for shirts; 40+ for capes with self-collision. GPU path via compute shader, 64-thread groups per mesh patch.

**Fluid.** SPH for puddles and small volumes (<50k particles). PIC-FLIP hybrid for large bodies (rivers, ocean splash) — particle-to-grid advection eliminates numerical damping of pure PIC while keeping stability. Run on async compute queue.

**Destruction.** Voronoi fracture at asset time, runtime chunk graph with mass-spring bonds. Bond break threshold from material DB. Fast path: pre-baked fracture patterns (Blast-style). Cold path: runtime Voronoi via Bowyer-Watson when needed.

**Soft body.** Shape matching (Müller 2005) for gameplay-scale (goo, slime, plushies). FEM tetrahedral for hero assets (co-rotational linear, 500-5000 tets). Budget: one FEM hero character per scene.

---

## 7. Interpolation & Curves

**Cubic Bezier.** De Casteljau evaluation — numerically stable, no explicit power basis. 4 lerps for position, another 3 for tangent. Use for UI, camera splines, particle emitter paths.

**Catmull-Rom.** Interpolates control points (unlike Bezier). Tension parameter 0.5 for the uniform variant. Use for cinematic camera rails.

**B-splines (uniform cubic).** C² continuous; does not interpolate control points. Use for smooth animation curves where overshoot is forbidden.

**Spherical harmonics L2.** 9 coefficients per channel (27 floats RGB). Sufficient for diffuse indirect lighting probes. L3 (16 coeffs) only if you need glossy indirect — usually better to use radiance cache or DDGI instead.

**Noise.** Perlin gradient for terrain and organic textures. Simplex (Ken Perlin 2001) for >3D domains — lower computational complexity than classic Perlin. Worley/cellular for stone, scales, caustics. Precompute gradient tables in persistent allocator (256 entries, hash-indexed).

---

## 8. Dual Quaternions

Linear blend skinning collapses limbs at 90° joint bends ("candy wrapper"). Dual quaternion skinning eliminates it at ~1.3x cost.

**Representation.** Rotation `q_r` (unit quat) + translation encoded as `q_d = 0.5 * t * q_r` (quaternion multiply). Rigid transform encoded in 8 floats.

```cpp
struct DualQuat {
    Quat real; // rotation
    Quat dual; // 0.5 * t * real
};

inline DualQuat from_rot_trans(Quat r, Vec4 t) noexcept {
    DualQuat dq;
    dq.real = r;
    dq.dual = 0.5f * Quat{t.x, t.y, t.z, 0.0f} * r;
    return dq;
}
```

**Skinning.** Blend `q_r` components weighted by bone influence, renormalize, extract translation via `t = 2 * q_d * conj(q_r)`. Ship DQS for characters; stick with LBS for props where bulge is invisible.

**SLERP on dual.** For camera / motion blur interpolation between two DQs, SLERP the real part and LERP the dual. Bit-exact cross-platform results require disabling FMA here (see §9).

---

## 9. Deterministic Simulation

Determinism is a choice. You pay for it. It is worth it for rollback netcode, replay systems, lockstep multiplayer, and reproducible bug repros.

**Fixed timestep.** Gaffer's accumulator pattern:

```cpp
constexpr double kFixedDt = 1.0 / 60.0;
double accumulator = 0.0;
while (game_running) {
    const double frame = clock.tick();
    accumulator += std::min(frame, 0.25); // cap spiral-of-death
    while (accumulator >= kFixedDt) {
        sim.step(kFixedDt);
        accumulator -= kFixedDt;
    }
    const float alpha = static_cast<float>(accumulator / kFixedDt);
    render.interpolate(alpha);
}
```

**Floating point strictness.** Compile sim TU's with `-ffp-contract=off` / `/fp:strict` on Clang/MSVC. Disable FMA explicitly (`-mno-fma`) on any code path that must bit-match across x64 and ARM — FMA rounds once, separate mul+add rounds twice. Different results. Every platform, every time.

**Reciprocal estimates.** Hardware `rcp`/`rsqrt` estimate instructions may start from vendor-specific seed bits. A fixed Newton-Raphson count does not make them cross-architecture bit-identical. Deterministic simulation must use a software-defined seed/iteration sequence or a verified strict `sqrt`/division path; keep approximate SIMD helpers out of deterministic state updates.

**Transcendentals.** `sinf`, `cosf`, `expf` vary between libc implementations (glibc vs Windows CRT vs Bionic vs Switch SDK). Ship your own polynomial approximations in the sim. Degree-7 minimax polynomials are sufficient for all game purposes and are bit-identical by construction.

**Verification.** Run the sim on every target platform in CI against a reference trace (seed + input log). Hash the world state every 60 frames (xxhash3 over contiguous component arrays). Mismatch = determinism bug. Caught early is caught cheap.

**RNG.** Prefer a small explicitly specified generator such as PCG32 or xoshiro256**. `std::mt19937` itself is standardized, but its large state is often undesirable and standard-library distribution mappings are not portable. Own the distribution algorithms when bit identity matters.

---

## See Also
- `ANIMATION_AND_CHARACTER.md` — dual quaternion skinning integration, IK solvers
- `AUDIO_AND_SPATIAL.md` — Doppler math, HRTF convolution
- `NETWORKING_AND_MULTIPLAYER.md` — deterministic rollback, fixed-timestep sim on the wire
