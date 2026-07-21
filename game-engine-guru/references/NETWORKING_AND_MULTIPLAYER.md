# Networking and Multiplayer

## Table of Contents
1. Network Architecture Models
2. Deterministic Rollback Netcode
3. State Replication
4. Client-Side Prediction
5. Lag Compensation
6. Interest Management
7. Transport Layer
8. Server Meshing
9. Security
10. See Also

---

## 1. Network Architecture Models

**Client-server (authoritative).** The server is truth. Clients send inputs, receive state. Standard for shooters, MMOs, and anything cheat-sensitive. Latency = 1x RTT for server actions, 2x RTT for other-player actions without prediction. Operational cost: one server instance per match/shard.

**P2P.** No dedicated server. One peer is elected host (often the match creator or lowest-latency node). Used for fighting games (rollback), RTS lockstep, and cooperative experiences with low cheat stakes. Zero server cost; host-migration complexity; NAT traversal required (STUN/TURN).

**Server mesh (SpatialOS / Star Citizen).** World partitioned into shards, each owned by a different server node. Actors hand off across shard boundaries. Scales to thousands of concurrent players in a single shared world. Engineering cost is enormous — budget a dedicated team.

**Decision matrix:**

| Players | Cheat tolerance | Latency budget | Architecture                  |
|---------|-----------------|----------------|-------------------------------|
| 2-8     | High            | Any            | P2P lockstep or rollback      |
| 2-64    | Low             | <100ms         | Client-server authoritative   |
| 64-256  | Low             | <100ms         | CS with dedicated instance    |
| 500+    | Low             | <150ms         | Server mesh / sharded         |
| 10000+  | Low             | MMO-range      | Zoned CS with cross-zone svc  |

---

## 2. Deterministic Rollback Netcode

The gold standard for fighting games (Street Fighter 6, GGST, MK1) and increasingly for small-scale shooters (Rocket League uses a variant).

**GGPO model (Tony Cannon).** Each peer simulates locally with predicted remote inputs. When real remote inputs arrive, if prediction was wrong, rewind to the last confirmed state and re-simulate up to the present using the real inputs. Player sees local actions with zero added latency; misprediction is invisible if rollback is <4 frames.

**Re-simulation budget.** At 60 Hz, eight frames represent 133 ms of history, not eight free simulation steps. Budget worst-case recovery as `(frame budget - render/present/current-tick work) / rollback depth`, keep full-depth events rare, and amortize recovery only if the game can tolerate delayed convergence.

**State serialization.** Every frame, hash the complete simulation state (xxhash3 over contiguous component arrays). Every N frames (N=30 typical), serialize a full snapshot into a ring buffer. Rollback reads the nearest snapshot and replays from there.

```cpp
struct NetFrame {
    uint32_t frame_id;
    uint64_t state_hash;           // cross-peer verification
    std::span<const std::byte> snapshot; // optional, every N frames
    PlayerInput inputs[kMaxPlayers];
};

// Each frame, after sim:
const uint64_t h = xxhash3_bulk(world.component_soa());
if (h != remote_reported_hash[frame_id]) desync_handler();
```

**Checksum verification.** Hash mismatch between peers = desync. Log the frame, dump state, and show a user-facing reconnect. Desyncs are bugs — hunt every one.

**Constraints.** Simulation must be deterministic across the declared peer matrix. Cross-architecture play needs stricter math/RNG rules than same-binary peers; see `PHYSICS_MATH_AND_SIMULATION.md` §9.

---

## 3. State Replication

**ECS-aware.** Replicate component deltas, not whole entities. Each replicated component declares its dirty bits. Per tick, collect dirty components, pack as a bitfield of changed fields + changed values.

```cpp
struct ReplicatedTransform {
    Vec3 pos;        // field 0
    Quat rot;        // field 1
    Vec3 vel;        // field 2

    static constexpr uint8_t kFieldCount = 3;
    uint8_t dirty_mask = 0;

    void write_delta(BitWriter& w) const noexcept {
        w.write_bits(dirty_mask, kFieldCount);
        if (dirty_mask & 0x1) w.write_vec3_quant(pos, 0.001f);
        if (dirty_mask & 0x2) w.write_quat_smallest3(rot);
        if (dirty_mask & 0x4) w.write_vec3_quant(vel, 0.01f);
    }
};
```

**Quantization.** Position: 0.1mm (0.0001m) precision → 20-24 bits per axis. Rotation: smallest-three quat — drop the largest component, store a 2-bit largest-component index + three 16-bit components = 50 bits total (encode/decode in `ANIMATION_AND_CHARACTER.md` §8). Velocity: coarser, 0.01 m/s → 16 bits per axis. Cuts bandwidth 4-6x over raw floats.

**Priority / relevancy.** Score = `base_importance + visibility_bonus - distance_penalty - time_since_last_update`. Per tick, per client, sort replicated entities by score, transmit top N that fits the bandwidth budget. Distant players update at 5-10 Hz; nearby combatants at 30-60 Hz.

