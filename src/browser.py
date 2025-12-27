import tkinter
from tab import Tab
from helpers import get_font
from draw import Rect, DrawText, DrawOutline, DrawLine, DrawRect
from client import URL


WIDTH = 800
HEIGHT = 600
HSTEP = 13
VSTEP = 18
SCROLL_STEP = 50


class Browser:
    def __init__(self) -> None:

        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
            bg="white")

        # make canvas fit in window
        self.canvas.pack()

        # init position of scroll bar
        self.scroll = 0

        # binding keys to scroll actions
        self.window.bind("<Down>", self.handle_down)
        self.window.bind("<Up>", self.handle_up)

        # binding keys to click buttons
        self.window.bind("<Button-1>", self.handle_click)

        # binding keys for typing in address bar
        self.window.bind("<Key>", self.handle_key)

        # binding keys on clicking enter button
        self.window.bind("<Return>", self.handle_enter)

        # binding keys on clicking delete button
        self.window.bind("<BackSpace>", self.handle_delete)

        self.tabs = []
        self.active_tab: Tab = None
        self.chrome = Chrome(self)


    def handle_down(self, e):
        """
        scroll down
        """

        self.active_tab.scrolldown()
        self.draw()


    def handle_up(self, e):
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
            self.chrome.click(e.x, e.y)

        else:
            # set focus back since we are on the browser content
            self.focus = "content"
            self.chrome.blur()
            tab_y = e.y - self.chrome.bottom
            self.active_tab.click(e.x, tab_y)

        self.draw()


    def handle_key(self, e):
        """
        executed when a key is pressed
        """

        if len(e.char) == 0: return

        # ignore key char if it falls beyond certain hex
        if not (0x20 <= ord(e.char) < 0x7f): return

        if self.chrome.keypress(e.char):
            self.draw()

        elif self.focus == "content":
            self.chrome.keypress(e.char)
            self.draw()


    def handle_enter(self, e):
        """
        executed when enter key is pressed
        """

        self.chrome.enter()
        self.draw()


    def handle_delete(self, e):
        """
        executed when delete key is pressed
        """

        self.chrome.delete()
        self.draw()


    def draw(self):
        """
        draw items onto canvas
        """

        self.canvas.delete("all")
        self.active_tab.draw(self.canvas, self.chrome.bottom)

        for cmd in self.chrome.paint():
            cmd.execute(0, self.canvas)

    
    def new_tab(self, url):
        """
        spawns new tab
        """

        new_tab = Tab(HEIGHT - self.chrome.bottom)
        new_tab.load(url)
        self.active_tab = new_tab
        self.tabs.append(new_tab)
        self.draw()


class Chrome:
    def __init__(self, browser: Browser) -> None:
        self.browser = browser
        self.focus = None
        self.address_bar = ""

        self.font = get_font(20, "normal", "roman")
        self.font_height = self.font.metrics("linespace")

        self.padding = 5
        self.tabbar_top = 0
        self.tabbar_bottom = self.font_height + 2 * self.padding

        # spacing, sizing for new tab button
        plus_width = self.font.measure("+") + 2 * self.padding
        self.newtab_rect = Rect(self.padding, self.padding, 
                                self.padding + plus_width, 
                                self.padding + self.font_height)
        
        # spacing, sizing for url bar
        self.urlbar_top = self.tabbar_bottom
        self.urlbar_bottom = self.urlbar_top + \
            self.font_height + 2 * self.padding

        # spacing, sizing for back button
        back_width = self.font.measure("<") + 2 * self.padding
        self.back_rect = Rect(self.padding, self.urlbar_top + self.padding, 
                              self.padding + back_width,
                              self.urlbar_bottom - self.padding)
        
        # spacing, sizing for address bar
        self.address_rect = Rect(
            self.back_rect.top + self.padding,
            self.urlbar_top + self.padding,
            WIDTH - self.padding,
            self.urlbar_bottom - self.padding)
        
        self.bottom = self.urlbar_bottom
        
    
    def tab_rect(self, i):
        """
        computing tab text sizes and creating a Rect object
        """

        tab_start = self.newtab_rect.right + self.padding
        tab_width = self.font.measure("Tab X") + 2 * self.padding

        return Rect(
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

        cmds.append(DrawRect(Rect(0, 0, WIDTH, self.bottom), "white"))
        cmds.append(DrawLine(0, self.bottom, WIDTH, self.bottom, "black", 1))

        # TODO
        cmds.append(DrawOutline(self.newtab_rect, "black", 1))
        cmds.append(DrawText(self.newtab_rect.left + self.padding,
                             self.newtab_rect.top, "+", self.font, "black"))
        
        # determine items to be rendered in the tab bar
        for i, tab in enumerate(self.browser.tabs):

            bounds = self.tab_rect(i)
            cmds.append(DrawLine(bounds.left, 0, bounds.left, bounds.bottom, "black", 1))
            cmds.append(DrawLine(bounds.right, 0, bounds.right, bounds.bottom, "black", 1))
            cmds.append(DrawText(
                bounds.left + self.padding, bounds.top + self.padding,
                f"Tab {i}", self.font, "black"))
            
            # if tab is active tab get rid of the bottom line
            if tab == self.browser.active_tab:

                cmds.append(DrawLine(0, bounds.bottom, bounds.left, bounds.bottom, "black", 1))
                cmds.append(DrawLine(bounds.right, bounds.bottom, WIDTH, bounds.bottom, "black", 1))

        # back navigation button
        cmds.append(DrawOutline(self.address_rect, "black", 1))
        cmds.append(DrawText(self.back_rect.left + self.padding,
                             self.back_rect.top, "<", self.font, "black"))
        
        cmds.append(DrawOutline(self.address_rect, "black", 1))
        
        # executes when we have clicked on the address bar
        if self.focus == "Address Bar":
            cmds.append(DrawText(
                self.address_rect.left + self.padding,
                self.address_rect.top,
                self.address_bar, self.font, "black"))
            
            w = self.font.measure(self.address_bar)
            cmds.append(DrawLine(
                self.address_rect.left + self.padding + w,
                self.address_rect.top,
                self.address_rect.left + self.padding + w,
                self.address_rect.bottom, "red", 1))

        # otherwise
        else:
            url = str(self.browser.active_tab.url)
            cmds.append(DrawText(
                self.address_rect.left + self.padding,
                self.address_rect.top,
                url, self.font, "black"))

        return cmds


    def click(self, x, y):
        """
        handles clicks events on back, new tab and address boxes
        """

        self.focus = None

        # click event has occured on new tab button
        if self.newtab_rect.contains_point(x, y):
            self.browser.new_tab(URL("https://browser.engineering/"))

        # click event has occured on back button
        elif self.back_rect.contains_point(x, y):
            self.browser.active_tab.go_back()

        # click event has occured on address bar
        elif self.address_rect.contains_point(x, y):
            self.focus = "Address Bar"
            self.address_bar = ""

        # click event has occured on one of the tabs
        else:
            for i, tab in enumerate(self.browser.tabs):
                if self.tab_rect(i).contains_point(x, y):
                    self.browser.active_tab = tab
                    break


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

    
    def delete(self):
        """
        handles what needs to be done when delete key is pressed
        """

        if self.focus == "Address Bar":
            self.address_bar = self.address_bar[:-1]