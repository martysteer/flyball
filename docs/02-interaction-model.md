# 02 — Interaction Model

This is the heart of Flyball. Read this one closely.

## The two-handed grammar

Think **modifier + scroll wheel**:

- **Left hand → Slate (Inky) buttons** pick **which channel** you're editing. The channel is a "mode." Each Inky button maps to one channel and its label is drawn sideways next to the physical button, always visible.
- **Right hand → Spark (Unicorn) buttons** act **within** the active channel: cycle options, commit, and access a secondary function. No labels needed — the LEDs *are* the feedback.

So: **Slate says WHAT, Spark says WHICH.** You rarely look away from the fast Spark while exploring; you glance at the slow Slate to change context or admire the result.

## Channels (Slate / Inky buttons A B C D)

A sensible default set of four channels. These are configurable — think of them as the "columns" from your Story Builder, promoted to first-class modes.

| Btn | Channel | Colour | What it holds |
|---|---|---|---|
| **A** | **Subject** | green | who/what — the noun. ("Private Eye", "Stargazer", "Drifter"…) |
| **B** | **Context** | blue | where/when — setting, era, weather. ("Foggy Alley", "1950s Suburb"…) |
| **C** | **Style** | magenta | how it looks — medium, palette, art movement. ("Film Noir Shadowplay", "Pop Art Block Tone"…) |
| **D** | **Engine** | amber | the *meta* channel — not a word slot. Controls the loop, evolution operator, cycle speed, send-to-render, and queue ops. |

The A/B/C word-block lists come straight from your ChatGPT-generated data (`shared/data/word_blocks.json`). The gestalt lists (visual layout, contrast, historical period, artistic genre) become **sub-options within the Style channel** or extra channels if you want more than four.

### Pressing a Slate button

- **Tap** an A/B/C button → make that channel active. The Spark retints to that channel's colour and starts showing that channel's current candidate.
- **Tap D** → enter the Engine channel; now the Spark cycles *engine settings* instead of words (see below).
- **Long-press** any A/B/C → jump that channel to a **sub-layer** (e.g. switch the whole theme, or switch the option *category* — Subject↔Persona↔Figure across themes). Optional, phase 2.

## Spark (Unicorn) buttons — act on the active channel

**Physical layout (confirmed from the hardware photo):** the four buttons sit at the *corners* of the 17×7 matrix, not in a row — **A top-left, B bottom-left** down the left edge, **X top-right, Y bottom-right** down the right edge. Design around this: the **left column = navigate** (A stacked over B reads naturally as prev-above-next / scroll-up-scroll-down), the **right column = act** (X commit, Y shift). Left thumb explores, right thumb commits.

```
  A ○ ·······17×7 matrix·······  ○ X      A = prev / up        X = commit
  B ○ ···························  ○ Y      B = next / down      Y = shift / alt
```

| Btn | Word channel (A/B/C active) | Engine channel (D active) |
|---|---|---|
| **A** (top-left) | **Prev** — cycle option backward | Prev setting / value down |
| **B** (bottom-left) | **Next** — cycle option forward | Next setting / value up |
| **X** (top-right) | **Commit** — push current candidate into the sentence stack for this channel | Apply / confirm the engine action |
| **Y** (bottom-right) | **Shift/Alt** — hold for secondary: coarse jump (±5), randomize this channel, or "mutate this token". Tap to toggle the second-line info. | Cycle *which* engine setting is focused (operator ↔ speed ↔ loop ↔ queue) |

Because the buttons flank the matrix left/right, you can also render **per-button hints at the matrix edges**: e.g. a small ▲/▼ glint in the left two columns next to A/B while navigating, and a dot in the right two columns next to X that brightens the moment a commit is available.

Debounce ~0.3–0.5s (you already do 0.5s in the Story Builder; the Unicorn can go tighter since it's not waiting on a slow display).

## What the Spark (17×7 LEDs) actually shows

17 wide × 7 tall is tiny, so be disciplined. Layout, top to bottom:

```
row 0      ▐ channel colour bar (full width, dim)  — reminds you which channel
row 1      · position pips: one dim dot per option, bright dot = current index
rows 2–6   the candidate word, scrolling right-to-left in the channel colour
```

- **Two "lines" of text** are only realistic with a 3px-tall glyph font (line rows 2–4, gap, line rows … doesn't quite fit 5 rows cleanly). More reliable: **one scrolling line** of the candidate word across rows 2–6, plus the colour bar + pips up top as the "second line" of *information*. Treat rows 0–1 as a status line, rows 2–6 as the text line.
- **Committed vs candidate:** while a candidate isn't yet committed, scroll it; the instant you Commit (X), flash the matrix that channel's colour once so the commit is felt, not just seen.
- **Engine channel** shows an icon-ish glyph + value instead of a word: e.g. a small looping arrow that spins faster/slower to show cycle speed; the operator shown as a 2–3 char scroll ("SWP", "LANG", "+CON", "-CON", "LTR").
- **Idle / loop running:** gentle colour breathing; a travelling pixel whose speed = cycle speed, so the room can see the machine "thinking."

## What the Slate (Inky) shows

The Inky only redraws on meaningful events (channel change, commit, new image, queue change) — never on Spark cycling.

```
┌───────────────────────────────────────────┐
│ [A]│                                        │
│ S  │                                        │
│ u  │        GENERATED IMAGE                 │
│ b  │        (7-colour, 640×400-ish          │
│ [B]│         area, dithered)                │
│ C  │                                        │
│ o  │                                        │
│ n  │                                        │
│ [C]│----------------------------------------│
│ S  │ sentence: "Private Eye · Foggy Alley · │
│ t  │  Film Noir Shadowplay"                 │
│ [D]│ queue: ▮▮▯   loop ▶ 8s   op: SWAP       │
│ Eng│                                        │
└───────────────────────────────────────────┘
```

- **Left menu strip** (~60–90px): the four channel labels rendered **sideways** (rotated 90°) next to their physical buttons, active channel highlighted (inverted block, like your Story Builder's active-category highlight).
- **Main area:** the current generated image.
- **Status ribbon** (bottom or overlaid): the assembled sentence, queue depth, loop state + speed, active operator.
- Because full refreshes are slow and flashy, batch changes: if the user is rapidly committing on the Spark, let the Slate coalesce and redraw once when they pause, rather than once per commit. (Conductor decides this — see architecture doc.)

## The fast/slow contract (say it out loud)

> The Spark may update as often as it likes. The Slate updates only on: (1) channel change, (2) commit that changes the sentence, (3) a finished generated image, (4) a queue/loop state change worth showing. Anything else stays on the Spark.

This is what makes a ~30s display feel good instead of maddening.

## Example flow

1. Tap **Slate A** (Subject). Spark tints green, scrolls "Private Eye", pips show 1/5.
2. **Spark B B B** → scrubs to "Detective". **Spark X** → commit. Matrix flashes green.
3. Tap **Slate B** (Context). Spark tints blue. Scrub → "Rain-Slicked Street". Commit.
4. Tap **Slate C** (Style). Scrub → "Film Noir Shadowplay". Commit. Slate redraws the sentence in its ribbon.
5. Tap **Slate D** (Engine). **Spark Y** to focus "SEND". **Spark X** → enqueue prompt. Slate starts generating; ~30s later the noir image paints.
6. Still in Engine: focus "LOOP", set operator to **LANG** and speed to **12s**, apply. Now every 12s the prompt drifts into another language and regenerates. Watch it evolve.
7. Tap **Slate D → PAUSE** (or any Slate word button auto-pauses the loop) to grab the wheel, tweak a channel, and resume.
