# Spark-Centric UI — Design Spec

**Date:** 2026-07-18
**Status:** Approved
**Supersedes:** parts of `docs/02-interaction-model.md` (Slate buttons, per-press messaging)

## Summary

All interaction moves to Spark's 4 buttons (short/long press). Spark owns
exploration state locally — instant LED feedback, zero network traffic while
exploring. Slate e-ink redraws **only** on explicit send (Engine channel +
long-press Y). Slate buttons unwired for now.

Motivation: e-ink refresh (~30s) made per-press Conductor round-trips and
frequent redraws feel broken. Exploration is fast and local; commitment is
explicit and slow.

## 1. Architecture — Local-State Inversion

- **Spark (Controller)** owns exploration state: active channel, option
  indices, per-channel committed words. Loads `shared/data/word_blocks.json`
  directly. Every press = local update + LED feedback.
- **Slate (Conductor)** stays authority for: sentence-of-record, render
  queue, image generation, e-ink. Receives only `send` messages, replies
  `ack`/state.
- **Bus unchanged**: WebSocket transport, reconnect + re-hello logic stays.
- **Removed**: per-press `button` messages Controller→Conductor.
- **New message**: `send {channels: {subject, context, style}, engine: {...}}`.
- **Slate buttons**: unwired (listener code stays, slate keymap ignored).

## 2. Button Grammar (Revised for Spatial Mapping)

| Btn | Short | Long (≥600ms) |
|---|---|---|
| A (top-left) | prev option | jump −5 |
| X (top-right) | next option | jump +5 |
| B (bottom-left) | commit channel | uncommit (clear channel) |
| Y (bottom-right) | next channel (Subj→Ctx→Style→Engine→wrap) | Engine: **send** / else: randomize channel |

- Long-press **fires at 600ms while held** (not on release) — snappier feel.
  `# ponytail: threshold constant, tune on hardware`
- **Top buttons (A/X) navigate pips** — spatial mapping to row-1 pip display.
- **Bottom buttons (B/Y) commit + channel** — actions vs exploration.

## 3. Spark Display (17×7)

| Rows | Content |
|---|---|
| 0 | Channel color bar. Solid = channel committed, dim = uncommitted. |
| 1 | Option pips: **brightest** = current index, **bright** = committed (if different from current), **dim** = others. Committed pip stays visible when navigating away. Engine: setting pips. |
| 2–6 | Candidate word, variable-width 5-high font, bounce scroll, channel color. |

- **Bounce scroll**: medium speed (~3 cols/s), scrolls left until end
  visible, reverses. Word fits ≤17 cols → static.
- **Commit flash**: full matrix in channel color, 2 frames.
- **Press feedback**: 1-frame edge glint beside pressed button (left cols
  for A/B, right cols for X/Y). Long-press shows growing glint until
  threshold fires — teaches the gesture.
- **Engine channel**: amber tint; focused setting as text (`SEND`, `OP`,
  later `SPEED`); A/B cycle values.
- **Brightness**: config value, default dim (~0.2). Calibrate on hardware.

## 4. Font

- Dict `char → list of columns`; column = 5 bits, bit 0 = top row.
- Render = concat char columns + 1 blank column between chars; window 17
  cols at bounce offset.
- Full set: A–Z, 0–9, space, hyphen, apostrophe, brackets.
- Variable width (e.g. `I` = 1 col, `W` = 5 cols).
- Replaces both duplicated 3×5 font dicts (SparkMock + hardware branch) —
  single shared table.

## 5. Rendering Architecture

- **Animation ticker** task on Controller, ~15fps: owns bounce-scroll
  offset, flash frames, glint frames.
- **Render = pure function** `(state, tick) → pixels`. Ticker calls it,
  pushes frames to display.
- Existing async render queue stays for Slate; Spark ticker replaces the
  state-driven render queue on Controller side (ticker reads current local
  state each frame).

## 6. Incremental Milestones — each demoable in sim

| Stage | Deliverable | Demo |
|---|---|---|
| **S1** | Variable-width font, bounce-scroll math, brightness config. Message flow untouched. | Long words readable. |
| **S2** | ~15fps ticker task; render as pure `(state, tick)` function. | Smooth bounce. |
| **S3** | Local state: Controller loads word_blocks, owns channel/index/committed. Y cycles channel, X commits, A/B cycle. Button messages to Conductor removed. | Full exploration, Slate silent. |
| **S4** | Long-press detection in buttons layer; Engine channel with SEND; long-Y → `send` → Conductor renders e-ink once. | End-to-end send. |
| **S5** | Polish: edge glints, commit flash, uncommit, jump ±5, randomize, engine glyphs. | Full grammar. |

Each stage: green tests + sim demo before the next.

## 7. Testing

- **Font**: pure-function tests — known char → columns, width calc, bounce
  window at edges.
- **Local state**: transition tests — cycle wrap, commit, channel wrap.
- **Long-press**: timing test with fake clock.
- **Send**: bus integration test (existing pattern) + one send round-trip.
- **Sim**: pygame KEYDOWN/KEYUP gives hold duration for long-press sim.

## 8. Edge Cases

- **Send while disconnected**: drop message, red flash feedback. Reconnect
  re-hellos automatically.
- **Send during e-ink refresh**: Slate render queue already keeps latest
  only.
- **Empty sentence send**: allowed; Conductor renders placeholder. No
  blocking validation.

## Decisions Log

- Bounce scroll (not wrap-around) — user preference, no seam, short words static.
- Variable-width font via column concat — user-specified implementation shape.
- Explicit-send-only Slate redraws — fixes constant e-ink refresh irritation.
- All-on-Spark interaction — Slate becomes pure display; enables fast solo prototyping.
- Local-state inversion scoped to exploration only — Conductor keeps
  authority for sentence-of-record, queue, image gen (CLAUDE.md rule 1
  honored at the commitment boundary, not the exploration loop).
- **Button grammar revised for spatial mapping** — A/X top buttons navigate pips (matches row-1 layout), B/Y bottom buttons commit/channel (2026-07-18).
- **Three-state pip brightness** — brightest = current cursor, bright = committed (when cursor elsewhere), dim = others. Visual feedback shows locked-in choice while exploring (2026-07-18).
