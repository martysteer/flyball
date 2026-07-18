# Next Session: Hardware Testing & Finalization

## What's Complete

All S1-S5 implementation complete (16 tasks, 93 tests green):

- **S1**: Variable-width font, bounce-scroll with dwell, brightness config
- **S2**: Pure render_frame, 30fps ticker
- **S3**: LocalState exploration on Spark, three-state pip brightness, button messages removed
- **S4**: Release events, LongPressDetector (600ms), SendMessage + explicit send
- **S5**: Commit flash, uncommit, jump ±5, randomize, edge glints, engine OP cycling, send-fail flash

Full button grammar working in simulation:
- **A/X** (top): prev/next option, long = jump ±5
- **B** (bottom-left): commit (2-frame flash), long = uncommit
- **Y** (bottom-right): next channel, long = send (engine) or randomize (word)
- **X on engine**: cycle settings (SEND ↔ OP)

Spark owns all exploration state locally — zero network traffic while exploring. Slate redraws only on explicit send (long Y on engine).

## What's Next

### Immediate: Hardware Deployment & Tuning

1. **Deploy to Pi hardware** (M4 target from roadmap):
   - Run `deploy/install-pi.sh` on both Pis
   - Verify systemd units start correctly
   - Test reconnect + re-hello on network hiccup

2. **Hardware calibration** (spec §3, §2):
   - Brightness: default 0.1, adjust via `FLYBALL_SPARK_BRIGHTNESS` env var
   - Long-press threshold: default 600ms, tune in `controller/longpress.py:THRESHOLD_S`
   - Verify growing glint teaches the gesture feel on real buttons

3. **GPIO edge cases**:
   - When_released fires correctly on gpiozero buttons
   - Bounce time (currently 0.1s) feels right for real buttons
   - Simultaneous presses handled gracefully

4. **E-ink timing verification** (spec edge case):
   - Slate render takes ~30-40s — verify render queue drops old frames correctly
   - Rapid button-mashing during refresh doesn't block
   - Send during refresh queues correctly (latest-only)

### Follow-on Work (M5+ from roadmap)

5. **Boot resilience** (M5):
   - systemd units restart on crash
   - Auto-reconnect on both sides survives reboots
   - State survives Conductor restart (or document: ephemeral by design)

6. **Image generation integration** (already stubbed):
   - Wire real API key from config
   - Test send → sentence → image → queue → e-ink end-to-end
   - Evolution loop (sentence stack, operator mutations)

7. **Polish**:
   - Slate buttons still unwired (spec: "listener stays, keymap ignored") — decide: enable or remove listener entirely?
   - Engine OP values currently cycle through all 5 — pare down to useful subset?
   - Boot state: always start on subject:0 or remember last position?

## Commands to Run

```bash
# Quick smoke test (macOS sim):
cd /Users/marty/Devel/flyball
python -m pytest tests/ -v  # Should see 93 passed

# Run both apps in sim (two terminals):
python -m conductor.main  # Terminal 1
python -m controller.main  # Terminal 2

# Deploy to hardware (from macOS, when ready):
rsync -av --exclude='.git' --exclude='*.pyc' . pi@slate.local:~/flyball/
rsync -av --exclude='.git' --exclude='*.pyc' . pi@spark.local:~/flyball/
ssh pi@slate.local 'cd flyball && ./deploy/install-pi.sh slate'
ssh pi@spark.local 'cd flyball && ./deploy/install-pi.sh spark'

# Check systemd status on Pi:
systemctl status flyball-conductor  # On Slate
systemctl status flyball-controller  # On Spark
journalctl -u flyball-controller -f  # Live logs
```

## Key Files to Know

- **Spec**: `docs/specs/2026-07-18-spark-centric-ui-design.md` (authoritative grammar)
- **Plan**: `docs/plans/2026-07-18-spark-centric-ui-plan.md` (implementation roadmap)
- **Roadmap**: `docs/05-roadmap.md` (M0-M5 milestones)
- **Config knobs**: `shared/config.py` (brightness, paths)
- **LocalState**: `controller/state.py` (exploration logic)
- **Render**: `controller/render.py` (pure frame rendering + effects)
- **Long-press**: `controller/longpress.py` (600ms threshold constant)

## Known Decisions

- Bounce-scroll (not wrap-around) — user preference
- 30fps ticker with 2px text padding, 30-tick dwell
- Spatial button mapping: top buttons = pips, bottom = commit/channel
- Three-state pip brightness teaches committed vs exploring
- Send-only Slate redraws (fixes 30s e-ink blocking)
- Empty sentence allowed (Conductor renders placeholder)

## Files Changed This Session

All committed to main branch (23 commits since start):
- Font system, ticker, LocalState, LongPressDetector
- Effects overlay, render_frame signature, button rewiring
- SendMessage, Conductor _on_send handler
- All S5 polish (flashes, glints, jump, randomize, engine OP)

No merge conflicts expected — linear history on main.

---

**TL;DR**: Implementation done, 93 tests green. Next: deploy to Pi hardware, tune brightness + long-press feel, verify e-ink render queue under rapid button-mashing. Then: image gen + evolution loop (M2-M3 from roadmap).
