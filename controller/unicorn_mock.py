#!/usr/bin/env python3
"""
Proxy implementation of UnicornHATMini for macOS
Simulates the UnicornHATMini hardware using pygame for display
"""

import pygame
import sys
import time
import colorsys
from PIL import Image

class UnicornHATMiniBase:
    # Constants matching the actual Unicorn HAT Mini
    WIDTH = 17
    HEIGHT = 7
    
    # Button constants
    BUTTON_A = 5
    BUTTON_B = 6
    BUTTON_X = 16
    BUTTON_Y = 24
    
    def __init__(self, spi_max_speed_hz=600000):
        """Initialize proxy Unicorn HAT Mini emulator"""
        # We ignore the SPI speed parameter since this is a simulation
        
        # Initialize pixel data structure
        self.disp = [[0, 0, 0] for _ in range(self.WIDTH * self.HEIGHT)]
        self.brightness = 0.5
        self._rotation = 0
        self.button_states = {
            self.BUTTON_A: False,
            self.BUTTON_B: False,
            self.BUTTON_X: False,
            self.BUTTON_Y: False
        }
        self.button_callback = None
        
        # Scale factor for larger display (makes it easier to see)
        self.scale = 15
        
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((self.WIDTH * self.scale, self.HEIGHT * self.scale))
        pygame.display.set_caption("Unicorn HAT Mini Emulator")
        
        # Draw initial state
        self.show()
        
        # Show help text on startup
        font = pygame.font.SysFont(None, 24)
        print("Unicorn HAT Mini Emulator")
        print("Use A/B/X/Y or Arrow keys to simulate buttons")
        
    def __del__(self):
        """Clean up pygame on exit"""
        try:
            pygame.quit()
        except:
            pass
    
    def set_pixel(self, x, y, r, g, b):
        """Set a single pixel."""
        if self._rotation == 90:
            x, y = y, self.WIDTH - 1 - x
        elif self._rotation == 180:
            x, y = self.WIDTH - 1 - x, self.HEIGHT - 1 - y
        elif self._rotation == 270:
            x, y = self.HEIGHT - 1 - y, x
            
        if 0 <= x < self.WIDTH and 0 <= y < self.HEIGHT:
            offset = x * self.HEIGHT + y
            self.disp[offset] = [r, g, b]
    
    def set_all(self, r, g, b):
        """Set all pixels to the same color."""
        for i in range(len(self.disp)):
            self.disp[i] = [r, g, b]
    
    def set_brightness(self, brightness):
        """Set the display brightness (0.0 to 1.0)."""
        self.brightness = max(0.0, min(1.0, brightness))
    
    def set_rotation(self, rotation=0):
        """Set display rotation (0, 90, 180, 270)."""
        if rotation not in [0, 90, 180, 270]:
            raise ValueError("Rotation must be one of 0, 90, 180, 270")
        self._rotation = rotation
    
    def get_shape(self):
        """Return the display shape based on rotation."""
        if self._rotation in [90, 270]:
            return self.HEIGHT, self.WIDTH
        else:
            return self.WIDTH, self.HEIGHT
    
    def clear(self):
        """Clear the display."""
        self.set_all(0, 0, 0)
    
    def set_image(self, image, offset_x=0, offset_y=0, wrap=False, bg_color=(0, 0, 0)):
        """Set pixels from a PIL image."""
        image_width, image_height = image.size
        
        if image.mode != "RGB":
            image = image.convert('RGB')
        
        display_width, display_height = self.get_shape()
        
        for y in range(display_height):
            for x in range(display_width):
                r, g, b = bg_color
                i_x = x + offset_x
                i_y = y + offset_y
                
                if wrap:
                    i_x = i_x % image_width
                    i_y = i_y % image_height
                
                if 0 <= i_x < image_width and 0 <= i_y < image_height:
                    r, g, b = image.getpixel((i_x, i_y))
                
                self.set_pixel(x, y, r, g, b)
    
    def on_button_pressed(self, callback):
        """Register callback for button events."""
        self.button_callback = callback
    
    def read_button(self, pin):
        """Read the current state of a button."""
        # Process any pending events
        self._process_events()
        return self.button_states.get(pin, False)
    
    def show(self):
        """Update the display."""
        # Process any pending events
        self._process_events()
        
        # Draw each pixel
        for x in range(self.WIDTH):
            for y in range(self.HEIGHT):
                offset = x * self.HEIGHT + y
                if offset < len(self.disp):
                    r, g, b = self.disp[offset]
                    # Apply brightness
                    r = int(r * self.brightness)
                    g = int(g * self.brightness)
                    b = int(b * self.brightness)
                    
                    # Draw a rectangle for each pixel
                    rect = pygame.Rect(
                        x * self.scale, 
                        y * self.scale, 
                        self.scale, 
                        self.scale
                    )
                    pygame.draw.rect(self.screen, (r, g, b), rect)
                    
                    # Draw a thin border around each pixel
                    pygame.draw.rect(
                        self.screen, 
                        (64, 64, 64), 
                        rect, 
                        1
                    )
        
        # Draw button state indicators
        self._draw_button_indicators()
        
        # Update the display
        pygame.display.flip()
    
    def _draw_button_indicators(self):
        """Draw button indicators at the bottom of the screen."""
        buttons = [
            ("A", self.BUTTON_A, 1),
            ("B", self.BUTTON_B, 5),
            ("X", self.BUTTON_X, 11),
            ("Y", self.BUTTON_Y, 15)
        ]
        
        indicator_y = self.HEIGHT * self.scale - self.scale // 2
        
        for label, button, x_pos in buttons:
            pressed = self.button_states.get(button, False)
            color = (255, 0, 0) if pressed else (64, 64, 64)
            
            # Draw a small circle to represent the button
            pygame.draw.circle(
                self.screen,
                color,
                (x_pos * self.scale // 1, indicator_y),
                self.scale // 3
            )
    
    def _process_events(self):
        """Process pygame events for button presses."""
        # Key mapping
        key_map = {
            pygame.K_a: self.BUTTON_A,
            pygame.K_b: self.BUTTON_B,
            pygame.K_x: self.BUTTON_X,
            pygame.K_y: self.BUTTON_Y,
            pygame.K_UP: self.BUTTON_A,
            pygame.K_LEFT: self.BUTTON_B,
            pygame.K_DOWN: self.BUTTON_X,
            pygame.K_RIGHT: self.BUTTON_Y
        }
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key in key_map:
                    button = key_map[event.key]
                    # Update button state
                    self.button_states[button] = True
                    # Call callback if registered
                    if self.button_callback:
                        self.button_callback(button)
            elif event.type == pygame.KEYUP:
                if event.key in key_map:
                    button = key_map[event.key]
                    # Update button state
                    self.button_states[button] = False


# Simple test if run directly
if __name__ == "__main__":
    unicornhatmini = UnicornHATMiniBase()
    
    try:
        hue = 0
        while True:
            # Create a rainbow pattern
            for y in range(unicornhatmini.HEIGHT):
                for x in range(unicornhatmini.WIDTH):
                    r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(
                        ((x + y) / 30.0 + hue) % 1.0, 
                        1.0, 
                        1.0
                    )]
                    unicornhatmini.set_pixel(x, y, r, g, b)
            
            unicornhatmini.show()
            time.sleep(0.05)
            hue += 0.01
            
    except KeyboardInterrupt:
        unicornhatmini.clear()
        unicornhatmini.show()