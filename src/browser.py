import tkinter

from client import Client

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

    
    def layout(self, text):
        """
        compute position of char in content
        """
        
        display_list = []
        cursor_x, cursor_y = HSTEP, VSTEP

        for c in text:

            if cursor_x >= WIDTH - HSTEP:
                cursor_y += VSTEP
                cursor_x = HSTEP

            display_list.append((cursor_x, cursor_y, c))
            cursor_x += HSTEP

        return display_list
    

    def draw(self):
        """
        draw chars using chars & positions onto the canvas
        """

        self.canvas.delete("all")
        for x, y, c in self.display_list:
            # dont draw below view
            if y > self.scroll + HEIGHT: continue
            # dont draw above
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c)


    def scrolldown(self, e):

        self.scroll += SCROLL_STEP
        self.draw()


    def scrollup(self, e):

        self.scroll -= SCROLL_STEP
        self.draw()


    def load(self):
        """
        render servers content onto browser
        """

        body = self.client.request()
        text = self.client.lex(body)
        self.display_list = self.layout(text)
        self.draw()