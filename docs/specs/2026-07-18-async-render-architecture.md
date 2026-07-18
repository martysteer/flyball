# Async Render Architecture

**Date:** 2026-07-18
**Status:** Implemented
**Context:** M1 milestone — state machine + bidirectional messaging

## Problem Statement

Two issues on hardware:

1. **One-way messaging**: Slate (Conductor) buttons update correctly, but Spark (Controller) LEDs don't update. Messages flow only Controller→Conductor, not reverse.

2. **Display blocks state updates**: E-ink refresh takes ~30s and blocks button handling. The 35s debounce workaround still blocks when render happens. Need to decouple: state updates should broadcast immediately over WebSocket, display rendering should happen asynchronously without blocking buttons.

## Root Causes

### Issue 1: Silent failures in message flow
- `conductor.py:127-137` — `_schedule()` returns silently if `self.loop` is None
- No logging to trace where messages succeed/fail
- WebSocket broadcast may send to empty client list (silent early return)

### Issue 2: Synchronous blocking render
- `conductor.py:166` — `display.render_image(frame)` called synchronously from `_broadcast_state()`
- Real Inky at `conductor/display.py:146` calls `inky.show()` which blocks 30s
- Button handlers call `_broadcast_state()` and block until render completes
- State broadcast happens before render (WebSocket is fine), but function doesn't return for 30s

## Solution: Async Render Queue

Use stdlib `asyncio.Queue(maxsize=1)` (precedent: `shared/buttons.py:24`).

**Flow:**
1. Button press → state update → broadcast state over WebSocket (fast, <5ms)
2. Enqueue render frame (non-blocking)
3. Background render loop consumes queue, updates display (slow, 30s, but doesn't block)
4. If new frame arrives while rendering: old frame discarded, new frame queued (maxsize=1 ensures latest-only)

**Benefits:**
- Buttons never block (state updates return immediately)
- Network messages send immediately (WebSocket broadcast not delayed by display)
- Display always shows latest state (old renders dropped if new state arrives)
- Removes need for 35s debounce hack

## Architecture Decisions

### Why Queue in Main Classes (not Display)?
- **Chosen:** Queue lives in Conductor/Controller classes
- **Alternative:** Queue inside Display classes
- **Rationale:** Display stays synchronous hardware wrapper. Async coordination lives in application layer.

### Why `maxsize=1`?
- Only latest state matters for UI
- Old renders discarded if new state arrives during slow refresh
- Simple eviction: `get_nowait()` + `put_nowait()`

### Why Not MQTT?
Current WebSocket transport sufficient for point-to-point (one Conductor, one Controller). MQTT useful for:
- Many-to-many (multiple Controllers/Conductors)
- QoS guarantees (retain last message for late joiners)
- Broker-based architecture

Can revisit MQTT in later milestones if architecture evolves.

## Event Loop Separation

**Before:** Main loop called `render()` every frame (~20 FPS) to process pygame events + update display.

**After:**
- `poll_events()` — process pygame events only (keyboard, window close)
- `render()` / `render_image()` — update display pixels only
- Main loop calls `poll_events()` at 20 FPS
- Async render loop calls `render()` when state changes

Separation prevents redundant renders and decouples input from output.

## Verification

### Simulation Test
1. Start Conductor + Controller
2. Press buttons rapidly
3. Verify: Spark updates immediately, no lag, no blocking

### Hardware Test (future)
1. Press Slate button → triggers 30s e-ink refresh
2. Press another button during refresh
3. Verify: second button press registers immediately
4. Verify: latest state renders after first refresh completes (not intermediate state)

### Timing Requirements
- Button → network broadcast: <5ms
- Spark LED update: <20ms from button press
- Slate e-ink: 30-40s (blocking in background only, not main thread)

## Trade-offs

| Approach | Lines | Pros | Cons |
|----------|-------|------|------|
| **Async queue in main** | ~90 | Minimal, stdlib only, clean separation | Queue visible in main class |
| Queue in Display | ~120 | Encapsulated | Display becomes async, breaks interface |
| Keep 35s debounce | 0 | No changes | Still blocks, doesn't solve root cause |
| Thread pool | ~80 | Non-blocking | Mixing async+threads, harder to reason |

**Chosen:** Async queue in main classes. Smallest diff, stdlib patterns only, solves both issues completely.
