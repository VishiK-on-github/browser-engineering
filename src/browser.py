import tkinter

from client import Client
from document_layout import DocumentLayout, paint_tree
from parser import HTMLParser, print_tree

WIDTH = 800
HEIGHT = 600
HSTEP = 13
VSTEP = 18
SCROLL_STEP = 50

class Browser:

    def __init__(self, url):
        # makes window
        self.window = tkinter.Tk()

        # make canvas
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT)
        # make canvas fit in window
        self.canvas.pack()

        # client which makes request
        self.client = Client(url)

        self.scroll = 0

        # binding keys to scroll actions
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)


    def scrolldown(self, e):

        self.scroll += SCROLL_STEP
        self.draw()


    def scrollup(self, e):

        self.scroll -= SCROLL_STEP
        self.draw()
    

    def draw(self):
        """
        draw chars using chars & positions onto the canvas
        """

        self.canvas.delete("all")
        for cmd in self.display_list:
            # dont draw below view
            if cmd.top > self.scroll + HEIGHT: continue
            # dont draw above
            if cmd.bottom + VSTEP < self.scroll: continue
            cmd.execute(self.scroll, self.canvas)


    def load(self):
        """
        render servers content onto browser
        """

        body = self.client.request()
        self.nodes = HTMLParser(body).parse()
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)
        self.draw()
