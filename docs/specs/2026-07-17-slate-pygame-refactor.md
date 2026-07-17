# Slate Display: Tkinter → Pygame Refactor

**Goal:** Replace Tkinter+PIL image rendering with direct pygame canvas for consistency, better control, and future extensibility.

---

## Current State (Tkinter)

**Implementation:**
- `conductor/display.py` → `InkyMock` class
- Creates PIL `Image` object (640×400)
- Uses `ImageDraw` to render menu strip + text
- Converts to `ImageTk.PhotoImage` for Tkinter `Label`
- Updates label on each state change
- Window created once, image updated in place

**Issues:**
- Tkinter + PIL + ImageTk layer cake
- Can't easily add visual effects (flash, pulse, grid)
- Inconsistent with Spark (pygame)
- PIL drawing API is verbose

---

## New Design (Pygame)

### Window Specs

**Size:** 640×400 (matches Inky Impression 4" aspect ratio)
**Title:** "Flyball Slate Mock (Inky Impression 7-color)"
**Background:** White (e-paper feel)

### Layout (Landscape, Inky orientation)

```
┌─────────────────────────────────────────────┐
│ [A] │                                        │
│  S  │                                        │
│  u  │        MAIN AREA                       │
│  b  │     (Generated Image)                  │
│ [B] │      560×330 px                        │
│  C  │     Placeholder: "No image"            │
│  o  │                                        │
│  n  │                                        │
│ [C] │────────────────────────────────────────│
│  S  │ SENTENCE: "Detective · Neon Bar ·..."  │
│  t  │ ENGINE: Loop ▶ 8s │ Op: SWAP │ Q: 0   │
│ [D] │                                        │
│ Eng │                                        │
└─────────────────────────────────────────────┘
 80px   560px wide content area
```

### Components

#### 1. Left Menu Strip (80×400 px)

**Position:** x=0, y=0, width=80, height=400
**Channels:** 4 buttons, 100px tall each

For each channel (Subject/Context/Style/Engine):
- **Rect:** `pygame.draw.rect()` with channel color
- **Label:** Button letter + channel name, rotated 90° or vertical text
- **Active state:** Filled rect with white text
- **Inactive state:** Outline rect with colored text

**Colors:**
- Subject: `(0, 200, 80)` green
- Context: `(0, 100, 200)` blue
- Style: `(200, 0, 150)` magenta
- Engine: `(200, 150, 0)` amber

#### 2. Main Image Area (560×330 px)

**Position:** x=80, y=10, width=560, height=330
**Background:** Light gray `(240, 240, 240)`
**Border:** 2px black outline

**Content (M1 - no real images):**
- Centered text: "Generated Image"
- Subtitle: `f"Candidate: {state.candidate}"`
- Gray placeholder box

**Content (M2+ - real images):**
- Render PIL image onto pygame surface
- Scale to fit 560×330 maintaining aspect ratio
- Center in area

#### 3. Status Ribbon (640×60 px)

**Position:** x=0, y=340, width=640, height=60
**Background:** White
**Top border:** 1px gray line

**Line 1 (y=345):**
- Font: 14pt bold
- Text: Assembled sentence from committed channels
- Format: `"Subject · Context · Style"` or `"[empty]"`
- Color: Black

**Line 2 (y=370):**
- Font: 12pt regular
- Engine status: `f"Loop: {'▶' if loop else '▫'} {speed}s │ Op: {operator} │ Queue: {depth}"`
- Color: Dark gray `(64, 64, 64)`

### Rendering

**Text Rendering:**
- Use `pygame.font.SysFont()` for clean system fonts
- Fallback: `pygame.font.Font(None, size)` if no system font

**Update Strategy:**
- Clear entire surface each render (white background)
- Redraw all components from state
- `pygame.display.flip()` to update window
- No partial updates needed (e-paper metaphor: full refresh)

**Performance:**
- Full redraw ~1-2ms on modern machine
- Acceptable for e-paper simulation (updates on commits only, not every frame)

---

## Implementation Plan

### Phase 1: Scaffold Pygame Window

**File:** `conductor/display.py`

1. Import pygame at top (conditional on `IS_SIMULATION`)
2. In `InkyMock.__post_init__()`:
   - `pygame.init()`
   - `pygame.display.set_mode((640, 400))`
   - `pygame.display.set_caption("Flyball Slate Mock (Inky Impression)")`
   - Create surface: `self.screen`
   - Load fonts: `self.font_large`, `self.font_small`

3. In `InkyMock.close()`:
   - Clear to white
   - `pygame.quit()`

### Phase 2: Render Components

**Method:** `InkyMock.render(state: StateSnapshot)`

1. **Clear surface**
   ```python
   self.screen.fill((255, 255, 255))  # White background
   ```

2. **Draw menu strip**
   - Loop through 4 channels
   - For each: `pygame.draw.rect()` for background/outline
   - Render text (vertical or rotated)
   - Highlight active channel

3. **Draw main area placeholder**
   - `pygame.draw.rect()` for border
   - Fill with light gray
   - Center text: "Generated Image"
   - Show current candidate below

4. **Draw status ribbon**
   - Top border line
   - Render sentence text (line 1)
   - Render engine status (line 2)

5. **Update display**
   ```python
   pygame.display.flip()
   ```

### Phase 3: Text Rendering Helper

**Method:** `InkyMock._render_text(text, x, y, font, color, align='left')`

```python
def _render_text(self, text, x, y, font, color, align='left'):
    """Render text at position with alignment."""
    surface = font.render(text, True, color)
    rect = surface.get_rect()

    if align == 'center':
        rect.center = (x, y)
    elif align == 'right':
        rect.right = x
        rect.top = y
    else:  # left
        rect.left = x
        rect.top = y

    self.screen.blit(surface, rect)
```

### Phase 4: Vertical Text for Menu

**Options:**
1. **Rotate rendered text:**
   ```python
   text_surf = font.render("Subject", True, color)
   rotated = pygame.transform.rotate(text_surf, 90)
   self.screen.blit(rotated, (x, y))
   ```

2. **Render character-by-character vertically:**
   ```python
   for i, char in enumerate(label):
       char_surf = font.render(char, True, color)
       self.screen.blit(char_surf, (x, y + i*15))
   ```

Choose option 2 for simplicity (easier positioning, cleaner look).

### Phase 5: Integration & Testing

1. Remove old Tkinter/PIL code
2. Keep `InkyMock` interface unchanged (still implements `Display`)
3. Test with existing Controller/Conductor flow
4. Verify:
   - Window opens on conductor start
   - Updates when state changes
   - Shows active channel highlight
   - Displays sentence correctly
   - Closes cleanly on exit

---

## File Changes

### Modified Files

**`conductor/display.py`**
- Remove: `import tkinter`, `from PIL import ImageTk`
- Add: `import pygame`
- Rewrite: `InkyMock` class completely
- Keep: `SlateDisplay` wrapper (unchanged)

**`requirements-dev.txt`**
- Already has pygame (added for Spark mock)
- No changes needed

**`docs/changelog-debug.md`**
- Add entry documenting refactor

### No Changes Needed

- `conductor/conductor.py` (uses Display interface)
- `shared/interfaces/display.py` (interface unchanged)
- Tests (use Display interface, not implementation)

---

## Testing Plan

### Manual Testing

**Terminal 1:**
```bash
make conductor
```

**Expected:**
- Pygame window opens (640×400)
- White background, clean layout
- Menu strip shows 4 channels (Subject highlighted green)
- Main area shows "Generated Image" placeholder
- Status ribbon shows `"[empty]"` sentence

**Terminal 2:**
```bash
make controller
```

**Expected:**
- Spark pygame window opens (separate from Slate)
- Press `b` in controller terminal
- Slate window updates: sentence changes as options committed

**Actions to test:**
1. Press `c` in conductor → Style channel highlighted (magenta)
2. Press `b` in controller → cycle Style options
3. Press `x` in controller → commit Style
4. Check Slate ribbon → sentence updated
5. Press `d` in conductor → Engine channel highlighted (amber)
6. Check Slate ribbon → engine status shown
7. Press `q` → both windows close cleanly

### Automated Testing

**Update existing tests:**
- `tests/test_display_mocks.py` already tests via interface
- No changes needed (pygame mock should pass same interface tests)

**Visual regression:**
- Take screenshot of Slate window after refactor
- Compare layout to spec diagram
- Verify colors, fonts, alignment

---

## Success Criteria

✓ Slate window opens as pygame window (not Tkinter)
✓ Layout matches spec (menu strip + main + ribbon)
✓ Active channel highlighted correctly
✓ Sentence updates when options committed
✓ Engine status displays when Engine channel active
✓ Text rendering clean and readable
✓ Window closes without errors
✓ Both Spark and Slate use pygame (consistency)
✓ No Tkinter/PIL dependencies in conductor/display.py

---

## Future Enhancements (Post-Refactor)

Once pygame is in place, easy to add:

- **Visual feedback:** Flash on commit, pulse active channel
- **Grid overlay:** Subtle grid to show e-paper "pixel" boundaries
- **Color palette preview:** Show Inky 7-color palette in corner
- **Image rendering:** Drop PIL images directly onto surface (M2)
- **Animations:** Smooth transitions between states
- **Theme:** E-paper color scheme (cream background, limited palette)

---

## Estimated Effort

- **Phase 1-2:** 20 min (scaffold + basic rendering)
- **Phase 3-4:** 15 min (text helpers + menu strip)
- **Phase 5:** 10 min (testing + cleanup)
- **Total:** ~45 min

---

## Risk Assessment

**Low risk:**
- Display interface unchanged → no impact on Conductor logic
- Pygame already working for Spark → known good dependency
- Can test alongside existing Tkinter version before replacing

**Rollback:**
- Keep `conductor/display.py.bak` with Tkinter version
- Easy to revert if pygame version has issues

---

## Approval Checkpoints

**Before coding:**
- [ ] User approves spec layout
- [ ] User approves pygame approach
- [ ] User approves menu strip design

**After Phase 2:**
- [ ] Window opens with basic layout
- [ ] Screenshot matches spec

**After Phase 5:**
- [ ] All manual tests pass
- [ ] Both mocks use pygame
- [ ] Commit + document in changelog

---

## Open Questions

1. **Menu text orientation:** Rotated 90° or vertical character-by-character?
   - **Recommendation:** Vertical (easier to read, cleaner)

2. **Font choices:** System font or pygame default?
   - **Recommendation:** Try Helvetica/Arial, fallback to pygame default

3. **Sentence truncation:** If sentence > 560px wide, truncate or scroll?
   - **Recommendation:** Truncate with "..." for M1, scroll in M2

4. **Window position:** Center screen or top-left?
   - **Recommendation:** Let OS decide (default pygame behavior)

---

Ready to proceed?
