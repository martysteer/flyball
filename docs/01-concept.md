# 01 — Concept, Naming & Glossary

## The core idea

Flyball is a **two-surface tangible interface for evolutionary AI image-making**. It separates two things that are usually crammed onto one screen:

- **Exploration** — trying options quickly, scrubbing back and forth, "what if." This wants a surface that updates *now* and never makes you wait. → the LED matrix (**Spark**).
- **Commitment & output** — the assembled prompt and the finished picture. This can afford to be slow and beautiful. → the e-paper canvas (**Slate**).

The magic is that the two are *coupled*: neither is a complete interface alone. The Slate tells you (and constrains) *what dimension* you're working in; the Spark lets you fly through the *values* in that dimension. It's a hardware version of a **modal editor**, or a **modifier key + jog wheel**.

## Naming

The project is **Flyball**, after the **flyball (centrifugal) governor** — the spinning-weights device that regulates an engine's speed by feedback, and the founding image of control theory. It fits on every level:

- Flyball is a **cybernetic governor for image-making**: a machine that regulates its own creative drift (cycle speed, evolution operator, the loop) while letting you grab the helm. "Governor," "cybernetics," and the Greek *kybernetes* (steersman) all trace to the same root — the name is the thing describing itself.
- The metaphor is **literal**: a governor has *two spinning weights*; Flyball has *two Raspberry Pis* in a feedback loop. The two weights are the device codenames — **Spark** (the fast-whirling regulator) and **Slate** (the throttle it settles).

**Device codenames — keep these in code** (`spark/`, `slate/`): short, unambiguous, and they name the fast/slow split directly. `InkyPie` can remain the umbrella name for your monorepo if you like the continuity with earlier work.

*Alternatives considered (for the record): DriftLoom, Kybernete, Chroma Governor, Flypi, Pixtruder.*

## Glossary (use these consistently in code)

- **Spark** — the Unicorn HAT Mini Pi. Fast controller. Runs the **Controller** app.
- **Slate** — the Inky Impression Pi. Slow canvas. Runs the **Conductor** app (state authority).
- **Conductor** — the process on Slate that owns the single source of truth: the current channel, the option indices, the sentence stack, the render queue, and the evolution loop. It orchestrates image generation and its own e-paper.
- **Controller** — the process on Spark that renders LED UI and emits button events. It holds *no authoritative state* — it's a fast, dumb-ish terminal onto the Conductor's state.
- **Channel** — one editable dimension of the prompt (e.g. Subject, Context, Style, Engine). Selected on the **Slate** buttons.
- **Option** — a candidate value within a channel (e.g. within Subject: "Private Eye", "Stargazer"…). Cycled on the **Spark** buttons.
- **Sentence / stack** — the ordered set of committed options that assemble into the image-gen prompt.
- **Render queue** — prompts waiting to be generated + painted. Lets you fire several fast and let Slate work through them.
- **Evolution operator** — a mutation applied to the prompt between loop iterations (swap word, change letter, translate, add/drop concept, …).
- **Loop** — the auto-evolve-and-regenerate cycle. Has a *speed* and an active *operator*. Pausable.
- **Lineage** — the tree of prompts→images produced by the loop, so you can branch/rewind.

## Design principles

1. **Fast is for candidates, slow is for commits.** The Spark shows what you *might* pick and never blocks; the Slate only redraws on a commit, a channel change, or a finished image. Never redraw the Inky on every Unicorn cycle.
2. **One source of truth.** The Conductor (Slate) owns state. The Controller (Spark) reflects it. This avoids two-device sync hell.
3. **Colour is language.** On the 17×7 Spark you can't show much text, so the *whole matrix tints* to the active channel's colour. The user always knows what they're editing without reading a word.
4. **Everything degrades to simulation.** Both roles must run on a Mac with no hardware, talking over localhost, so the whole thing is buildable and testable before flashing Pis. (Carried over from your Story Builder's sim mode.)
