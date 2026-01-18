import ctypes
import sys
import threading
import urllib
import math

import sdl2
import skia

from helpers import get_font, linespace, paint_tree, tree_to_list
from draw import DrawText, DrawOutline, DrawLine
from client import URL
from task import Task, TaskRunner
from document_layout import DocumentLayout
from html_parser import HTMLParser
from css_parser import CSSParser, style, cascade_priority
from element import Element
from text import Text
from js_context import JSContext
from profiler import MeasureTime
from commit import CommitData


WIDTH = 800
HEIGHT = 600
HSTEP = 13
VSTEP = 18
SCROLL_STEP = 50
REFRESH_RATE_SEC = 0.033
DEFAULT_STYLE_SHEET = CSSParser(open("./browser.css").read()).parse()


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
        self.address_bar = ""
        self.lock = threading.Lock()
        self.active_tab_url = None
        self.active_tab_scroll = 0

        # for profiling
        self.measure = MeasureTime()
        threading.current_thread().name = "Browser Thread"

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

        self.animation_timer = None
        self.active_tab_height = 0
        self.needs_raster_and_draw = False
        self.needs_animation_frame = False
        self.active_tab_display_list = None


    def commit(self, tab, data):
        """
        finalizes which components must 
        be drawn to the screen
        """

        self.lock.acquire(blocking=True)

        # to prevent an inactive tabs content 
        # from being drawn on active tab
        if tab == self.active_tab:
            self.active_tab_url = data.url

            if data.scroll != None:
                self.active_tab_scroll = data.scroll

            self.active_tab_height = data.height

            if data.display_list:
                self.active_tab_display_list = data.display_list

            # after commit data has been finalized we want to 
            # raster and draw the committed components to the window
            self.animation_timer = None
            self.set_needs_raster_and_draw()

        self.lock.release()


    def clamp_scroll(self, scroll):
        """
        helps limit amount of scrolling up & down
        """

        height = self.active_tab_height
        max_scroll = height - (HEIGHT - self.chrome.bottom)

        return max(0, min(scroll, max_scroll))


    def handle_down(self):
        """
        scroll down
        """

        self.lock.acquire(blocking=True)

        if not self.active_tab_height:
            self.lock.release()
            return

        self.active_tab_scroll = self.clamp_scroll(self.active_tab_scroll + SCROLL_STEP)
        self.set_needs_raster_and_draw()
        self.needs_animation_frame = True
        self.lock.release()


    def handle_up(self):
        """
        scroll up
        """

        self.lock.acquire(blocking=True)

        if not self.active_tab_height:
            self.lock.release()
            return

        self.active_tab_scroll = self.clamp_scroll(self.active_tab_scroll - SCROLL_STEP)
        self.set_needs_raster_and_draw()
        self.needs_animation_frame = True
        self.lock.release()


    def handle_click(self, e):
        """
        executed when left mouse button clicked
        """

        self.lock.acquire(blocking=True)

        if e.y < self.chrome.bottom:
            # set focus for browser to be None, since we 
            # are currently on browser common ui contents
            self.focus = None

            # use chrome class click event
            self.chrome.click(e.x, e.y)

            self.set_needs_raster_and_draw()

        else:
            # check and set focus to website content
            if self.focus != "content":
                self.focus = "content"

                # unfocus from address bar
                self.chrome.focus = None

                self.set_needs_raster_and_draw()
            
            self.chrome.blur()
            tab_y = e.y - self.chrome.bottom
            task = Task(self.active_tab.click, e.x, tab_y)
            self.active_tab.task_runner.schedule_task(task)

        self.lock.release()


    def handle_key(self, char):
        """
        executed when a key is pressed
        """

        self.lock.acquire(blocking=True)

        # ignore key char if it falls beyond certain hex
        if not (0x20 <= ord(char) < 0x7f): return

        # if focus on chrome propagate event to chrome 
        # classes keypress and render chrome section
        if self.chrome.keypress(char):
            self.set_needs_raster_and_draw()

        # if focus on website content propagate event to 
        # chrome classes keypress and render chrome section
        elif self.focus == "content":
            task = Task(self.active_tab.keypress, char)
            self.active_tab.task_runner.schedule_task(task)

        self.lock.release()


    def handle_enter(self):
        """
        executed when enter key is pressed
        """
        
        self.lock.acquire(blocking=True)

        if self.chrome.enter():
            self.set_needs_raster_and_draw()

        self.lock.release()


    def handle_delete(self):
        """
        executed when delete key is pressed
        """

        self.chrome.delete()
        self.raster_chrome()
        self.draw()


    def raster_tab(self):
        """
        compute which skia draw objects must be 
        drawn to the tab surface
        """

        if self.active_tab_height == None:
            return

        # allocate new surface for tab
        if not self.tab_surface or self.active_tab_height != self.tab_surface.height():
            self.tab_surface = skia.Surface(WIDTH, self.active_tab_height)

        canvas = self.tab_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)

        for cmd in self.active_tab_display_list:
            cmd.execute(canvas)


    def schedule_animation_frame(self):
        """
        schedule a run animation frame in tasks queue
        """

        def callback():

            self.lock.acquire(blocking=True)

            scroll = self.active_tab_scroll
            active_tab = self.active_tab
            self.needs_animation_frame = False

            self.lock.release()

            task = Task(self.active_tab.run_animation_frame, scroll)
            active_tab.task_runner.schedule_task(task)

        self.lock.acquire(blocking=True)

        if self.needs_animation_frame and not self.animation_timer:
            self.animation_timer = threading.Timer(REFRESH_RATE_SEC, callback)
            self.animation_timer.start()

        self.lock.release()


    def schedule_load(self, url, body=None):
        """
        clears existing tasks in task queue of 
        active tab and schedules new task
        """

        self.active_tab.task_runner.clear_pending_tasks()
        task = Task(self.active_tab.load, url, body)
        self.active_tab.task_runner.schedule_task(task)


    def set_needs_animation_frame(self, tab):
        """
        sets the needs_animation_frame
        """

        self.lock.acquire(blocking=True)

        if tab == self.active_tab:
            self.needs_animation_frame = True

        self.lock.release()


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


    def set_needs_raster_and_draw(self):
        """
        updates needs_raster_and_draw flag
        """

        self.needs_raster_and_draw = True


    def raster_and_draw(self):
        """
        computes display list items for chrome 
        and tab and renders them to the screen
        """

        self.lock.acquire(blocking=True)
        if not self.needs_raster_and_draw: 
            self.lock.release()
            return

        self.measure.time('raster/draw')
        self.raster_chrome()
        self.raster_tab()
        self.draw()
        self.measure.stop('raster/draw')
        self.needs_raster_and_draw = False
        self.lock.release()


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

        self.lock.acquire(blocking=True)
        self.new_tab_internal(url)
        self.lock.release()


    def set_active_tab(self, tab):
        """
        set an active tab
        """

        self.active_tab = tab
        self.active_tab_scroll = 0
        self.active_tab_url = None
        self.needs_animation_frame = True
        self.animation_timer = None


    def new_tab_internal(self, url):
        """
        create a new tab
        """

        new_tab = Tab(self, HEIGHT - self.chrome.bottom)
        self.tabs.append(new_tab)
        self.set_active_tab(new_tab)
        self.schedule_load(url)

    
    def handle_quit(self):
        """
        destroy sdl window on pressing quit button
        """

        self.measure.finish()
        for tab in self.tabs:
            tab.task_runner.set_needs_quit()

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
            url = str(self.browser.active_tab.url) if self.browser.active_tab_url else ""
            cmds.append(DrawText(
                self.address_rect.left() + self.padding,
                self.address_rect.top(),
                url, self.font, "black"))

        return cmds


    def click(self, x, y):
        """
        handles clicks events on back, new tab and address boxes
        """

        # click event has occured on new tab button
        if self.newtab_rect.contains(x, y):
            self.browser.new_tab_internal(URL("https://browser.engineering/"))

        # click event has occured on back button
        elif self.back_rect.contains(x, y):
            task = Task(self.browser.active_tab.go_back)
            self.browser.active_tab.task_runner.schedule_task(task)

        # click event has occured on address bar
        elif self.address_rect.contains(x, y):
            self.focus = "Address Bar"
            self.address_bar = ""

        # click event has occured on one of the tabs
        else:
            for i, tab in enumerate(self.browser.tabs):
                if self.tab_rect(i).contains(x, y):
                    self.browser.set_active_tab(tab)
                    active_tab = self.browser.active_tab
                    task = Task(active_tab.set_needs_render)
                    active_tab.task_runner.schedule_task(task)
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
            self.browser.schedule_load(URL(self.address_bar))
            self.focus = None
            self.browser.focus = None


    def delete(self):
        """
        handles what needs to be done when delete key is pressed
        """

        if self.focus == "Address Bar":
            self.address_bar = self.address_bar[:-1]


