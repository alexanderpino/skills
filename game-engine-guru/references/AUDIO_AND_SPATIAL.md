# Audio and Spatial Systems

## Table of Contents
1. Audio Engine Architecture
2. 3D Spatialization
3. Acoustic Propagation
4. Audio Material System
5. Voice Management
6. Dynamic Mixing
7. Streaming Audio
8. Multi-Listener
9. See Also

---

## 1. Audio Engine Architecture

Audio is a hard-real-time problem masquerading as an afterthought. The audio callback fires at ~2.67 ms intervals (128 samples @ 48 kHz) and if you miss it once, the player hears a click that will haunt them through every YouTube review. Design accordingly.

**Audio graph (DAG).** Nodes produce float buffers; edges carry audio. Leaves are voice sources (one-shot / streamed / synth). Interior nodes are DSP effects. Sinks are output buses. The graph is compiled to a flat execution schedule once per mix configuration change — no virtual dispatch in the per-sample loop.

**DSP pipeline.** Push-based: the driver calls your render callback; you fill its output buffer in one pass. Do NOT allocate inside the callback. Do NOT take contested locks — only single-writer / single-reader lock-free queues between game thread and audio thread. RT-safe command queue (SPSC ring) for parameter changes, voice start/stop, bus mutes.

**Bus routing.** Master → (Music, SFX, Voice, Ambience, UI). Each bus has gain, optional compressor, and a send to reverb if configured. Bus tree is data-driven via JSON/YAML at load time. Mute/solo at the bus level costs zero in the mix loop — bus gain is multiplied into the voice post-pan gain.

**Middleware.** Wwise and FMOD are the defaults. Wwise scales better for AAA (profiler, authoring, asset pipeline); FMOD is faster to integrate for mid-scale. Both expose C APIs — wrap them behind a thin `IAudio` interface returning `std::expected`. If you ship in-house audio (Naughty Dog, Insomniac, id Software, Guerrilla), expect 18 engineer-months minimum.

```cpp
struct AudioEngine {
    [[nodiscard]] std::expected<VoiceHandle, AudioError>
    play(SoundRef s, const PlayParams& p) noexcept;

    [[nodiscard]] std::expected<void, AudioError>
    stop(VoiceHandle h, float fadeMs = 10.f) noexcept;

    // game-thread only. pushed to audio thread via SPSC queue.
    void set_parameter(VoiceHandle h, ParamId id, float v) noexcept;
};
```

---

## 2. 3D Spatialization

**HRTF.** Head-Related Transfer Function. Per-ear impulse response measured (or simulated) as a function of azimuth/elevation. Convolve the mono source with left/right HRIR and you get binaural output. Use for headphone output. Partitioned convolution (Gardner 1995): 128-sample first block, larger blocks later — amortizes FFT cost across frames.

Budget HRTF voices separately from the total voice pool. A title might render 16-64 high-priority binaural voices and virtualize or pan the rest, but the correct count depends on filter length, partitioning, platform DSP, and the audio frame budget.

**Ambisonics.** Sound field encoded as spherical harmonics. First-order (FOA, 4 channels) for ambient beds. Third-order (3OA, 16 channels) for precise positioning of non-point sources. Rotate the field with the listener's head orientation (cheap — block-diagonal rotation matrix). Decode to HRTF virtual speakers at output.

**Distance attenuation.** Three standard curves:
- Linear: `gain = clamp(1 - (d-dmin)/(dmax-dmin), 0, 1)` — predictable, worst sounding
- Log: `gain = dmin / d` past `dmin`, clamped at `dmax` — physically accurate, long tail
- Inverse (curve-based): sound designer authors curve, engine evaluates — ship this

**Doppler.** Project both velocities onto a single axis and pitch-shift. Fix the convention explicitly or you will invert it: let `u = normalize(source_pos − listener_pos)` (the **listener→source** axis). Project *both* velocities onto that same `u`:

