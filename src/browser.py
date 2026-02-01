import ctypes
import sys
import threading
import urllib
import math
from typing import List

import sdl2
import skia
import OpenGL.GL

from helpers import get_font, linespace, paint_tree, tree_to_list, add_parent_pointers
from draw import DrawText, DrawLine
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
from compositing import CompositedLayer, PaintCommand, DrawCompositedLayer, absolute_bounds_for_obj, DrawOutline, local_to_absolute
from blend import Blend


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
            sdl2.SDL_CreateWindow(b"Browser", 
                                  sdl2.SDL_WINDOWPOS_CENTERED, 
                                  sdl2.SDL_WINDOWPOS_CENTERED, 
                                  WIDTH, HEIGHT, 
                                  sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_OPENGL)

        # setting up OpenGL attributes in SDL
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_MAJOR_VERSION, 3)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_MINOR_VERSION, 2)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, True)
        sdl2.SDL_GL_SetAttribute(sdl2.SDL_GL_CONTEXT_PROFILE_MASK,
                                 sdl2.SDL_GL_CONTEXT_PROFILE_CORE)
        
        """
        Initializes the GPU rendering pipeline. 

        Creates an SDL OpenGL context, binds it to a Skia DirectContext for hardware 
        acceleration, and establishes the root rendering surface mapped to the 
        window's default framebuffer.
        """

        # context is created for external processors (GPU) to keep track of state
        self.gl_context = sdl2.SDL_GL_CreateContext(self.sdl_window)

        print(f"OpenGL initialized: vendor={OpenGL.GL.glGetString(OpenGL.GL.GL_VENDOR)}, renderer={OpenGL.GL.glGetString(OpenGL.GL.GL_RENDERER)}")

        # translate commands between skia and OpenGL, GPU understands OpenGL
        self.skia_context = skia.GrDirectContext.MakeGL()

        # create a skia root surface
        self.root_surface = skia.Surface.MakeFromBackendRenderTarget(
            self.skia_context,
            skia.GrBackendRenderTarget(WIDTH, HEIGHT, 0, 0,
                skia.GrGLFramebufferInfo(0, OpenGL.GL.GL_RGBA8)),
                skia.kBottomLeft_GrSurfaceOrigin,
                skia.kRGBA_8888_ColorType,
                skia.ColorSpace.MakeSRGB())
        
        assert self.root_surface is not None
        
        # creates a surface for common components, address bar, tabs, back button
        self.chrome_surface = skia.Surface.MakeRenderTarget(
                self.skia_context, skia.Budgeted.kNo,
                skia.ImageInfo.MakeN32Premul(WIDTH, math.ceil(self.chrome.bottom)))
        
        assert self.chrome_surface is not None

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
        self.composited_layers = []
        self.draw_list = []
        self.composited_updates = {}
        self.needs_composite = False
        self.needs_raster = False
        self.needs_draw = False


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

            self.animation_timer = None
            self.composited_updates = data.composited_updates

            if self.composited_updates == None:
                self.composited_updates = {}
                self.set_needs_composite()

            else:
                self.set_needs_draw()

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
        self.set_needs_draw()
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

            self.set_needs_raster()

        else:
            # check and set focus to website content
            if self.focus != "content":
                self.set_needs_raster()

            self.focus = "content"
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
            self.set_needs_raster()

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
            self.set_needs_raster()

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
        
        for composited_layer in self.composited_layers:
            composited_layer.raster()


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


    def get_latest(self, effect):
        """
        get latest version of an effect
        """

        node = effect.node

        if node not in self.composited_updates:
            return effect
        
        if not isinstance(effect, Blend):
            return effect
        
        return self.composited_updates[node]


    def set_needs_raster(self):
        """
        setting flags when browser needs to raster
        """

        self.needs_raster = True
        self.needs_draw = True


    def set_needs_composite(self):
        """
        setting flags when browser needs to composite
        """

        self.needs_composite = True
        self.needs_raster = True
        self.needs_draw = True


    def set_needs_draw(self):
        """
        setting flags when browser needs to draw
        """

        self.needs_draw = True


    def composite_raster_and_draw(self):
        """
        computes display list items for chrome 
        and tab and renders them to the screen
        """

        self.lock.acquire(blocking=True)
        if not self.needs_composite \
            and not self.needs_raster \
            and not self.needs_draw:
            self.lock.release()
            return

        self.measure.time('composite_raster_and_draw')

        if self.needs_composite:
            self.measure.time('composite')
            self.composite()
            self.measure.stop('composite')

        if self.needs_raster:
            self.measure.time('raster')
            self.raster_chrome()
            self.raster_tab()
            self.measure.stop('raster')

        if self.needs_draw:
            self.measure.time('draw')
            self.paint_draw_list()
            self.draw()
            self.measure.stop('draw')

        self.measure.stop('composite_raster_and_draw')
        self.needs_composite = False
        self.needs_raster = False
        self.needs_draw = False
        self.lock.release()


    def draw(self):
        """
        draw pixels on the SDL surface
        """

        canvas = self.root_surface.getCanvas()
        canvas.clear(skia.ColorWHITE)

        canvas.save()

        canvas.translate(0, self.chrome.bottom - self.active_tab_scroll)

        # draw items to the root surface
        for item in self.draw_list:
            item.execute(canvas)

        canvas.restore()

        chrome_rect = skia.Rect.MakeLTRB(0, 0, WIDTH, self.chrome.bottom)
        canvas.save()

        # restrict common components drawing to only chrome_rects dimensions
        canvas.clipRect(chrome_rect)
        self.chrome_surface.draw(canvas, 0, 0)

        # undo clipRect
        canvas.restore()

        # flushing the skia surface
        self.root_surface.flushAndSubmit()

        # activate the latest frame buffer
        sdl2.SDL_GL_SwapWindow(self.sdl_window)


    def paint_draw_list(self):
        """
        using list of composited layers to 
        create hierarchy of visual effects
        """

        new_effects = {}
        self.draw_list = []

        # iterate over all the composited layers
        for composited_layer in self.composited_layers:
            current_effect = DrawCompositedLayer(composited_layer)

            # if the composited layer has no items skip
            if not composited_layer.display_items: continue

            parent = composited_layer.display_items[0].parent

            while parent:
                
                # get the latest visual effect associated with the parent
                new_parent = self.get_latest(parent)

                if new_parent in new_effects:
                    new_effects[new_parent].children.append(current_effect)
                    break
                
                else:
                    current_effect = new_parent.clone(current_effect)
                    new_effects[new_parent] = current_effect
                    parent = new_parent.parent

            if not parent:
                self.draw_list.append(current_effect)


    def clear_data(self):
        """
        discard & reset data
        """

        self.active_tab_scroll = 0
        self.active_tab_url = None
        self.display_list = []
        self.composited_layers = []
        self.composited_updates = {}


    def composite(self):
        """
        This is used to determine how to group 
        & cache paint commands onto a composited layer.
        This would help us minimize raster commands since 
        components where layout doesn't change can be combined into one layer
        """

        # add links from child node to parent. 
        # I think this is used to determine if 
        # composited layers have a common ancestor
        add_parent_pointers(self.active_tab_display_list)
        self.composited_layers: List[CompositedLayer] = []
        all_commands = []

        # get all the paint commands in the display list
        for cmd in self.active_tab_display_list:
            all_commands = tree_to_list(cmd, all_commands)
        
        non_composited_commands = \
            [cmd for cmd in all_commands 
             if isinstance(cmd, PaintCommand) or not cmd.needs_compositing
             if not cmd.parent or cmd.parent.needs_compositing]

        for cmd in non_composited_commands:
            did_break = False

            # top to bottom checking
            for layer in reversed(self.composited_layers):

                # if a composited layer is compatible we 
                # merge paint commands with it
                if layer.can_merge(cmd):
                    layer.add(cmd)
                    did_break = True
                    break
                
                # if it cannot be merged but layers bounds intersect 
                # with the paint commands rect we create a new layer and dont check any further
                elif skia.Rect.Intersects(layer.composited_bounds(), 
                                          local_to_absolute(cmd, cmd.rect)):
                    self.composited_layers.append(CompositedLayer(self.skia_context, cmd))
                    did_break = True
                    break
            
            # if there are no merges then we create a new top layer compos
            if not did_break:
                layer = CompositedLayer(self.skia_context, cmd)
                self.composited_layers.append(layer)

        # recompute the active tabs height due to composited layers
        self.active_tab_height = 0
        for layer in self.composited_layers:
            self.active_tab_height = \
                max(self.active_tab_height, layer.absolute_bounds().bottom())


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
        self.clear_data()
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

        sdl2.SDL_GL_DeleteContext(self.gl_context)
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
        
        self.needs_style = False
        self.needs_layout = False
        self.needs_paint = False

        self.composited_updates = []

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

        for node in tree_to_list(self.nodes, []):
            for (property_name, animation) in node.animations.items():
                value = animation.animate()

                # if we have a new value for the property update 
                # the nodes property with new value
                if value:
                    node.style[property_name] = value
                    self.composited_updates.append(node)
                    self.set_needs_paint()

        needs_composite = self.needs_style or self.needs_layout

        self.render()

        # update scroll if it has changed
        scroll = None
        if self.scroll_changed_in_tab:
            scroll = self.scroll

        composited_updates = None

        if not needs_composite:
            composited_updates = {}

            for node in self.composited_updates:
                composited_updates[node] = node.blend_op

        self.composited_updates = []
        
        document_height = math.ceil(self.document.height + 2 * VSTEP)
        commit_data = CommitData(self.url, scroll, 
                                 document_height, self.display_list,
                                 composited_updates)

        self.display_list = None
        self.scroll_changed_in_tab = False

        self.browser.commit(self, commit_data)


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

        loc_rect = skia.Rect.MakeXYWH(x, y, 1, 1)
        objs = [obj for obj in tree_to_list(self.document, [])
                if absolute_bounds_for_obj(obj).intersects(
                    loc_rect)]
        
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

        self.needs_style = True
        self.browser.set_needs_animation_frame(self)


    def set_needs_layout(self):
        """
        setting flags when browser needs to update layout
        """

        self.needs_layout = True
        self.browser.set_needs_animation_frame(self)


    def set_needs_paint(self):
        """
        setting flags when browser needs to paint
        """

        self.needs_paint = True
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
        self.browser.measure.time('fetch_page')
        headers, body = url.request(self.url, payload)
        self.browser.measure.stop('fetch_page')

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

        self.browser.measure.time('render')

        if self.needs_style:
            style(self.nodes, sorted(self.rules, key=cascade_priority), self)
            self.needs_layout = True
            self.needs_style = False

        if self.needs_layout:
            self.document = DocumentLayout(self.nodes)
            self.document.layout()
            self.needs_paint = True
            self.needs_layout = False

        if self.needs_paint:
            self.display_list = []
            paint_tree(self.document, self.display_list)
            self.needs_paint = False

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

        browser.composite_raster_and_draw()
        browser.schedule_animation_frame()
