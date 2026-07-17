"""Test button listeners."""

from controller.buttons import KeyboardListener


def test_keyboard_listener_initializes():
    """KeyboardListener can be created."""
    listener = KeyboardListener(device="spark")
    assert listener.device == "spark"


def test_keyboard_listener_registers_handler():
    """Can register button handler."""
    listener = KeyboardListener(device="spark")

    received = []

    def on_button(btn, event):
        received.append((btn, event))

    listener.on(on_button)
    # Handler registered; would need actual keyboard input to test