- `vL = dot(listener_velocity, u)` — listener velocity along listener→source
- `vS = dot(source_velocity,   u)` — source velocity along listener→source

Then `f' = f * (c + vL) / (c + vS)` with `c = 343 m/s`. With this convention, *closing the gap raises pitch*: a listener moving toward the source gives `vL > 0` (numerator up); a source moving toward the listener moves opposite `u`, so `vS < 0` (denominator down). Both push `f'` up, as expected. Clamp the denominator away from zero (guard `c + vS`) before dividing, then cap the final shift at [0.5, 2.0] to avoid "bee noise" when objects graze the listener. Disable for UI sounds, menu music, and narrative VO.

---

## 3. Acoustic Propagation

**Occlusion (ray-based).** Fire 16-64 rays from source to listener in a cone. Hit count drives low-pass filter cutoff and gain. 64 rays per source per 100ms is plenty — not per frame. Cache per source, invalidate on movement >0.5m.

**Diffraction (portal-based).** Precomputed portal graph over rooms. Audio travels through portals, losing energy per portal and accumulating path length. A* from source room to listener room through the portal graph gives effective path length for delay and attenuation. Real-time geometric diffraction (UTD — Uniform Theory of Diffraction) exists in research engines; portal graphs ship.

**Transmission.** Sound passing through walls. Material-driven. Transmission gain + low-pass filter per material per octave band. Sum with the diffracted path at the output.

**Reverb.** Two techniques, both shipped:
- Convolution with impulse response (IR). Pre-recorded or wave-simulated (Project Acoustics / Steam Audio bake). Realistic but static.
- FDN (Feedback Delay Network). 8-16 delay lines with feedback matrix + per-line low-pass. Parametric, cheap, dynamic. Use for real-time room state changes.

Steam Audio / Project Acoustics offload precompute to the editor; runtime is an IR lookup per source per room. Ship this for indoor-heavy titles.

---

## 4. Audio Material System

Per-material properties, stored in the same material DB used by rendering and physics:

| Property       | Typical range | Unit            |
|----------------|---------------|-----------------|
| Absorption     | 0.0 - 1.0     | fraction per octave band |
| Transmission   | 0.0 - 1.0     | fraction per octave band |
| Scattering     | 0.0 - 1.0     | fraction per octave band |
| Roughness      | 0.0 - 1.0     | for impact sound variant selection |

**Octave bands.** 8 bands are standard: 63, 125, 250, 500, 1000, 2000, 4000, 8000 Hz. Store absorption as 8 × float16 (16 bytes per material). Dot-product the material vector with the ray-path energy vector to get transmitted energy.

**Impact sounds.** Material-pair table: `{surfaceA, surfaceB} -> SoundRef`. 20 surfaces → 210 entries (upper triangle). Randomize among 3-5 variants per pair to avoid repetition. Randomize pitch ±5% and gain ±2 dB on every trigger.

---

## 5. Voice Management

**Voice pool.** A preallocated pool around 256 voices is a plausible starting point, not a standard. Establish separate budgets for active decode, DSP, HRTF, ambience, music, UI, and virtual voices from target-platform profiling.

**Priority stealing.** When the pool is full and a new voice is requested:
1. Score every active voice: `score = importance - distance_attenuation_dB - age_seconds * 0.5`
2. If the requested voice's score > worst active, steal that slot.
3. Fade out the stolen voice over 20ms to avoid click.

Importance is authored per-asset (dialogue=10, weapon fire=8, footstep=3, ambient leaf=1).

**Virtualization.** Voices below the audibility threshold (gain < -60 dB) are suspended, not stolen. Keep their playback position ticking; when they become audible again, resume. Essential for long ambient loops and looping emitters.

