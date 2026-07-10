# 03 — Architecture: two Pis talking

## Roles

- **Slate = Conductor = state authority.** It owns all state, runs the evolution loop, calls the image-gen API, and drives its own e-paper. It naturally lives here because the heavy, slow work (generation + display) is here, and keeping state next to the output avoids a class of races.
- **Spark = Controller = thin client.** It renders LEDs from state it receives and emits button events. It holds only *ephemeral* local animation state (scroll position, breathing phase).

One authority, one follower. No distributed-consensus headaches.

## Networking: the options, and a recommendation

You asked to discuss protocols. Here's the honest landscape for "two Pis on the same LAN, one authority, small JSON messages, needs to feel instant":

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **WebSocket + JSON** | Bidirectional, trivial to debug (open it from a laptop browser), no broker, one dependency, reconnect is easy | You write your own reconnect/heartbeat (small) | **Recommended for v1** |
| **MQTT (mosquitto broker on Slate)** | Pub/sub, *retained* state topics (Spark joins late → instantly gets current state), *last-will* (device drop is detectable), scales to a 3rd device/phone for free | A broker to install + run; slightly more moving parts | **Recommended upgrade path** once you add devices |
| Plain TCP + newline-JSON | Minimal deps | You reinvent framing, reconnect, discovery | Skip |
| UDP broadcast | Great for discovery/heartbeat | Lossy; bad for authoritative state | Use *only* for discovery/heartbeat if you want |
| Redis pub/sub | Nice if you already run Redis | Overkill on a Zero 2 | Skip |
| ZeroMQ / gRPC | Powerful | Heavier than this needs | Skip |

**Plan: build v1 on WebSockets, keep the message layer swappable.** If you later want retained-state + easy multi-device, drop in MQTT behind the same message interface. Design the transport as a thin `Bus` abstraction (`send(msg)`, `on(msg_type, handler)`) so the app code doesn't care which is underneath.

### Discovery (don't hardcode IPs)

Use **mDNS / zeroconf** (avahi is already on Raspberry Pi OS). The Conductor advertises itself; the Controller resolves it by name:

- Conductor advertises `_flyball._tcp` (or simply is reachable at `slate.local`).
- Controller connects to `ws://slate.local:8765`.
- Fallback: a `FLYBALL_CONDUCTOR_HOST` env var / config value overrides discovery.

### Resilience

- **Heartbeat** every ~2s each way; if the Controller misses N beats it shows a "disconnected" LED pattern (e.g. slow red sweep) and keeps retrying with backoff.
- **Auto-reconnect** on the Controller; on reconnect it sends `hello` and the Conductor replies with a full `state` snapshot (this is exactly the case MQTT retained messages handle for free).
- Conductor is stateless-restart-safe: persist the sentence stack + queue to a small JSON file so a reboot mid-session recovers.

## Message protocol (WebSocket JSON, v1)

All messages: `{"type": "...", ...}`. Keep them small and flat.

**Controller → Conductor**

```json
{"type": "hello", "device": "spark", "fw": "0.1.0"}
{"type": "button", "btn": "A", "event": "press"}      // event: press | release | hold
{"type": "button", "btn": "Y", "event": "hold", "ms": 800}
{"type": "ping"}
```

**Conductor → Controller**

```json
// Full snapshot — sent on connect and after big changes
{"type": "state",
 "channel": "subject",           // active channel id
 "channel_color": [0,200,80],
 "option_index": 3,
 "option_count": 5,
 "candidate": "Detective",       // text to scroll on the LEDs
 "committed": true,              // is the candidate already in the stack?
 "engine": {"loop": true, "speed_s": 12, "operator": "lang", "queue_depth": 2},
 "mode": "word"                  // word | engine
}

// Small nudges when only one thing changed (optional optimisation)
{"type": "patch", "candidate": "Silent Dancer", "option_index": 4}

{"type": "pong"}
{"type": "toast", "text": "SENT", "color": [255,180,0]}   // brief Spark flash/scroll
```

Design notes:

- The Conductor sends **semantic state**, not pixel data. The Spark decides how to render (scroll speed, breathing, pips). This lets the Spark animate smoothly at 30–60fps locally without any network round-trips per frame — critical for "instant."
- `patch` is just an optimisation; you can ship v1 with only `state` and it'll be fine on a LAN.
- Button semantics live on the **Conductor**, not the Spark. The Spark says "B was pressed"; the Conductor decides that means "next option in the active channel." This keeps all the logic (which is genuinely your Story Builder's `button_next/prev/select/back`, promoted to a networked service) in one place.

## Boot straight into the app (systemd)

Each Pi runs one enabled service that auto-restarts. Examples in `deploy/`:

- `slate-conductor.service` → `ExecStart=/usr/bin/python3 -m conductor` on the Inky Pi.
- `spark-controller.service` → `ExecStart=/usr/bin/python3 -m controller` on the Unicorn Pi.

Both `Restart=always`, `After=network-online.target`, `WantedBy=multi-user.target`. Secrets (image-gen API key) and config (conductor host, channel colours) live in an env file (`/etc/flyball.env`) or a `config.toml`, not in code. `raspi-config` → enable SPI (both HATs use SPI) and set unique hostnames (`slate`, `spark`) so mDNS names are clean.

## Simulation mode (build it on your Mac first)

Carry over the Story Builder's pattern (`IS_SIMULATION = platform.system() != "Linux" ...`). Both roles get a headless/sim backend, and they talk over `localhost:8765`:

- **Spark sim:** render the 17×7 matrix to a terminal (ANSI colour blocks) or a tiny pygame/Tk window; map keyboard `a/b/x/y` to buttons (mirrors your Story Builder's `a/b/c/d` keys).
- **Slate sim:** use your existing `InkyMock` — build the PIL image and `.show()` it; map keyboard `a/b/c/d` to buttons.
- Run `python -m conductor` and `python -m controller` in two terminals on the Mac; they discover each other on localhost. The entire UX — channels, cycling, committing, queue, loop, evolution — is testable with zero hardware, and image gen still works (it's just an API call).

This means Claude Code can build and iterate the whole system on the Mac, and the Pi step is mostly "flip sim off, wire GPIO, write two systemd units."

## Abstraction seams (so this stays swappable)

- `Bus` — transport (WebSocket now, MQTT later).
- `Display` — `SlateDisplay` (Inky) / `SlateMock`, `SparkDisplay` (Unicorn) / `SparkMock`.
- `Buttons` — GPIO (gpiod / gpiozero) / keyboard sim.
- `ImageBackend` — pluggable generator (see `04-prompt-engine.md`).
- `Evolver` — pluggable prompt-mutation strategy (rule-based / LLM-assisted).
