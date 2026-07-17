# Flyball M0–M1 Implementation Summary

## What Was Built

**M0 + M1 complete.** Full two-handed WebSocket bus + state machine + terminal/e-paper mocks running in macOS simulation.

- ✅ **WebSocket Bus** — Conductor (Slate authority) server on `localhost:8765`, Controller (Spark client) connects and round-trips `hello` / `state` / `button` / `ping`–`pong` messages.
- ✅ **State Machine** — Channels (Subject/Context/Style/Engine), option lists loaded from `shared/data/word_blocks.json`, buttons trigger prev/next/commit/shift logic.
- ✅ **Spark Mock** — 17×7 ANSI terminal matrix: colour bar (row 0) + position pips (row 1) + two-line scrolling text (rows 2–6).
- ✅ **Slate Mock** — PIL image with sideways menu strip (A/B/C/D labels) + candidate/sentence ribbon at bottom.
- ✅ **Keyboard Sim** — Spark responds to `a/b/x/y` keys; Conductor responds to `a/b/c/d` keys. Daemon threads, non-blocking.
- ✅ **Full Flow** — Pick channel on Slate (a/b/c/d) → cycle/commit options on Spark (a/b/x/y) → state broadcasts → both displays update.
- ✅ **Tests** — 27 tests pass: message schema, state machine, WebSocket round-trip, display rendering, end-to-end integration.

## Architecture

```
Conductor (Slate authority)
  │
  ├─ WebSocketServer (localhost:8765)
  ├─ ChannelRegistry (state machine)
  │  ├─ Channel: subject, context, style, engine
  │  └─ Options loaded from word_blocks.json
  ├─ InkyMock (PIL image render)
  └─ KeyboardListener (daemon: a/b/c/d → button events)

Controller (Spark client)
  │
  ├─ WebSocketClient (connects to server)
  ├─ SparkMock (17×7 ANSI terminal render)
  └─ KeyboardListener (daemon: a/b/x/y → button events)

Bus: WebSocket + JSON (swappable for MQTT later)
Interfaces: Bus, Display, Buttons, ImageBackend, Evolver
```

## File Structure

```
flyball/
├── shared/
│   ├── config.py (env loader)
│   ├── messages.py (Pydantic message schema)
│   ├── bus_websocket.py (WebSocket server/client)
│   ├── data/
│   │   └── word_blocks.json (seed options)
│   └── interfaces/
│       ├── bus.py (abstract)
│       ├── display.py (abstract)
│       ├── buttons.py (abstract)
│       ├── image_backend.py (stub)
│       └── evolver.py (stub)
├── conductor/
│   ├── __main__.py (entry point)
│   ├── conductor.py (server + state + handlers)
│   ├── state_machine.py (channels + stack)
│   ├── display.py (InkyMock + SlateDisplay)
│   └── buttons.py (KeyboardListener)
├── controller/
│   ├── __main__.py (entry point)
│   ├── controller.py (client + render loop)
│   ├── display.py (SparkMock)
│   └── buttons.py (KeyboardListener)
├── tests/
│   ├── test_messages.py
│   ├── test_state_machine.py
│   ├── test_bus_integration.py
│   ├── test_display_mocks.py
│   ├── test_buttons.py
│   └── test_integration_e2e.py
├── requirements.txt
└── M0-M1-SUMMARY.md (this file)
```

## How to Run

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Terminal 1: Start Conductor (Slate)

```bash
python -m conductor
```

Expected output:
```
Running in SIMULATION mode
Starting Conductor server...
WebSocket server listening on ws://localhost:8765
KeyboardListener (slate) ready. Press keys: ['a', 'b', 'c', 'd']
```

### Terminal 2: Start Controller (Spark)

```bash
python -m controller
```

Expected output:
```
Running in SIMULATION mode
Connecting to Conductor at localhost:8765...
Connected to ws://localhost:8765
KeyboardListener (spark) ready. Press keys: ['a', 'b', 'x', 'y']

Spark 17×7 Mock — Channel: SUBJECT

  █ ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄ █
  █ ●○○○○             █
  █ Private Eye  Priv █
  █                   █
  █                   █
  █                   █
  █                   █
```

## Two-Handed Flow Example

1. **Terminal 2 (Spark):** Press `b` → cycles to next Subject option ("Silent Dancer")
2. **Terminal 2 (Spark):** Press `b` again → cycles to "Street Hustler"
3. **Terminal 2 (Spark):** Press `x` → commits "Street Hustler" to Subject channel
4. **Terminal 1 (Conductor):** Press `b` → switches to Context channel
5. **Terminal 2 (Spark):** Display updates to blue (Context colour), shows first Context option
6. **Terminal 2 (Spark):** Press `b b` → cycle to "Neon Bar"
7. **Terminal 2 (Spark):** Press `x` → commits Context
8. **Terminal 1 (Conductor):** InkyMock PIL image shows sideways menu, sentence ribbon updates

## What's Stubbed for M2

- **ImageBackend** — M2 adds real image generation (hosted API or local SD/ComfyUI)
- **Evolver** — M2 adds prompt mutation operators (SWAP, LANG, LTR, +CON, -CON, etc.)
- **Engine Channel** — SEND button, loop control, queue management (plumbing in place, logic TBD)
- **Real Hardware** — GPIO listeners and Unicorn HAT / Inky Impression drivers (stubs ready, hardware integration in M4)

## Swappable Interfaces

All behind abstract base classes — no app code changes needed to swap:

- `Bus` → WebSocket (M0) → MQTT (future)
- `Display` → InkyMock / SparkMock (sim) → Real Inky / Unicorn (M4)
- `Buttons` → KeyboardListener (sim) → GPIOListener (M4)
- `ImageBackend` → Stub (M1) → Hosted API / Local SD (M2)
- `Evolver` → Stub (M1) → Rule-based / LLM-assisted (M2/M3)

## Testing

Run all tests:
```bash
pytest tests/ -v
```

Run specific test:
```bash
pytest tests/test_state_machine.py -v
```

End-to-end integration (server + client in same test):
```bash
pytest tests/test_integration_e2e.py -v -s
```

## Next Steps (M2)

1. Add `ImageBackend` implementation (pick: hosted API or local SD box)
2. Implement `Evolver` with rule-based operators
3. Wire Engine channel: SEND button → generate image → paint to Slate
4. Add render queue + loop state machine

All plumbing is ready. Interfaces are locked. No refactoring needed.

## Notes

- Simulation mode detects `platform.system() != "Linux"` — runs mocks on macOS, real drivers on Pi.
- Message schema is flat JSON; easy to debug with browser WebSocket client.
- ANSI terminal rendering clears screen on each render (harmless in sim, will optimize in M4).
- Pydantic models validate all messages; type safety at boundaries.
- Asyncio event loop supports concurrent server + client in single process (useful for testing).