**Eventual consistency.** Not every tick for every entity. Guarantee "within 500ms for distant, within 33ms for nearby." Use sequence numbers to drop stale updates on the receiver.

---

## 4. Client-Side Prediction

**Input buffering.** Circular buffer (128 entries @ 60Hz = 2.1s history). Client records input per tick with a frame ID, sends last 3-5 inputs per packet for redundancy against packet loss.

**Local sim.** Run the same authoritative movement code on the client. Apply local input, advance local pawn. Player sees action at t+0, not t+RTT.

**Reconciliation.** Server sends authoritative state for your pawn tagged with the last-processed input's frame ID. Client compares local predicted state at that frame ID against server state. If different (beyond tolerance), rewind local state to server's, re-apply all inputs from that frame forward.

```cpp
void on_server_state(ServerPawnState s) noexcept {
    const auto& pred = prediction_history[s.last_input_frame];
    if (distance(pred.position, s.position) < 0.05f) return; // within tolerance
    // rewind
    pawn.state = s;
    // replay from s.last_input_frame + 1 to current
    for (uint32_t f = s.last_input_frame + 1; f <= current_frame; ++f) {
        pawn.step(input_history[f], kFixedDt);
    }
}
```

**Smoothing.** On mispredict, don't snap — smooth position error to zero over 200-300ms with an exponential or critically-damped spring. Player sees a tiny drift, not a teleport. Rotation and animation state follow the same smoothing.

---

## 5. Lag Compensation

Client shoots at a target the client sees. By the time the packet arrives at the server, the target may have moved. Two fixes: interpolation delay for remote entities, rewind-and-test on the server for shots.

**Snapshot history.** Server keeps 1 second of per-entity position/collider snapshots (ring buffer). 60Hz × 1s × 2000 entities × 64 bytes = 7.3 MB — fits in L3 easily.

**Rewind-and-test.** Client tags fire events with its perceived server time. Server rewinds target colliders to that time, re-runs the hit test, applies damage, restores. Classic Valve hit-reg (Source / CS2). Budget: 4-6μs per rewound raycast.

```text
// Pseudocode: server-side rewind — save present, query the past, always restore.
resolve_shot(shooter, ray, client_time):
    t    = clamp(client_time, now - history_len, now)   // reject ancient / future times
    snap = interpolate(history, t)                       // two bracketing snapshots -> lerp
    saved = {}
    for e in broadphase(ray, snap):
        saved[e] = e.collider_xform                      // 1) save present
        e.collider_xform = snap[e]                       // 2) rewind to t
    hit = raycast(ray)                                   // 3) query in the past
    for (e, xform) in saved: e.collider_xform = xform    // 4) restore present (ALWAYS)
    if hit: apply_damage(hit.entity, shooter.weapon, hit)
    return hit
```

**Interpolation delay.** Remote entities (other players, AI) render at `server_time - interp_delay`, where interp_delay = 100-150ms. You always have two snapshot frames bracketing render time; LERP between them. Tradeoff: 100ms of visual lag for smooth, pop-free remote motion.

**Extrapolation.** Don't. For game state, interpolation from behind always beats extrapolation from ahead. Only extrapolate VFX (debris, particles) where accuracy is invisible.

---

## 6. Interest Management

The server is not sending every entity's state to every client. That's O(N²) bandwidth and it doesn't scale past ~32 players.

**Spatial partitioning.** Grid (for open worlds) or octree (for verticality). Each actor tagged with a cell. Per-client query: actors in cells within the client's interest radius.

**Distance LOD for updates:**
- 0-20m: 60 Hz, full state
- 20-60m: 30 Hz, position + rotation
- 60-150m: 10 Hz, position only
- 150m+: 2 Hz or event-driven only

**Area-of-interest shape.** Circle (radius) is the default. View-frustum AOI (wider in front, narrow behind) increases apparent density in the screen area but risks rubber-banding on quick turns. Ship circular with slight bias toward velocity vector.

**Stream-in, stream-out.** Entity enters AOI → send full state snapshot once, then deltas. Entity leaves AOI → send "despawn" event, client removes local proxy. Hysteresis (enter at 150m, leave at 170m) prevents thrash at the boundary.

```text
// Pseudocode: per-client relevancy update with enter/update/leave and hysteresis.
// R_enter < R_leave (e.g. 150m / 170m) so an entity on the boundary can't thrash.
update_interest(client):
    near = query_cells(client.pos, R_enter)      // candidate set within the inner radius
    prev = client.relevant
    for e in (near - prev):                      // ENTER: newly relevant
        send_full_snapshot(client, e)
    for e in prev:                               // UPDATE or LEAVE
        if dist(client, e) > R_leave:
            send_despawn(client, e)              // LEAVE: crossed the outer radius
        else:
            send_delta(client, e, rate_for(dist(client, e)))   // UPDATE at distance-LOD rate
    client.relevant = (prev ∪ near) filtered to dist ≤ R_leave
```

---

## 7. Transport Layer

**UDP.** Never TCP for real-time game state. TCP head-of-line blocking will ruin your day on every packet loss.

