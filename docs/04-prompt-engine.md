# 04 — The Prompt Engine (queues, evolution, image gen)

This is the payload: turning stacked words into an evolving stream of images.

## Two queues, kept distinct

1. **The sentence stack** — the ordered committed options that assemble into *one* prompt. One slot per word-channel (Subject, Context, Style), plus any free-text or extra modifiers. Operations: `commit(channel, option)`, `remove_last`, `clear`, optionally `reorder`.
2. **The render queue** — finished prompts waiting to be generated and painted. Because generation+display is slow (~30s+), you can assemble and enqueue several prompts fast on the Spark, then let the Slate grind through them one at a time. This is the "select rapidly, then queue them" behaviour you described.

Assembly: the stack renders to a prompt string via a template, e.g.
`"{subject}, {context}, {style}, {global_modifiers}"` →
`"Detective, rain-slicked street, film noir shadowplay, bold flat colours high contrast"`.
Keep the template configurable; the *global modifiers* are where you bias toward the Inky's palette (see below).

## The evolution loop

When **Loop = ON**, the Conductor repeats:

```
current_prompt → [evolution operator] → next_prompt → generate → paint → wait(cycle_speed) → repeat
```

- **Cycle speed** — selectable on the Engine channel (e.g. 4s / 8s / 12s / 30s / manual). Note the floor is really "generation time + refresh time," so "4s" means "as fast as the pipeline allows"; the number is the *minimum* dwell.
- **Pause** — grabs the wheel. Any Slate word-button press auto-pauses (you're clearly editing). While paused you can edit the stack, change the operator, or hand-pick the next prompt, then resume. Resume continues evolving from the *current* prompt, not the pre-pause one.

## Evolution operators

Selectable in the Engine channel. Two implementation tiers — ship rule-based first, add LLM-assisted for richer drift.

| Operator | Code | What it does | Rule-based | LLM-assisted |
|---|---|---|---|---|
| Swap word | `SWAP` | Replace one token with a sibling from its channel's option list, or a synonym | pick random from list / thesaurus | "replace one noun, keep it coherent" |
| Change letter | `LTR` | Mutate a character — glitchy typo-drift | random char edit | — (rule-based is the point) |
| Change language | `LANG` | Translate a word or the whole phrase into another language | offline dictionary / lookup table | translation model / API |
| Add concept | `+CON` | Append a modifier/token | pull from gestalt lists | "add one evocative concept" |
| Delete concept | `-CON` | Drop a token | remove random modifier | "remove the least essential concept" |
| Shift style | `STY` | Change only the Style channel | next in Style list | "reinterpret in a new art movement" |
| Intensify/soften | `AMP` | Tune adjectives / weights | swap adjective tier | "make it more/less extreme" |
| Crossover | `X` | Blend with a past prompt from lineage | splice tokens | "merge these two prompts" |

Design the `Evolver` as a strategy interface: `evolve(prompt, lineage) -> new_prompt`. Rule-based needs no network and is cheap/deterministic-ish (good for offline demos). LLM-assisted goes out to an API and gives more surprising, coherent drift. Let the operator be chosen per-loop, and consider a "surprise me" mode that random-walks across operators.

## Lineage (nice-to-have, phase 2)

Keep a tree of `{prompt, image_ref, parent, operator}`. This gives you:
- **Rewind** — step back up the tree if a mutation went somewhere bad.
- **Branch** — pause, fork, explore a different operator, compare.
- **Gallery** — the Slate can cycle through past frames (it's e-paper — a saved image loads as fast as a fresh one).

Store as JSON + image files on the Slate. This is basically evolutionary/generative art with a family tree, and it's where the piece gets genuinely mesmerising.

## Image generation

The Zero 2 W can't generate locally at any usable speed, so generation is an **API call** behind an `ImageBackend` interface: `generate(prompt) -> PIL.Image`.

- **Backends (pluggable):** any hosted image API (OpenAI-style images endpoint, Stability, Replicate, etc.), OR a box on your own LAN running Stable Diffusion / ComfyUI if you have a capable machine — that keeps it fully local and free-to-run. The interface is the same; the config picks the backend + key.
- **Palette-aware prompting.** The Inky Impression is **7-colour** (roughly black, white, red, green, blue, yellow, orange). Images with subtle gradients look muddy after dithering. So bias the prompt toward **bold flat colour, high contrast, poster/screenprint/risograph/woodcut aesthetics** — these both suit the panel *and* give the piece a strong consistent look. Put this in the global-modifiers slot of the template.
- **Post-process for the panel:** downscale to the panel's native resolution (~640×400), then let the Inky library's saturation/dither do the 7-colour quantisation (your Story Builder already calls `set_image(img, saturation=...)`). Optionally pre-quantise to the exact 7-colour palette yourself for more control.
- **Cost/rate awareness:** loop mode can burn API calls. Add a per-session cap and show remaining budget somewhere (Engine channel value). Cache by prompt hash so identical prompts don't regenerate.
- **Live reference:** the stamp-collage image currently on your panel is a good north star — flat printy shapes, warm reds/browns/black/cream, high contrast, no reliance on smooth gradients. Note it reads *warm*; test pure blues/greens/yellows early to see how vivid they actually come out on your specific unit, and lean the global modifiers toward whatever renders punchiest. A **"vintage stamp / philatelic collage"** style is also an obvious ready-made theme to ship with, since it's clearly a look you already like and it suits the panel perfectly.

## Data seed

Your ChatGPT thread already produced the perfect seed data: five themed word-triplet sets (cinematic noir, romantic/dreamlike, moody/introspective, retro/nostalgic, gritty/real) plus gestalt lists (visual layout, contrast/light, portrait/landscape types, historical periods, artistic genres). Land all of that in `shared/data/word_blocks.json`:

- Themed triplets → the **Subject / Context / Style** channel option lists (per theme).
- Gestalt lists → **Style sub-options** and **global modifier** candidates, and great fodder for the `+CON` operator.

This means Flyball boots with a rich option space on day one, reusing work you've already done.
