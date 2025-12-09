import tkinter

# from client import Client, lex
from client import Client
from layout import Layout
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
        for x, y, c, f in self.display_list:
            # dont draw below view
            if y > self.scroll + HEIGHT: continue
            # dont draw above
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c, font=f, anchor="nw")


    def load(self):
        """
        render servers content onto browser
        """

        body = self.client.request()
        self.nodes = HTMLParser(body).parse()
        self.display_list = Layout(self.nodes).display_list
        self.draw()