class Tab:

    def __init__(self, browser, tab_height):

        # store history data
        self.history = []
        # set tab height
        self.tab_height = tab_height
        self.focus = None
        # tabs current url
        self.url = None
        self.scroll = 0
        self.scroll_changed_in_tab = False
        # used to determine if we need to run render
        self.needs_render = False
        self.needs_raf_callbacks = False
        self.browser = browser
        self.js = None
        self.loaded = False

        # init task queue for tab
        self.task_runner = TaskRunner(self)

        self.task_runner.start_thread()


    def run_animation_frame(self, scroll):
        """
        evaluate the raf invokation and finalize 
        on data to be drawn to screen
        """

        if not self.scroll_changed_in_tab:
            self.scroll = scroll

        self.browser.measure.time('script-runRAFHandlers')
        self.js.interp.evaljs("__runRAFHandlers()")
        self.browser.measure.stop('script-runRAFHandlers')

        self.render()

        # update scroll if it has changed
        scroll = None
        if self.scroll_changed_in_tab:
            scroll = self.scroll
        
        document_height = math.ceil(self.document.height + 2 * VSTEP)
        commit_data = CommitData(self.url, scroll, 
                                 document_height, self.display_list)

        self.display_list = None
        self.browser.commit(self, commit_data)
        self.scroll_changed_in_tab = False


    def clamp_scroll(self, scroll):
        """
        limit max scrolling height
        """

        height = math.ceil(self.document.height + 2 * VSTEP)
        maxscroll = height - self.tab_height

        return max(0, min(scroll, maxscroll))


    def scrolldown(self):
        """
        scroll down
        """

        max_y = max(self.document.height + 2 * VSTEP - self.tab_height, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)


    def scrollup(self):
        """
        scroll up
        """

        self.scroll = max(self.scroll - SCROLL_STEP, 0)


    def click(self, x, y):
        """
        executed when left mouse button clicked
        """

        self.render()

        self.focus = None

        # making position relative to web page
        y += self.scroll

        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x <= obj.x + obj.width
                and obj.y <= y <= obj.y + obj.height]
        
        if not objs: return
        elt = objs[-1].node

        if elt and self.js.dispatch_event("click", elt): return

        while elt:

            if isinstance(elt, Text):
                pass
            
            # if click on a link load the page associated with link
            elif elt.tag == "a" and "href" in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                self.load(url)
                return
            
            elif elt.tag == "input":
                elt.attributes["value"] = ""
                
                if self.focus:
                    self.focus.is_focused = False

                self.focus = elt
                elt.is_focused = True
                self.set_needs_render()
                return

            elif elt.tag == "button":
                while elt.parent:
                    if elt.tag == "form" and "action" in elt.attributes:
                        return self.submit_form(elt)
                    
                    elt = elt.parent

            elt = elt.parent


    def submit_form(self, elt):
        """
        extract form values from the form inputs
        """

        if self.js.dispatch_event("submit", elt): return

        inputs = [node for node in tree_to_list(elt, [])
                  if isinstance(node, Element) 
                  and node.tag == "input"
                  and "name" in node.attributes]
        
        body = ""

        for input in inputs:

            name = input.attributes["name"]
            value = input.attributes.get("value", "")

            name = urllib.parse.quote(name)
            value = urllib.parse.quote(value)

            body += "&" + name + "=" + value

        body = body[1:]

        url = self.url.resolve(elt.attributes["action"])
        self.load(url, body)


    def allowed_request(self, url):
        """
        checks whether an origin is allowed by the csp
        """

        return self.allowed_origins == None or url.origin() in self.allowed_origins


    def raster(self, canvas):
        """
        draw items using positions onto the canvas
        """

        # iterate and render items
        for cmd in self.display_list:
            cmd.execute(canvas)


    def set_needs_render(self):
        """
        update needs_render flag
        """

        self.needs_render = True
        self.browser.set_needs_animation_frame(self)


    def load(self, url, payload=None):
        """
        render servers content onto browser
        """

        self.loaded = False
        self.scroll = 0
        self.scroll_changed_in_tab = True
        self.task_runner.clear_pending_tasks()

        # download html file from the server
        headers, body = url.request(self.url, payload)

        # set tab url and add url to tab history
        self.url = url
        self.history.append(url)

        # used to specify csp, this is done to prevent loading js scripts 
        # if they originate from some different origin than one in csp
        self.allowed_origins = None
        if "content-security-policy" in headers:
            csp = headers["content-security-policy"].split()

            if len(csp) > 0 and csp[0] == "default-src":
                self.allowed_origins = csp[1:]

        # parse html file and create tree of nodes
        self.nodes = HTMLParser(body).parse()

        if self.js: self.js.discarded = True

        # instance of js interpreter, we use a 
        # single context to load multiple scripts
        self.js = JSContext(self)

        # get links of all scripts used by the webpage
        scripts = [node.attributes["src"] 
                   for node in tree_to_list(self.nodes, []) 
                   if isinstance(node, Element)
                   and node.tag == "script"
                   and "src" in node.attributes]
        
        # download js scripts used by the document
        for script in scripts:
            script_url = self.url.resolve(script)

            if not self.allowed_request(script_url):
                print("Blocked script", script, "due to CSP !")
                continue

            try:

                headers, body = script_url.request(url)

            except:
                continue

            task = Task(self.js.run, script_url, body)
            self.task_runner.schedule_task(task)

        # init css rules with a copy of default stylesheet
        self.rules = DEFAULT_STYLE_SHEET.copy()

        # get links of all stylesheets used by the webpage
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and node.attributes.get("rel") == "stylesheet"
                 and "href" in node.attributes]
        
        # iterate and download stylesheets and 
        # append rules to existing rules
        for link in links:
            style_url = self.url.resolve(link)

            try:
                headers, body = style_url.request(url)

            except:
                continue
            
            self.rules.extend(CSSParser(body).parse())

        self.set_needs_render()
        self.loaded = True


    def go_back(self):
        """
        gets previous url and loads tab
        """

        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)


    def render(self):
        """
        performs styling, layout, paint and draw phases
        """

        if not self.needs_render: return

        self.browser.measure.time('render')

        # apply styling info to all the nodes based on priority
        style(self.nodes, sorted(self.rules, key=cascade_priority))
        
        # init and build a tree of block layout objects
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []

        # compute objects based on layout type
        paint_tree(self.document, self.display_list)

        # reset needs_render flag
        self.needs_render = False

        clamped_scroll = self.clamp_scroll(self.scroll)

        if clamped_scroll != self.scroll:
            self.scroll_changed_in_tab = True

        self.scroll = clamped_scroll

        self.browser.measure.stop('render')


    def keypress(self, char):
        """
        when focused on an element add characters.
        useful for input boxes.
        """

        if self.focus:
            if self.js.dispatch_event("keydown", self.focus): return
            self.focus.attributes["value"] += char
            self.set_needs_render()


    def __repr__(self):
        return f"Tab(history={self.history})"


def mainloop(browser):
    """
    main eventloop for sdl window
    """

    # used to read and write events to/from event queue
    event = sdl2.SDL_Event()

    while True:
        
        # keep polling for pending events
        if sdl2.SDL_PollEvent(ctypes.byref(event)) != 0:

            # quit event
            if event.type == sdl2.SDL_QUIT:
                browser.handle_quit()
                sdl2.SDL_Quit()
                sys.exit()
                break

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

                elif event.key.keysym.sym == sdl2.SDLK_BACKSPACE:
                    browser.handle_delete()

            # text key event
            elif event.type == sdl2.SDL_TEXTINPUT:
                browser.handle_key(event.text.text.decode("utf8"))

        browser.raster_and_draw()
        browser.schedule_animation_frame()
