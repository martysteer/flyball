# Flyball

*A cybernetic governor for image-making. Two Raspberry Pis in a feedback loop — a fast little light-machine and a slow painted screen — grow AI images out of words you stack, drift them on their own, and hand you the helm whenever you want it.*

> Named for the **flyball governor**, the spinning-weights feedback device that regulates an engine and founds control theory. A governor has two weights; Flyball has two Pis. Those weights are **Spark** (the fast Unicorn HAT Mini) and **Slate** (the slow Inky Impression). See `docs/01-concept.md`.

---

## The one-paragraph pitch

Two Pi Zero 2 W boards sit on the same network. One wears a **Unicorn HAT Mini** (17×7 RGB LEDs, 4 buttons) — it's the **fast controller**, updating instantly, cycling and scrolling through options. The other wears an **Inky Impression 4"** (640×400, 7-colour e-paper, 4 buttons) — it's the **slow canvas**, taking ~30s to redraw but showing a full-colour generated image plus a sideways menu strip. You use the two together like a **modifier + a scroll wheel**: the Inky's buttons pick *which* part of a prompt you're editing; the Unicorn's buttons explore *which option* to put there. Committed words stack into a sentence, the sentence goes to an image generator, and the result paints onto the Inky. Then it can **loop** — mutating the prompt on its own (swap a word, change a language, add or drop a concept) at a speed you choose — and you can **pause** any time to grab the wheel and steer the next generation by hand.

## Why this is a natural next step from Inky Story Builder

Your existing `inky_story_builder.py` already nails the core UX grammar: an A/B/C/D button hierarchy (Select / Next / Prev / Back), a mode ladder (theme → categories → view), a word-triplet stack, and a clean macOS **simulation mode** so you can build without hardware. Flyball keeps all of that and does three new things:

1. **Splits the interface across two devices** so exploration (fast) and commitment (slow) live on the surface each is good at.
2. **Replaces canned vignettes with a live image generator**, so the stacked sentence becomes a picture.
3. **Adds a feedback loop** — the prompt evolves itself between generations, with operators you can select and pause.

## Hardware

| Role | Board | Display | Buttons | Speed |
|---|---|---|---|---|
| **Spark** (controller) | Pi Zero 2 W | Unicorn HAT Mini, 17×7 RGB | A/B/X/Y on BCM 5,6,16,24 | Instant |
| **Slate** (canvas) | Pi Zero 2 W | Inky Impression 4", 640×400, 7-colour | A/B/C/D on BCM 5,6,16,24 | ~30–40s refresh |

Both on the same router/LAN. Image generation happens off-device via an API (the Zero 2 can't generate locally at any usable speed).

## Repo layout (proposed)

```
flyball/
├── README.md                  ← you are here
├── CLAUDE.md                  ← orientation Claude Code auto-reads on start
├── GET-STARTED.md             ← CLI commands + copy-paste kickoff prompt
├── .gitignore
├── docs/
│   ├── 01-concept.md          ← vision, naming, glossary
│   ├── 02-interaction-model.md← the two-handed hierarchy, button maps, screen layouts
│   ├── 03-architecture.md     ← two-Pi roles, networking, message protocol, boot, sim
│   ├── 04-prompt-engine.md    ← queues, sentence stacking, evolution operators, image gen
│   └── 05-roadmap.md          ← build order / milestones for Claude Code
├── conductor/                 ← runs on Slate (Inky): state authority + image gen + e-paper
├── controller/                ← runs on Spark (Unicorn): LED UI + button events
├── shared/                    ← message schema, word/option data, config
│   └── data/word_blocks.json  ← seed from your ChatGPT-generated theme lists
└── deploy/                    ← systemd units, install scripts
```

## Read next

Start with `docs/02-interaction-model.md` — the two-handed control scheme is the heart of the whole thing. Then `docs/03-architecture.md` for how the two Pis talk, and `docs/04-prompt-engine.md` for the evolving-image loop.
