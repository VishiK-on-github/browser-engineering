import sdl2
from client import URL
from browser import Browser, mainloop


if __name__ == "__main__":
    import sys

    # used to init sdl lib
    # SDL_INIT_EVENTS used for init event handling
    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser()

    if len(sys.argv) < 2:
        url_str = "file:///default/default.html"
    else:
        url_str = sys.argv[1]

    url = URL(url_str)
    browser.new_tab(url)
    browser.draw()
    mainloop(browser)
