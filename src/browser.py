import tkinter
from client import Client
from document_layout import DocumentLayout
from html_parser import HTMLParser
from css_parser import CSSParser, style, cascade_priority
from element import Element
from helpers import paint_tree, tree_to_list


WIDTH = 800
HEIGHT = 600
HSTEP = 13
VSTEP = 18
SCROLL_STEP = 50
DEFAULT_STYLE_SHEET = CSSParser(open("./testing_files/browser.css").read()).parse()


class Browser:

    def __init__(self, url: str):
        self.window = tkinter.Tk()

        # make canvas
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT,
            bg="white")

        # make canvas fit in window
        self.canvas.pack()

        # client which makes request
        self.client = Client(url)

        # init position of scroll bar
        self.scroll = 0

        # binding keys to scroll actions
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)

        # init list of items to be drawn to screen
        self.display_list = []


    def scrolldown(self, e):
        """
        scroll down
        """

        self.scroll += SCROLL_STEP
        self.draw()


    def scrollup(self, e):
        """
        scroll up
        """

        self.scroll -= SCROLL_STEP
        self.draw()
    

    def draw(self):
        """
        draw chars using chars & positions onto the canvas
        """

        # cleanup all items on canvas
        self.canvas.delete("all")

        # iterate and render items
        for cmd in self.display_list:
            # dont draw below view
            if cmd.top > self.scroll + HEIGHT: continue

            # dont draw above
            if cmd.bottom + VSTEP < self.scroll: continue
            cmd.execute(self.scroll, self.canvas)


    def load(self, url: str):
        """
        render servers content onto browser
        """

        # download html file from the server
        body = self.client.request()

        # parse html file and create tree of nodes
        self.nodes = HTMLParser(body).parse()

        # init css rules with a copy of default stylesheet
        rules = DEFAULT_STYLE_SHEET.copy()

        # get links of all stylesheets which the webpage uses
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and node.attributes.get("rel") == "stylesheet"
                 and "href" in node.attributes]
        
        # iterate and download stylesheets and 
        # append rules to existing rules
        for link in links:
            style_url = self.client.resolve(link)

            try:
                body = style_url.request()

            except:
                continue
            
            rules.extend(CSSParser(body).parse())

        # apply styling info to all the nodes based on priority
        style(self.nodes, sorted(rules, key=cascade_priority))

        # init and build a tree of block layout objects
        self.document = DocumentLayout(self.nodes)
        self.document.layout()

        self.display_list = []

        # compute objects based on layout type
        paint_tree(self.document, self.display_list)

        # draw computed items onto tkinter canvas
        self.draw()
