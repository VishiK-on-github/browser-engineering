import sdl2
from client import URL
from browser import Browser, mainloop


if __name__ == "__main__":
    import sys

    # used to init sdl lib
    # SDL_INIT_EVENTS used for init event handling
    sdl2.SDL_Init(sdl2.SDL_INIT_EVENTS)
    browser = Browser()
    url_str = sys.argv[1]
    url = URL(url_str)
    browser.new_tab(url)
    browser.raster_and_draw()
    mainloop(browser)
