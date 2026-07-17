# Flyball Development Changelog & Debug Notes

Development log of fixes, improvements, and debug sessions.

---

## 2026-01-17 — M0-M1 Implementation & UX Fixes

### Bug Fixes

**Thread-safe button events** (commit a8a4d8b)
- **Problem:** Keyboard listener runs in thread, tried to call `asyncio.create_task()` without event loop → `RuntimeWarning: coroutine was never awaited`
- **Fix:** Store event loop reference, use `asyncio.run_coroutine_threadsafe()` to schedule coroutines from threads
- **Files:** `controller/controller.py`, `conductor/conductor.py`

**Single-character keyboard input** (this commit)
- **Problem:** Keyboard required pressing Enter after each key (buffered input)
- **Fix:** Use `tty.setraw()` + `termios` to read unbuffered single chars, restore terminal on exit
- **Files:** `controller/buttons.py`, `conductor/buttons.py`
- **Note:** Falls back gracefully if not a TTY (tests still work)

**Persistent Slate window** (this commit)
- **Problem:** PIL `.show()` opened new window on every button press (macOS Preview spam)
- **Fix:** Use Tkinter window (stdlib), create once, update image on subsequent renders
- **Files:** `conductor/display.py`
- **Note:** Tkinter included with Python on macOS + Pi, no extra deps

### Environment Setup

**Makefile + venv** (commit 5ed8b72)
- Split `requirements.txt` (runtime) and `requirements-dev.txt` (test deps)
- Makefile targets: `setup`, `setup-dev`, `conductor`, `controller`, `test`, `clean`, `install`
- Works on macOS + Pi Zero with basic venv
- `SETUP.md` guide added

### Implementation

**M0: Bus + Scaffold** (commits 2607161–3b48b17)
- WebSocket server/client with JSON messages
- Pydantic message schema (hello, state, button, ping/pong, toast, patch)
- Abstract interfaces: Bus, Display, Buttons, ImageBackend, Evolver

**M1: State Machine + Mocks** (commits b5651f3–e5fc94a)
- Channels (Subject/Context/Style/Engine) loaded from `word_blocks.json`
- Button handlers: prev/next/commit/shift
- SparkMock: 17×7 ANSI terminal with colour bar + pips + scrolling text
- InkyMock: PIL/Tkinter window with menu strip + sentence ribbon
- Full two-handed flow: pick channel on Slate → cycle+commit on Spark → state broadcasts
- 27 tests pass

---

**ANSI clear screen in raw mode** (this commit)
- **Problem:** `os.system("clear")` doesn't work in raw terminal mode → garbled display with progressive indentation
- **Fix:** Use ANSI escape codes directly (`\033[2J\033[H` for clear + home cursor) instead of system call
- **Files:** `controller/display.py`

**Ctrl+C exit not working** (commit c7dd7cb + this commit)
- **Problem:** Raw mode captures Ctrl+C as `\x03` char, doesn't raise KeyboardInterrupt. First fix only stopped button thread, main loop kept running.
- **Fix:** Added `on_exit` callback to button listeners that signals main Controller/Conductor to shut down
- **Files:** `controller/buttons.py`, `conductor/buttons.py`, `controller/controller.py`, `conductor/conductor.py`
- **Note:** Both `q` and Ctrl+C now exit cleanly and immediately

**Logging noise interfering with display** (this commit)
- **Problem:** INFO logs mixing with ANSI terminal output → garbled display
- **Fix:** Set log level to WARNING in simulation mode (logs to stderr, display to stdout)
- **Files:** `controller/__main__.py`, `conductor/__main__.py`

**Display buffering** (this commit)
- **Problem:** ANSI clear codes not flushing immediately
- **Fix:** Use `sys.stdout.write()` + explicit `flush()` for clear codes
- **Files:** `controller/display.py`

## Known Issues

### Terminal Display
- Terminal may need to be wide enough for 17-char matrix + borders
  - Minimum ~25 chars wide recommended

### Slate Window
- Tkinter window updates work, but window doesn't auto-focus
  - User may need to click window to see updates
  - **TODO:** Add `window.lift()` or `window.focus_force()` if needed

### Keyboard Input
- Raw mode captures all input, including Ctrl+C
  - Press `q` to quit cleanly
  - Ctrl+C still works but may leave terminal in raw mode
  - **TODO:** Add signal handler for SIGINT (M2)

---

## Testing Notes

### End-to-End Flow Verification
```bash
make test                    # 27 tests pass
make conductor              # Terminal 1
make controller             # Terminal 2
# Press a/b/x/y (Spark) and a/b/c/d (Slate) — no Enter needed
# Press q to quit
```

### Thread Safety Verified
- Button events from keyboard thread → asyncio loop works
- No "coroutine was never awaited" warnings
- State updates propagate correctly

---

## Performance Notes

- WebSocket latency on localhost: <1ms
- State broadcast + display update: ~10-20ms
- Terminal ANSI render: <5ms (screen clear dominates)
- PIL image creation: ~20ms
- Tkinter update: <10ms

---

## Next Steps (M2)

1. Add ImageBackend implementation (stub → real API)
2. Implement Evolver with rule-based operators
3. Wire Engine channel: SEND → generate → render
4. Add render queue + loop control
5. Polish: cursor positioning, signal handlers, window focus

---

## Debugging Tips

**"No running event loop" error:**
- Check if asyncio code called from thread
- Use `asyncio.run_coroutine_threadsafe(coro, loop)` from threads

**Terminal in weird state after quit:**
- Run `reset` or `stty sane` to restore
- Or just close terminal and reopen

**Slate window not appearing:**
- Check Tkinter installed: `python -c "import tkinter"`
- macOS: should work with system Python
- Pi: `sudo apt-get install python3-tk` if needed

**Tests hanging:**
- Button listeners set raw mode, tests might block
- Listeners check if stdin is a TTY before setting raw mode
- Run tests with `pytest -v` not in background
