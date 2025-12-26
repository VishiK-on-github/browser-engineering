import tkinter
from client import URL
from document_layout import DocumentLayout
from html_parser import HTMLParser
from css_parser import CSSParser, style, cascade_priority
from element import Element
from text import Text
from helpers import paint_tree, tree_to_list


WIDTH = 800
HEIGHT = 600
HSTEP = 13
VSTEP = 18
SCROLL_STEP = 50
DEFAULT_STYLE_SHEET = CSSParser(open("./testing_files/browser.css").read()).parse()


class Tab:

    def __init__(self, tab_height):
        self.url = None

        # set tab height
        self.tab_height = tab_height

        # store history data
        self.history = []


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

        # making position relative to web page
        y += self.scroll

        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x <= obj.x + obj.width
                and obj.y <= y <= obj.y + obj.height]
        
        if not objs: return
        elt = objs[-1].node

        while elt:
            if isinstance(elt, Text):
                pass
                
            elif elt.tag == "a" and "href" in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)

            elt = elt.parent


    def draw(self, canvas, offset):
        """
        draw chars using chars & positions onto the canvas
        """

        # iterate and render items
        for cmd in self.display_list:

            # dont draw below view
            if cmd.rect.top > self.scroll + self.tab_height:
                continue

            # dont draw above
            if cmd.rect.bottom < self.scroll: continue
            cmd.execute(self.scroll - offset, canvas)


    def load(self, url):
        """
        render servers content onto browser
        """

        # download html file from the server
        body = url.request()
        self.scroll = 0
        self.url = url
        self.history.append(url)

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
            style_url = self.url.resolve(link)

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

    
    def go_back(self):
        """
        gets previous url and loads tab
        """

        if len(self.history) > 1:
            self.history.pop()
            back = self.history.pop()
            self.load(back)


    def __repr__(self):
        return f"Tab(history={self.history})"
 