# Flyball

*A cybernetic governor for image-making. Two Raspberry Pis in a feedback loop — a fast little light-machine and a slow painted screen — grow AI images out of words you stack, drift them on their own, and hand you the helm whenever you want it.*

> Named for the **flyball governor**, the spinning-weights feedback device that regulates an engine and founds control theory. A governor has two weights; Flyball has two Pis. Those weights are **Spark** (the fast Unicorn HAT Mini) and **Slate** (the slow Inky Impression). See `docs/01-concept.md`.

---

## The one-paragraph pitch

Two Pi Zero 2 W boards sit on the same network. One wears a **Unicorn HAT Mini** (17x7 RGB LEDs, 4 buttons) — it's the **fast controller**, updating instantly, cycling and scrolling through options. The other wears an **Inky Impression 4"** (640x400, 7-colour e-paper, 4 buttons) — it's the **slow canvas**, taking ~30s to redraw but showing a full-colour generated image plus a sideways menu strip. You use the two together like a **modifier + a scroll wheel**: the Inky's buttons pick *which* part of a prompt you're editing; the Unicorn's buttons explore *which option* to put there. Committed words stack into a sentence, the sentence goes to an image generator, and the result paints onto the Inky. Then it can **loop** — mutating the prompt on its own (swap a word, change a language, add or drop a concept) at a speed you choose — and you can **pause** any time to grab the wheel and steer the next generation by hand.

## Hardware

| Role | Board | Display | Buttons | Speed |
|---|---|---|---|---|
| **Spark** (controller) | Pi Zero 2 W | Unicorn HAT Mini, 17x7 RGB | A/B/X/Y on BCM 5,6,16,24 | Instant |
| **Slate** (canvas) | Pi Zero 2 W | Inky Impression 4", 640x400, 7-colour | A/B/C/D on BCM 5,6,16,24 | ~30-40s refresh |

Both on the same router/LAN. Image generation happens off-device via an API.

## Quick start (macOS simulation)

```bash
make setup-dev    # venv + dependencies
make test         # 27 tests pass
```

Two terminals:

```bash
make conductor    # Terminal 1 — Slate window opens
make controller   # Terminal 2 — Spark window opens
```

Both pygame windows stay on top. Click a window and press keys:
- **Spark window:** `a`/`b` prev/next, `x` commit, `y` shift
- **Slate window:** `a`/`b`/`c`/`d` switch channel (Subject/Context/Style/Engine)
- Either window: `q` to quit

Keypress feedback prints to each terminal.

## Current status

**M0 + M1 complete.** WebSocket bus, state machine, pygame display mocks, full two-handed simulation. See `docs/m0-m1-summary.md` for details.

**Next:** M2 (image generation + render queue). See `docs/05-roadmap.md`.

## Repo layout

```
flyball/
├── README.md
├── CLAUDE.md                  ← context for Claude Code
├── Makefile                   ← setup, test, run targets
├── requirements.txt           ← runtime deps
├── requirements-dev.txt       ← dev/test deps (includes pygame)
├── docs/
│   ├── 01-concept.md          ← vision, naming, glossary
│   ├── 02-interaction-model.md← two-handed button maps, screen layouts
│   ├── 03-architecture.md     ← two-Pi roles, networking, message protocol
│   ├── 04-prompt-engine.md    ← queues, sentence stacking, evolution operators
│   ├── 05-roadmap.md          ← milestones M0–M5
│   ├── m0-m1-summary.md       ← what was built in M0–M1
│   ├── setup.md               ← dev + Pi deployment guide
│   └── changelog-debug.md     ← debug log and fixes
├── conductor/                 ← Slate app: state authority + display
│   ├── __main__.py
│   ├── conductor.py           ← server + state + button handlers
│   ├── state_machine.py       ← channels + option cycling
│   ├── display.py             ← InkyMock (pygame) + SlateDisplay
│   └── buttons.py             ← KeyboardListener (GPIO fallback)
├── controller/                ← Spark app: LED UI + button events
│   ├── __main__.py
│   ├── controller.py          ← client + render loop
│   ├── display.py             ← SparkMock (pygame) + SparkDisplay
│   ├── buttons.py             ← KeyboardListener (GPIO fallback)
│   └── unicorn_mock.py        ← pygame Unicorn HAT Mini emulator
├── shared/                    ← message schema, config, interfaces
│   ├── config.py
│   ├── messages.py            ← Pydantic message schema
│   ├── bus_websocket.py       ← WebSocket server/client
│   ├── data/word_blocks.json  ← seed option space
│   └── interfaces/            ← swappable abstractions
│       ├── bus.py, display.py, buttons.py
│       ├── image_backend.py   ← stub (M2)
│       └── evolver.py         ← stub (M3)
├── tests/                     ← 27 tests
└── deploy/                    ← systemd units (M4/M5)
```

## Read next

Start with `docs/02-interaction-model.md` — the two-handed control scheme is the heart of the design. Then `docs/03-architecture.md` for how the two Pis talk, and `docs/04-prompt-engine.md` for the evolving-image loop.