```text
// Pseudocode: voice lifecycle — Active ⇄ Virtual, plus steal on pool-full request.
score(v) = v.importance - v.attenuation_dB - v.age_seconds * 0.5

request_voice(new):
    if have_free_slot(): return start(new, take_free_slot())
    worst = argmin(active_voices, key=score)
    if score(new) > score(worst):
        fade_out(worst, 20ms); recycle(worst); return start(new, worst.slot)
    return DROP(new)                         // not worth a slot

tick_voice(v):                               // once per mix block
    if v.state == Active  and v.gain_dB <  -60: v.state = Virtual   // suspend decode/DSP
    if v.state == Virtual and v.gain_dB >= -60 and have_free_or_stealable():
        v.state = Active                     // resume at the position that kept ticking
    if v.state == Virtual: advance_position(v)   // clock only, zero decode/DSP cost
```

**Fade on steal.** 20ms linear ramp to zero before reusing the voice slot. Zero clicks, zero pops. Non-negotiable.

---

## 6. Dynamic Mixing

**Ducking (sidechain compressor).** Dialogue bus sends a sidechain signal to the music bus compressor — music dips 6 dB when anyone speaks. Attack 50ms, release 300ms. Data-driven threshold per scene.

**State snapshots.** Named mix states (Explore, Combat, Stealth, Menu, Cinematic). Each snapshot stores per-bus gain, per-bus filter cutoff, per-send amount. Cross-fade between snapshots over 500-1500ms on state change. Sound designers own the snapshot data.

**RTPC (Real-Time Parameter Control).** Game-thread parameter (e.g., `health`, `tension`, `speed`) drives audio parameters via authored curves. Push parameter updates through the SPSC queue at game rate; interpolate on the audio thread.

**Cross-fading.** Stem-based music: tracks have parallel instrument stems (drums, bass, melody, tension). Combat tension increases melody stem gain, decreases ambient pad stem. Musically coherent transitions without pre-baked transitions for every combo.

---

## 7. Streaming Audio

**Ring buffer.** 2-second ring per stream. Read position (audio thread) chases write position (IO thread). Underrun = silence + click. Never underrun.

**Seamless looping.** Loop points authored at sample-accurate positions. Optional 20ms crossfade between end and start for imperfect loops (wind, rain, machines). Detect zero-crossings during authoring for pop-free hard loops.

**Cross-fade between streams.** Music transitions: two streams decoding in parallel for ~2s during the crossfade window, then deallocate the old stream's ring. Budget for one concurrent extra stream on memory-constrained targets (Switch 2).

**Codec.** Vorbis (legacy), Opus (modern, variable bitrate, better quality/bitrate), XMA (Xbox native, hardware-decoded), AT9 (PS5 native, hardware-decoded). Use platform-native codecs for music and long VO — hardware decode saves CPU. Opus for cross-platform, short-form, or web streaming.

---

## 8. Multi-Listener

Split-screen, shared-screen local co-op, and some VR configurations have >1 listener.

**Per-listener context.** Each listener has position, orientation, velocity, and a local bus output. Each voice's spatialization runs per listener, summed (or routed per screen region) into the listener's output.

**Attenuation to nearest listener.** For a single shared mix (2-player split-screen on one speaker set), pick min distance across listeners for attenuation. Pan averaged (vector sum of per-listener pan) — avoids "sound pulls toward player 1 only." Don't sum gains across listeners; that doubles loud sounds in co-op.

**Per-screen output.** VR with per-eye / per-ear routing, or hardware with 4 separate headphone outs (older 4-player couch co-op), runs a full spatialization per listener. 4x cost. Budget voice pool accordingly (64 voices per listener × 4 listeners = 256).

**Cinematic override.** During cutscenes, collapse to a single cinematic listener regardless of player count. Sound designers author in mono-listener space; don't force them to mix for N.

---

## See Also
- `PHYSICS_MATH_AND_SIMULATION.md` — Doppler velocity sourcing, raycast for occlusion
- `ANIMATION_AND_CHARACTER.md` — footstep triggers from foot IK plant events, lip sync from audio
- `NETWORKING_AND_MULTIPLAYER.md` — voice chat integration, replication of audio events
