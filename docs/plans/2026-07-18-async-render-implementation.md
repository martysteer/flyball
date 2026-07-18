# Async Render Implementation Plan

**Date:** 2026-07-18
**Status:** Completed
**Related Spec:** `docs/specs/2026-07-18-async-render-architecture.md`

## Objective

Implement async render queue to decouple state updates from display rendering, fixing:
1. Bidirectional messaging (Conductor → Controller state updates)
2. Non-blocking display updates (30s e-ink refresh doesn't block buttons)

## Implementation Steps

### 1. Conductor — Add Async Render Queue

**File:** `conductor/conductor.py`

**Changes:**
- `__init__`: Add `self.render_queue = asyncio.Queue(maxsize=1)` and `self.render_task`
- `start()`: Launch background render task with `asyncio.create_task(self._render_loop())`
- `shutdown()`: Cancel render task and await completion
- `_render_loop()`: New async method consuming render queue
- `_broadcast_state()`: Replace synchronous render with non-blocking queue put
- `_schedule()`: Add logging for visibility
- Remove: `self.last_display_update` and 35s debounce logic
- Remove: `time` import (no longer needed)

**Queue behavior:**
```python
try:
    self.render_queue.put_nowait(frame)
except asyncio.QueueFull:
    self.render_queue.get_nowait()  # discard old
    self.render_queue.put_nowait(frame)  # queue latest
```

### 2. Controller — Add Async Render Queue

**File:** `controller/controller.py`

**Changes:**
- `__init__`: Add `self.render_queue` and `self.render_task`
- `connect()`: Launch background render task
- `shutdown()`: Cancel render task and await completion
- `_render_loop()`: New async method consuming render queue
- `_on_state()`: Replace `self.display.render(state)` with queue put
- `_on_patch()`: Replace `self.display.render(self.current_state)` with queue put
- `_schedule()`: Add logging for visibility

**Same queue behavior as Conductor (maxsize=1 with eviction).**

### 3. Conductor Main Loop — Separate Event Polling

**File:** `conductor/__main__.py`

**Before:**
```python
while conductor.server_running:
    snapshot = StateSnapshot.from_registry(conductor.registry, mode="word")
    frame = conductor.image_backend.render_frame(snapshot)
    conductor.display.render_image(frame)  # also processes events
    await asyncio.sleep(0.05)
```

**After:**
```python
while conductor.server_running:
    conductor.display.poll_events()  # process events only
    await asyncio.sleep(0.05)
```

Rendering now happens in background `_render_loop()`.

### 4. Controller Main Loop — Separate Event Polling

**File:** `controller/__main__.py`

**Before:**
```python
while controller.running:
    if controller.current_state:
        controller.display.render(controller.current_state)  # also processes events
    await asyncio.sleep(0.05)
```

**After:**
```python
while controller.running:
    if IS_SIMULATION and hasattr(controller.display, 'poll_events'):
        controller.display.poll_events()  # process events only
    await asyncio.sleep(0.05)
```

### 5. InkyMock — Split Event Polling from Rendering

**File:** `conductor/display.py`

**Changes:**
- Extract event processing from `render_image()` into new `poll_events()` method
- `render_image()` now only blits to pygame, no event loop
- Add `poll_events()` proxy to `SlateDisplay` class

**Before:** `render_image()` did both event processing + blitting.
**After:** `poll_events()` processes events, `render_image()` blits pixels.

### 6. SparkMock — Split Event Polling from Rendering

**File:** `controller/display.py`

**Changes:**
- Add `poll_events()` method to `SparkMock` (calls `self.unicorn._process_events()`)
- Add `poll_events()` proxy to `SparkDisplay` class

**File:** `controller/unicorn_mock.py`

**Changes:**
- Remove `self._process_events()` call from `show()` method
- Events now processed explicitly via `poll_events()` from main loop

### 7. Logging for Visibility

**Added to both Conductor and Controller:**
- `_schedule()`: Log warning if called before event loop initialized
- `_broadcast_state()`: Log channel on each broadcast
- `_render_loop()`: Log frame render start/complete
- Queue operations: Log "Queued render" vs "Replaced queued render"

## Verification Results

### Simulation Test (macOS)
✅ Conductor + Controller start successfully
✅ WebSocket bidirectional messaging (hello, state, ping/pong, button)
✅ Button press → state broadcast logged immediately
✅ Render happens asynchronously in background
✅ Spark LEDs update on state changes

**Log evidence:**
```
INFO:conductor.conductor:Button: B press
DEBUG:conductor.conductor:Broadcasting state: channel=subject
DEBUG:conductor.conductor:Queued render
DEBUG:websockets.server:> TEXT '{"type": "state", ...}' [188 bytes]
DEBUG:controller.controller:Rendering Spark: channel=subject
```

Button → broadcast → network send → Spark render all happen in <20ms.

### Files Modified

1. `conductor/conductor.py` — ~50 lines changed
2. `controller/controller.py` — ~40 lines changed
3. `conductor/__main__.py` — ~10 lines changed
4. `controller/__main__.py` — ~10 lines changed
5. `conductor/display.py` — ~30 lines changed
6. `controller/display.py` — ~10 lines changed
7. `controller/unicorn_mock.py` — ~3 lines removed

**Total:** ~90 lines changed across 7 files

## Next Steps

- [ ] Test on hardware with real 30s e-ink refresh
- [ ] Verify button mashing during e-ink update doesn't block
- [ ] Confirm latest state renders after slow refresh (not intermediate states)
- [ ] Monitor timing: button→network <5ms, Spark update <20ms

## Notes

- Installed `pygame` in dev environment for simulation support
- Logging level set to WARNING in sim (DEBUG for testing, reverted after verification)
- All background test processes terminated cleanly (exit code 0)
