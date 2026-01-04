import ctypes
import sys
import sdl2
import skia
import math
from tab import Tab
from helpers import get_font, linespace
from draw import DrawText, DrawOutline, DrawLine
from client import URL


WIDTH = 800
HEIGHT = 600
HSTEP = 13
VSTEP = 18
SCROLL_STEP = 50


class Browser:
    def __init__(self) -> None:
        
        self.chrome = Chrome(self)
    
        # creating SDL window
        self.sdl_window = \
            sdl2.SDL_CreateWindow(b"Browser", sdl2.SDL_WINDOWPOS_CENTERED, 
                                  sdl2.SDL_WINDOWPOS_CENTERED, WIDTH, HEIGHT, 
                                  sdl2.SDL_WINDOW_SHOWN)
        
        # creates skia surface
        # effectively a chunk of memory which stores pixel values
        # ct -> color type uses 8 bits for rgb and alpha
        # skia actually uses 32 bit int to represent rgba
        # this is a CPU-backed surface
        self.root_surface = \
            skia.Surface.MakeRaster(skia.ImageInfo.Make(WIDTH, HEIGHT, 
                                                        ct=skia.kRGBA_8888_ColorType, 
                                                        at=skia.kUnpremul_AlphaType))
        
        # creates a surface for common components, address bar, tabs, back button
        self.chrome_surface = skia.Surface(WIDTH, math.ceil(self.chrome.bottom))

        # will eventual store surface for the actual website content
        self.tab_surface = None

        self.tabs = []
        self.active_tab: Tab = None
        self.focus = None

        # sets the byte order
        if sdl2.SDL_BYTEORDER == sdl2.SDL_BIG_ENDIAN:
            self.RED_MASK = 0xff000000
            self.GREEN_MASK = 0x00ff0000
            self.BLUE_MASK = 0x0000ff00
            self.ALPHA_MASK = 0x000000ff

        else:
            self.RED_MASK = 0x000000ff
            self.GREEN_MASK = 0x0000ff00
            self.BLUE_MASK = 0x00ff0000
            self.ALPHA_MASK = 0xff000000


    def handle_down(self):
        """
        scroll down
        """

        self.active_tab.scrolldown()
        self.draw()


    def handle_up(self):
        """
        scroll up
        """

        self.active_tab.scrollup()
        self.draw()


    def handle_click(self, e):
        """
        executed when left mouse button clicked
        """
       
        if e.y < self.chrome.bottom:
            # set focus for browser to be None, since we 
            # are currently on browser common ui contents
            self.focus = None

            # use chrome class click event
            self.chrome.click(e.x, e.y)

            # render chrome address bar section
            self.raster_chrome()

        else:
            # check and set focus to website content
            if self.focus == "content":
                self.focus = "content"

                # unfocus from address bar
                self.chrome.blur()

                # TODO: why raster chrome?
                self.raster_chrome()
                
            url = self.active_tab.url
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)

            # we raster the common components if 
            # new address being added into address bar
            if self.active_tab.url != url:
                self.raster_chrome()

            self.raster_tab()

        self.draw()


    def handle_key(self, char):
        """
        executed when a key is pressed
        """

        # ignore key char if it falls beyond certain hex
        if not (0x20 <= ord(char) < 0x7f): return

        # if focus on chrome propagate event to chrome 
        # classes keypress and render chrome section
        if self.chrome.focus:
            self.chrome.keypress(char)
            self.raster_chrome()
            self.draw()

        # if focus on website content propagate event to 
        # chrome classes keypress and render chrome section
        elif self.focus == "content":
            self.active_tab.keypress(char)
            self.raster_tab()
            self.draw()


    def handle_enter(self):
        """
        executed when enter key is pressed
        """

        if self.chrome.focus:
            # execs fetching of the new uri
            self.chrome.enter()
            self.raster_tab()
            self.raster_chrome()
            self.draw()


    def handle_delete(self):
        """
        executed when delete key is pressed
        """

        self.chrome.delete()
        self.draw()

    
    def raster_tab(self):
        """
        compute which skia draw objects must be 
        drawn to the tab surface
        """

        tab_height = math.ceil(self.active_tab.document.height + 2 * VSTEP)

        # allocate new surface for tab
        if not self.tab_surface or tab_height != self.tab_surface.height():
            self.tab_surface = skia.Surface(WIDTH, tab_height)

        canvas = self.tab_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)
        self.active_tab.raster(canvas)


    def raster_chrome(self):
        """
        compute which skia draw objects must be 
        drawn to the chrome surface
        """

        canvas = self.chrome_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)

        # get all the common components objects to be drawn to the surface
        for cmd in self.chrome.paint():
            cmd.execute(canvas)


    def draw(self):
        """
        draw pixels on the SDL surface
        """

        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)

        tab_rect = skia.Rect.MakeLTRB(0, self.chrome.bottom, WIDTH, HEIGHT)
        tab_offset = self.chrome.bottom - self.active_tab.scroll

        canvas.save()

        # restrict tabs contents drawing to only tab_rects dimensions
        # any out of bounds should not be on sdl window. this action
        # affects all commands which run between and restore command
        canvas.clipRect(tab_rect)

        # move origin from (0, tab_offset)
        canvas.translate(0, tab_offset)
        self.tab_surface.draw(canvas, 0, 0)

        # revert the clipRect & translate operation
        canvas.restore()

        chrome_rect = skia.Rect.MakeLTRB(0, 0, WIDTH, self.chrome.bottom)
        canvas.save()

        # restrict common components drawing to only chrome_rects dimensions
        canvas.clipRect(chrome_rect)
        self.chrome_surface.draw(canvas, 0, 0)

        # undo clipRect
        canvas.restore()

        # make the root surface to an image
        skai_img = self.root_surface.makeImageSnapshot()

        # convert img -> bytes
        skia_bytes = skai_img.tobytes()

        # bits per pixel
        depth = 32

        # bytes per row
        pitch = 4 * WIDTH

        # wrap data in SDL surface without copying bytes
        sdl_surface = sdl2.SDL_CreateRGBSurfaceFrom(skia_bytes, WIDTH, 
                                                    HEIGHT, depth, pitch, 
                                                    self.RED_MASK, self.GREEN_MASK, 
                                                    self.BLUE_MASK, self.ALPHA_MASK)
        
        rect = sdl2.SDL_Rect(0, 0, WIDTH, HEIGHT)
        window_surface = sdl2.SDL_GetWindowSurface(self.sdl_window)

        # we copy bytes from sdl_surface to window - Blit is copying
        sdl2.SDL_BlitSurface(sdl_surface, rect, window_surface, rect)

        # used to signify drawing is done and to show the result on SDL window
        sdl2.SDL_UpdateWindowSurface(self.sdl_window)


    def new_tab(self, url):
        """
        spawns new tab
        """

        new_tab = Tab(HEIGHT - self.chrome.bottom)
        new_tab.load(url)
        self.tabs.append(new_tab)
        self.active_tab = new_tab
        self.raster_chrome()
        self.raster_tab()
        self.draw()

    
    def handle_quit(self):
        """
        destroy sdl window on pressing quit button
        """

        sdl2.SDL_DestroyWindow(self.sdl_window)


