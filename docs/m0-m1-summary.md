# Flyball M0-M1 Implementation Summary

## What Was Built

**M0 + M1 complete.** Full two-handed WebSocket bus + state machine + pygame display mocks running in macOS simulation.

- **WebSocket Bus** — Conductor (Slate authority) server on `localhost:8765`, Controller (Spark client) connects and round-trips `hello` / `state` / `button` / `ping`-`pong` messages.
- **State Machine** — Channels (Subject/Context/Style/Engine), option lists loaded from `shared/data/word_blocks.json`, buttons trigger prev/next/commit/shift logic.
- **Spark Mock** — Pygame Unicorn HAT Mini emulator: 17x7 LED matrix with colour bar, position pips, 3x5 pixel font text. Always-on-top window.
- **Slate Mock** — Pygame Inky Impression emulator: 640x400 window with left menu strip (channel buttons A/B/C/D), main image placeholder, sentence/engine status ribbon. Always-on-top window.
- **Keyboard Sim** — Both pygame windows respond to keyboard when focused. Spark: `a/b/x/y`. Slate: `a/b/c/d`. Press `q` or close window to quit.
- **Full Flow** — Pick channel on Slate → cycle/commit options on Spark → state broadcasts → both displays update.
- **Tests** — 27 tests pass: message schema, state machine, WebSocket round-trip, display rendering, end-to-end integration.

## Architecture

```
Conductor (Slate authority)
  │
  ├─ WebSocketServer (localhost:8765)
  ├─ ChannelRegistry (state machine)
  │  ├─ Channel: subject, context, style, engine
  │  └─ Options loaded from word_blocks.json
  ├─ InkyMock (pygame 640x400 window)
  └─ on_key callback (pygame KEYDOWN events)

Controller (Spark client)
  │
  ├─ WebSocketClient (connects to server)
  ├─ SparkMock (pygame 17x7 LED emulator)
  └─ on_key callback (pygame KEYDOWN events)

Bus: WebSocket + JSON (swappable for MQTT later)
Interfaces: Bus, Display, Buttons, ImageBackend, Evolver
```

## Two-Handed Flow

1. **Slate window:** Press `b` → switches to Context channel (blue highlight)
2. **Spark window:** Display updates — blue colour bar, Context options shown
3. **Spark window:** Press `b b` → cycles to "Neon Bar"
4. **Spark window:** Press `x` → commits "Neon Bar" to Context
5. **Slate window:** Sentence ribbon updates with committed words
6. Repeat for Style, Engine channels

## Swappable Interfaces

All behind abstract base classes — swap without changing app code:

| Interface | Current (M0-M1) | Future |
|---|---|---|
| `Bus` | WebSocket | MQTT |
| `Display` | InkyMock / SparkMock (pygame) | Real Inky / Unicorn (M4) |
| `Buttons` | pygame KEYDOWN + KeyboardListener | GPIOListener (M4) |
| `ImageBackend` | Stub | Hosted API / Local SD (M2) |
| `Evolver` | Stub | Rule-based / LLM-assisted (M3) |

## What's Stubbed for M2+

- **ImageBackend** — Real image generation (hosted API or local SD/ComfyUI)
- **Evolver** — Prompt mutation operators (SWAP, LANG, LTR, +CON, -CON)
- **Engine Channel** — SEND button, loop control, queue management (plumbing in place)
- **Real Hardware** — GPIO listeners and Unicorn HAT / Inky Impression drivers (M4)
