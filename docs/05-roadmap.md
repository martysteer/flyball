# 05 — Roadmap (build order for Claude Code)

Build entirely in **simulation on your Mac**, then flip to hardware. Each milestone is demoable on its own.

## M0 — Skeleton + bus (Mac only)
- Repo scaffold per README layout.
- `Bus` abstraction over WebSocket. Conductor runs a WS server; Controller connects to `localhost:8765`.
- `hello` / `state` / `button` / `ping`-`pong` messages round-trip. Log both ends.
- **Demo:** press a key in the Controller terminal, see the Conductor receive the button event.

## M1 — State machine + channels (Mac, no image gen)
- Port the Story Builder's `button_next/prev/select/back` logic into the Conductor as networked handlers.
- Channels (Subject/Context/Style/Engine), option lists loaded from `shared/data/word_blocks.json`.
- Conductor emits `state`; Controller renders it (terminal ANSI 17×7 mock: colour bar + pips + scrolling candidate).
- Slate mock (`InkyMock` → PIL `.show()`) draws the sideways menu strip + sentence ribbon.
- **Demo:** full two-handed flow — pick channel on "Slate," cycle+commit on "Spark," watch the sentence build. No pictures yet.

## M2 — Image generation + render queue (Mac)
- `ImageBackend` interface + one real backend (hosted API or local SD/ComfyUI on your LAN).
- Palette-aware prompt template + global modifiers; downscale + saturation for the Inky mock.
- Sentence stack → assemble prompt → enqueue → generate → paint to Slate mock.
- **Demo:** stack a sentence, hit send, ~30s later a poster-style image appears in the Slate window.

## M3 — Evolution loop (Mac)
- `Evolver` strategy interface + rule-based operators (SWAP, LTR, LANG-lookup, +CON, -CON, STY).
- Engine channel controls: loop play/pause, cycle speed, operator select, send, queue ops.
- Auto-pause when a Slate word-button is pressed.
- **Demo:** turn on Loop with operator = LANG at 8s; watch the image drift language by language. Pause, tweak, resume.

## M4 — Hardware bring-up
- Two Pi Zero 2 W, Raspberry Pi OS, SPI enabled, hostnames `slate` / `spark`.
- Real `SparkDisplay` (unicornhatmini lib) + buttons (gpiozero, BCM 5/6/16/24).
- Real `SlateDisplay` (inky lib) + buttons (gpiod, BCM 5/6/16/24) — reuse your Story Builder's button setup.
- mDNS discovery: Controller finds `slate.local`. Env-var fallback.
- **Demo:** the whole M3 experience, now physical, two devices on the LAN.

## M5 — Boot + resilience
- systemd units (`slate-conductor.service`, `spark-controller.service`), `Restart=always`, boot-into-app.
- Heartbeat + auto-reconnect + disconnected LED pattern.
- Persist sentence stack + queue to disk for reboot recovery.
- **Demo:** power both Pis; they boot straight into a working, self-discovering, evolving art machine.

## M6 — Delight (phase 2, pick and choose)
- LLM-assisted evolution operators (richer, more coherent drift).
- Lineage tree: rewind / branch / gallery-cycle past frames on the Slate.
- Long-press sub-layers (theme switch, category switch).
- "Surprise me" operator random-walk; per-session API budget + prompt-hash cache.
- Second-line micro-typography experiments on the 17×7 (two-line 3px font).

## Open questions to resolve in Claude Code
- **Final name** (see `01-concept.md` shortlist) — locks folder/module names.
- **Channel set** — is 3 word-channels + 1 engine right, or do you want Style split into Medium/Palette/Era (needs long-press sub-layers or a 5th "virtual" channel)?
- **Image backend** — hosted API (simplest, costs per image) vs. a local SD/ComfyUI box on your LAN (free to run, needs a capable machine)?
- **Transport** — confirm WebSocket for v1; note the MQTT upgrade trigger (adding a 3rd device / wanting retained state).
- **Two-line vs one-line Spark text** — decide after seeing the 17×7 mock in M1.
