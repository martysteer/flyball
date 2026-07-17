# Flyball — context for Claude Code

Flyball is a **two-Raspberry-Pi tangible interface for evolutionary AI image-making**. Read `README.md` and `docs/01`–`docs/05` before writing code. This file is the short version so you stay oriented.

## What it is
Two Pi Zero 2 W boards on the same LAN:
- **Spark** — Unicorn HAT Mini (17×7 RGB, 4 buttons at the corners A/B left, X/Y right). The **fast controller**: instant updates, cycles/scrolls options, holds *no authoritative state*.
- **Slate** — Inky Impression 4" (640×400, 7-colour e-paper, 4 buttons down the left edge, ~30–40s refresh). The **slow canvas** and the **state authority** (the Conductor): owns the channel, option indices, sentence stack, render queue, and evolution loop; calls the image-gen API; drives its own e-paper.

The interaction is **modifier + jog wheel**: Slate buttons pick *which channel* you edit; Spark buttons explore *which option*. See `docs/02` for the full button maps.

## Non-negotiable design rules
1. **One source of truth.** Slate/Conductor owns state; Spark/Controller reflects it and emits button events only. Don't split authority.
2. **Fast is for candidates, slow is for commits.** The Slate redraws **only** on: channel change, a commit that changes the sentence, a finished image, or a loop/queue state change. Never redraw the Inky on a Spark cycle.
3. **Sim-first.** Everything must run on macOS with no hardware, both roles talking over `localhost`. Carry over the existing Story Builder pattern (`platform.system()` detection, `InkyMock`). Ship the whole UX in simulation before touching GPIO.
4. **Keep the seams swappable:** `Bus` (transport — WebSocket now, MQTT later), `Display` (Inky/Unicorn + mocks), `Buttons` (gpiod/gpiozero + keyboard sim), `ImageBackend` (hosted API or local SD/ComfyUI), `Evolver` (rule-based or LLM-assisted).

## Where things go
- `conductor/` → Slate app (authority, image gen, e-paper).
- `controller/` → Spark app (LED UI, buttons).
- `shared/` → message schema, config, and `data/word_blocks.json` (seed option space — already populated).
- `deploy/` → systemd units + install scripts (M4/M5).

## Build order
Follow `docs/05-roadmap.md`: M0 bus → M1 state machine + channels → M2 image gen + queue → M3 evolution loop → M4 hardware → M5 boot/resilience. Each milestone is demoable in sim.

## Documentation
- `docs/` — all docs live here (design docs `01`–`05`, setup, changelog, summaries).
- `docs/plans/` — implementation plans. Date-prefixed: `YYYY-MM-DD-<name>.md`.
- `docs/specs/` — specs and brainstorm outputs. Date-prefixed: `YYYY-MM-DD-<name>.md`.
- No `superpowers/` subdir — plans and specs go directly in the dirs above.

## Conventions
- Python 3. Transport is WebSocket + JSON (see `docs/03` for the message schema). Conductor interprets button *semantics* (Spark just reports "B pressed").
- Config + secrets via env/`config.toml`, never hardcoded. Image-gen key comes from the environment.
- Before large changes, propose a short plan + file tree. Flag any "open questions" from `docs/05` that need a human decision.