**Reliability layer on top of UDP.** Two channels:
- Unreliable: state snapshots, input (older data is worthless on arrival)
- Reliable ordered: chat, trade, match events, entity spawns/despawns

Reliable layer = sequence numbers + ACK bitfields (32-bit bitfield covers last 32 packets). Retransmit if unacked after RTT + slack. Implementation: Gaffer's "Reliability over UDP" or ENet.

**Packet aggregation.** One UDP datagram = many game messages. Target packet size 1200 bytes (safe MTU). Aggressive: pack every replicated component, every event, every chat, every ACK into one packet per tick per direction.

**Congestion control.** Start with fixed send rate (30-60 Hz). Add windowed BBR-lite if you ship variable-quality streams. Detect loss spike → back off send rate, trim replication priority list. Don't reinvent TCP.

**Bandwidth budget.** 64 KB/s per client is a reasonable AAA default. Mobile/Switch target 32 KB/s. Player-facing bandwidth slider for capped connections. Budget per client per tick at 30Hz = ~2 KB/tick outbound from server, ~200 B/tick inbound input.

```cpp
struct PacketHeader {
    uint16_t sequence;          // this packet's seq
    uint16_t ack;               // latest received seq from peer
    uint32_t ack_bitfield;      // ack - 1 .. ack - 32
    uint16_t channel_id;
};
```

---

## 8. Server Meshing

A single game server can't simulate an entire persistent world with 1000+ concurrent players at full fidelity. Mesh it.

**Distributed actors.** Authoritative simulation of actor A lives on one server node. Other nodes holding actor A in their AOI have a read-only proxy, kept fresh by the authoritative node's replication.

**Entity handoff.** Actor crosses a world region boundary. Authority migrates: source node serializes state, destination node deserializes, ACK confirms, source drops. Handoff window ~100ms during which both nodes co-simulate for continuity. Implemented as a two-phase commit over the backbone.

**Boundary streaming.** 50-100m overlap region around each boundary where two nodes have dual authority for reads (both have up-to-date state of boundary actors). Writes still go to the single authoritative node. Prevents seams.

**Backbone.** Internal traffic between nodes is not UDP game protocol — it's high-bandwidth TCP/QUIC over the datacenter fabric. Reliability matters more than latency here (both are <1ms LAN).

**Scale.** A 4km × 4km region with 16 nodes (1km²/node) handles 2000-4000 concurrent players at AAA tick rate. Star Citizen, Dual Universe, Pax Dei all ship variants.

---

## 9. Security

**Server-authoritative validation.** Never trust client-reported position, velocity, damage, pickup, or inventory. Client sends input; server computes state. If the client tells you it's at (1000, 1000) after starting at (0, 0) one frame ago, the client is lying.

**Speed / teleport detection.** Per-tick, check `|pos_new - pos_prev| <= max_speed * dt * slack`. Violations → snap-back, log, flag. Three flags in 60s → kick. Ten flags in 5min → ban review.

**Anti-cheat.** Integrity checks (binary hash, kernel-level driver for PC — EasyAntiCheat / BattlEye / Vanguard). Heuristic detection (inhuman aim consistency, impossible reaction times). Server-side statistical flags (headshot ratio >80% over 100 encounters). No single silver bullet — defense in depth.

**Encryption.** DTLS 1.3 over UDP for all game traffic. Prevents trivial packet inspection and injection. Platform-provided libraries (Sony NetCL, Microsoft XSAPI) handle cert pinning and console trust. On PC, bundle OpenSSL / BoringSSL.

**Rate limiting.** Token bucket per connection: 200 messages/sec capacity, 60/sec refill. Exceeding → drop + flag. Prevents CPU-exhaustion DoS via input spam.

**Replay protection.** Every packet carries a monotonic sequence number inside the encrypted payload. Server maintains a sliding window of accepted sequences. Duplicates dropped, ancient packets rejected. DTLS gives this for free — don't roll your own.

**Never ship debug RPCs in release builds.** Teleport, give-all-items, god-mode RPCs that worked for QA are "how did a streamer break our economy in 6 hours" on launch day. Strip with `#ifdef` and a release build verification step.

```cpp
[[nodiscard]] std::expected<void, NetError>
handle_move_cmd(ClientId id, MoveCmd cmd) noexcept {
    auto& pawn = world.get_pawn(id);
    const float max_dist = pawn.max_speed * kFixedDt * 1.15f; // 15% slack
    if (distance(cmd.target_pos, pawn.position) > max_dist) [[unlikely]] {
        flag_client(id, CheatFlag::SpeedHack);
        return std::unexpected(NetError::InputRejected);
    }
    pawn.queue_input(cmd);
    return {};
}
```

---

## See Also
- `PHYSICS_MATH_AND_SIMULATION.md` — fixed-timestep determinism, fixed-point math for lockstep
- `ANIMATION_AND_CHARACTER.md` — pose quantization for replication, compressed quat on the wire
- `AUDIO_AND_SPATIAL.md` — voice chat integration, replicated audio events
