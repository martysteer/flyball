"""Test GPIO button listener hardware detection and fallback."""


def test_controller_has_gpio_flag():
    """controller.buttons exposes HAS_GPIO flag."""
    from controller import buttons
    assert hasattr(buttons, "HAS_GPIO")
    assert isinstance(buttons.HAS_GPIO, bool)


def test_conductor_has_gpio_flag():
    """conductor.buttons exposes HAS_GPIO flag."""
    from conductor import buttons
    assert hasattr(buttons, "HAS_GPIO")
    assert isinstance(buttons.HAS_GPIO, bool)


def test_gpio_listener_fallback_to_keyboard():
    """GPIOButtonListener without GPIO falls back to KeyboardListener."""
    from controller.buttons import GPIOButtonListener, HAS_GPIO
    if not HAS_GPIO:
        listener = GPIOButtonListener(device="spark")
        assert listener.fallback is not None


def test_gpio_listener_has_button_interface():
    """GPIOButtonListener has on/start/stop methods."""
    from controller.buttons import GPIOButtonListener
    listener = GPIOButtonListener(device="spark")
    assert callable(getattr(listener, "on", None))
    assert callable(getattr(listener, "start", None))
    assert callable(getattr(listener, "stop", None))