class Chrome:
    def __init__(self, browser: Browser) -> None:
        self.browser = browser
        self.focus = None
        self.address_bar = ""

        self.font = get_font(20, "normal", "roman")
        self.font_height = linespace(self.font)

        self.padding = 5
        self.tabbar_top = 0
        self.tabbar_bottom = self.font_height + 2 * self.padding

        # spacing, sizing for new tab button
        plus_width = self.font.measureText("+") + 2 * self.padding
        self.newtab_rect = skia.Rect.MakeLTRB(self.padding, self.padding, 
                                self.padding + plus_width, 
                                self.padding + self.font_height)
        
        # spacing, sizing for url bar
        self.urlbar_top = self.tabbar_bottom
        self.urlbar_bottom = self.urlbar_top + \
            self.font_height + 2 * self.padding

        # spacing, sizing for back button
        back_width = self.font.measureText("<") + 2 * self.padding
        self.back_rect = skia.Rect.MakeLTRB(self.padding, self.urlbar_top + self.padding, 
                              self.padding + back_width,
                              self.urlbar_bottom - self.padding)
        
        # spacing, sizing for address bar
        self.address_rect = skia.Rect.MakeLTRB(
            self.back_rect.top() + self.padding,
            self.urlbar_top + self.padding,
            WIDTH - self.padding,
            self.urlbar_bottom - self.padding)
        
        self.bottom = self.urlbar_bottom
        
    
    def tab_rect(self, i):
        """
        computing tab text sizes and creating a Rect object
        """

        tab_start = self.newtab_rect.right() + self.padding
        tab_width = self.font.measureText("Tab X") + 2 * self.padding

        return skia.Rect.MakeLTRB(
            tab_start + tab_width * i, self.tabbar_top,
            tab_start + tab_width * (i + 1), self.tabbar_bottom)
    

    def blur(self):
        """
        set the common ui focus to be none. 
        """

        self.focus = None
    

    def paint(self):
        """
        lays out draw objects to be rendered
        """

        cmds = []

        cmds.append(DrawLine(0, self.bottom, WIDTH, self.bottom, "black", 1))

        # drawing components for new tab button
        cmds.append(DrawOutline(self.newtab_rect, "black", 1))
        cmds.append(DrawText(self.newtab_rect.left() + self.padding,
                             self.newtab_rect.top(), "+", self.font, "black"))
        
        # determine items to be rendered in the tab bar
        for i, tab in enumerate(self.browser.tabs):

            bounds = self.tab_rect(i)
            cmds.append(DrawLine(bounds.left(), 0, bounds.left(), bounds.bottom(), "black", 1))
            cmds.append(DrawLine(bounds.right(), 0, bounds.right(), bounds.bottom(), "black", 1))
            cmds.append(DrawText(
                bounds.left() + self.padding, bounds.top() + self.padding,
                f"Tab {i}", self.font, "black"))
            
            # if tab is active tab get rid of the bottom line
            if tab == self.browser.active_tab:

                cmds.append(DrawLine(0, bounds.bottom(), bounds.left(), bounds.bottom(), "black", 1))
                cmds.append(DrawLine(bounds.right(), bounds.bottom(), WIDTH, bounds.bottom(), "black", 1))

        # back navigation button
        cmds.append(DrawOutline(self.back_rect, "black", 1))
        cmds.append(DrawText(self.back_rect.left() + self.padding,
                             self.back_rect.top(), "<", self.font, "black"))
        
        cmds.append(DrawOutline(self.address_rect, "black", 1))
        
        # executes when we have clicked on the address bar
        if self.focus == "Address Bar":
            cmds.append(DrawText(
                self.address_rect.left() + self.padding,
                self.address_rect.top(),
                self.address_bar, self.font, "black"))
            
            w = self.font.measureText(self.address_bar)
            cmds.append(DrawLine(
                self.address_rect.left() + self.padding + w,
                self.address_rect.top(),
                self.address_rect.left() + self.padding + w,
                self.address_rect.bottom(), "red", 1))

        # otherwise
        else:
            url = str(self.browser.active_tab.url)
            cmds.append(DrawText(
                self.address_rect.left() + self.padding,
                self.address_rect.top(),
                url, self.font, "black"))

        return cmds


    def click(self, x, y):
        """
        handles clicks events on back, new tab and address boxes
        """

        self.focus = None

        # click event has occured on new tab button
        if self.newtab_rect.contains(x, y):
            self.browser.new_tab(URL("https://browser.engineering/"))

        # click event has occured on back button
        elif self.back_rect.contains(x, y):
            self.browser.active_tab.go_back()
            self.browser.raster_chrome()
            self.browser.raster_tab()

        # click event has occured on address bar
        elif self.address_rect.contains(x, y):
            self.focus = "Address Bar"
            self.address_bar = ""

        # click event has occured on one of the tabs
        else:
            for i, tab in enumerate(self.browser.tabs):
                if self.tab_rect(i).contains(x, y):
                    self.browser.active_tab = tab
                    break

            self.browser.raster_tab()


    def keypress(self, char):
        """
        handles what needs to be done when a button is pressed
        """

        if self.focus == "Address Bar":
            self.address_bar += char
            return True

        return False


    def enter(self):
        """
        handles what needs to be done when enter/return key is pressed
        """

        if self.focus == "Address Bar":
            self.browser.active_tab.load(URL(self.address_bar))
            self.focus = None
            self.browser.focus = None

    
    def delete(self):
        """
        handles what needs to be done when delete key is pressed
        """

        if self.focus == "Address Bar":
            self.address_bar = self.address_bar[:-1]


def mainloop(browser):
    """
    main eventloop for sdl window
    """

    # used to read and write events to/from event queue
    event = sdl2.SDL_Event()

    while True:
        
        # keep polling for pending events
        while sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:

            # quit event
            if event.type == sdl2.SDL_QUIT:
                browser.handle_quit()
                sdl2.SDL_Quit()
                sys.exit()

            # click event
            elif event.type == sdl2.SDL_MOUSEBUTTONUP:
                browser.handle_click(event.button)

            # key down event
            elif event.type == sdl2.SDL_KEYDOWN:

                if event.key.keysym.sym == sdl2.SDLK_RETURN:
                    browser.handle_enter()

                elif event.key.keysym.sym == sdl2.SDLK_DOWN:
                    browser.handle_down()

                elif event.key.keysym.sym == sdl2.SDLK_UP:
                    browser.handle_up()

            # text key event
            elif event.type == sdl2.SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode("utf8"))
