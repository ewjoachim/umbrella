import curses
import logging
import time
import random
import sys

logger = logging.getLogger(__file__)

OPEN_UMBRELLA = r"""
     .
    _|_
 .-'   '-.
/         \
^^^^^|^^^^^
     |
   \_/""".splitlines()[1:]
CLOSED_UMBRELLA = r"""
     .
     |
    / \
    | |
    | |
    ^|^
   \_/""".splitlines()[1:]

RAIN = "\\"
REFRESH_TIME = 0.02
MIN_SIZE = (25, 25)
DROPS_RATIO = 0.4
INSTRUCTIONS = (
    "(q)uit |"
    " left, right: move umbrella |"
    " up, down: open or close umbrella")


class ScreenTooSmall(Exception):
    pass


class Drop(object):

    class FellOnSomething(Exception):
        pass

    char = "\\"

    def __init__(self, window):
        height, width = window.getmaxyx()
        init_point = random.randint(-height + 1, width - 1)
        self.x = init_point if init_point >= 0 else 0
        self.y = - init_point if init_point < 0 else 0
        self.window = window

    def draw(self, char):
        self.window.addch(self.y, self.x, char)

    def fall(self, bottom):
        try:
            self.draw(" ")
            self.x += 1
            self.y += 1
            char = chr(self.window.inch(self.y, self.x) & (2 ** 8 - 1))
            if char != " ":
                raise self.FellOnSomething
            self.draw(char=self.char)
        except curses.error:
            raise self.FellOnSomething


class Umbrella(object):
    def __init__(self, window):
        self.window = window
        height, width = window.getmaxyx()
        self.y = height // 2 - len(OPEN_UMBRELLA) // 2
        self.x = width // 2
        self.state = "open"
        self.umbrella_width = max(len(line) for line in OPEN_UMBRELLA)
        self.umbrella_height = len(OPEN_UMBRELLA)

    def draw(self):
        umbrella = OPEN_UMBRELLA if self.state == "open" else CLOSED_UMBRELLA
        for i, line in enumerate(umbrella):
            spaces = len(line) - len(line.lstrip())
            self.window.addstr(self.y + i, self.x + spaces, line.lstrip())

    def undraw(self):
        umbrella = OPEN_UMBRELLA if self.state == "open" else CLOSED_UMBRELLA
        for i, line in enumerate(umbrella):
            spaces = len(line) - len(line.lstrip())
            self.window.addstr(
                self.y + i, self.x + spaces, " " * len(line.lstrip()))

    def loop(self, dx, state):
        height, width = self.window.getmaxyx()
        self.undraw()
        self.state = state
        self.x += dx
        self.x = min(max(self.x, 1), width - self.umbrella_width - 1)
        self.draw()


def setup_logging():
    hdlr = logging.FileHandler("umbrella.log")
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.DEBUG)


def main():
    try:
        curses.wrapper(loop)
    except ScreenTooSmall:
        print("Screen is too small")
        sys.exit(1)


def get_keypress(window):
    try:
        keypress = window.getkey()
    except curses.error:
        keypress = None

    if keypress == "q":
        sys.exit(0)

    # it seems OSX has a problem with the escape codes.
    if keypress == "\x1b":
        keypress = {
            "[D": curses.KEY_LEFT, "[C": curses.KEY_RIGHT,
            "[B": curses.KEY_DOWN, "[A": curses.KEY_UP,
        }.get(window.getkey() + window.getkey(), None)

    return keypress


def loop(full_screen):
    full_screen.keypad(False)
    full_screen.leaveok(True)

    height, width = full_screen.getmaxyx()
    window = curses.newwin(height - 1, width, 0, 0)
    bottom = curses.newwin(1, width, height - 1, 0)
    bottom.addstr(0, 0, INSTRUCTIONS)
    bottom.refresh()

    setup_logging()
    curses.curs_set(0)
    window.nodelay(True)
    drops = set()
    umbrella = Umbrella(window)
    state = "open"
    while True:
        umbrella_dx = 0
        keypress = get_keypress(window)
        if keypress == curses.KEY_LEFT:
            umbrella_dx = -1
        elif keypress == curses.KEY_RIGHT:
            umbrella_dx = 1
        elif keypress == curses.KEY_UP:
            state = "open"
        elif keypress == curses.KEY_DOWN:
            state = "close"
        else:
            keypress = None

        height, width = window.getmaxyx()
        if width < MIN_SIZE[0] or height < MIN_SIZE[1]:
            raise ScreenTooSmall

        if len(drops) < height * width * DROPS_RATIO:
            drops.add(Drop(window))

        for drop in list(drops):
            try:
                drop.fall(bottom)
            except Drop.FellOnSomething:
                drops.remove(drop)
                drops.add(Drop(window))
        umbrella.loop(dx=umbrella_dx, state=state)

        window.refresh()
        bottom.refresh()
        time.sleep(REFRESH_TIME)
        curses.update_lines_cols()


if __name__ == '__main__':
    main()
