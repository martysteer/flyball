"""Buttons seam: keyboard sim now, GPIO (gpiozero/gpiod) in M4."""
import asyncio
import sys
import termios
import tty


class KeyboardButtons:
    """Maps single keypresses to button names via keymap; 'q' raises SystemExit.

    keymap example: {"a": "A", "b": "B", "x": "X", "y": "Y"}
    on_button: async def(btn_name)
    """

    def __init__(self, keymap, on_button):
        self.keymap = keymap
        self.on_button = on_button

    async def run(self):
        loop = asyncio.get_running_loop()
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        queue = asyncio.Queue()
        loop.add_reader(fd, lambda: queue.put_nowait(sys.stdin.read(1)))
        try:
            while True:
                ch = (await queue.get()).lower()
                if ch == "q":
                    raise SystemExit
                btn = self.keymap.get(ch)
                if btn:
                    await self.on_button(btn)
        finally:
            loop.remove_reader(fd)
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
