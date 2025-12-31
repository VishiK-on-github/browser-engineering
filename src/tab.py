import urllib
from document_layout import DocumentLayout
from html_parser import HTMLParser
from css_parser import CSSParser, style, cascade_priority
from element import Element
from text import Text
from js_context import JSContext
from helpers import paint_tree, tree_to_list
from client import URL


WIDTH = 800
HEIGHT = 600
HSTEP = 13
VSTEP = 18
SCROLL_STEP = 50
DEFAULT_STYLE_SHEET = CSSParser(open("./browser.css").read()).parse()


class Tab:

    def __init__(self, tab_height):
        self.url = None

        # set tab height
        self.tab_height = tab_height

        # store history data
        self.history = []

        self.focus = None


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

        if self.focus:
            self.focus.is_focused = True

        self.focus = None

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
                if self.js.dispatch_event("click", elt): return
                url = self.url.resolve(elt.attributes["href"])
                return self.load(url)
            
            elif elt.tag == "input":
                if self.js.dispatch_event("click", elt): return
                elt.attributes["value"] = ""
                self.focus = elt
                elt.is_focused = True
                return self.render()

            elif elt.tag == "button":
                if self.js.dispatch_event("click", elt): return
                while elt:
                    if elt.tag == "form" and "action" in elt.attributes:
                        return self.submit_form(elt)
                    
                    elt = elt.parent

            elt = elt.parent

        self.render()


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


    def load(self, url, payload=None):
        """
        render servers content onto browser
        """

        # download html file from the server
        self.scroll = 0
        self.url = url
        self.history.append(url)
        headers, body = url.request(self.url, payload)

        # parse html file and create tree of nodes
        self.nodes = HTMLParser(body).parse()

        # used to specify csp, this is done to prevent loading js scripts 
        # if they originate from some different origin than one in csp
        self.allowed_origins = None
        if "content-security-policy" in headers:
            csp = headers["content-security-policy"].split()

            if len(csp) > 0 and csp[0] == "default-src":
                self.allowed_origins = []
                
                for origin in csp[1:]:
                    self.allowed_origins.append(URL(origin).origin())

        # get links of all scripts used by the webpage
        scripts = [node.attributes["src"] 
                   for node in tree_to_list(self.nodes, []) 
                   if isinstance(node, Element)
                   and node.tag == "script"
                   and "src" in node.attributes]
        
        # init css rules with a copy of default stylesheet
        self.rules = DEFAULT_STYLE_SHEET.copy()

        # get links of all stylesheets used by the webpage
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and node.attributes.get("rel") == "stylesheet"
                 and "href" in node.attributes]

        # instance of js interpreter, we use a 
        # single context to load multiple scripts
        self.js = JSContext(self)
        
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

            self.js.run(script, body)
        
        # iterate and download stylesheets and 
        # append rules to existing rules
        for link in links:
            style_url = self.url.resolve(link)

            try:
                headers, body = style_url.request(url)

            except:
                continue
            
            self.rules.extend(CSSParser(body).parse())

        self.render()


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

        # apply styling info to all the nodes based on priority
        style(self.nodes, sorted(self.rules, key=cascade_priority))
        
        # init and build a tree of block layout objects
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []

        # compute objects based on layout type
        paint_tree(self.document, self.display_list)


    def keypress(self, char):
        """
        when focused on an element add characters.
        useful for input boxes.
        """

        if self.focus:
            if self.js.dispatch_event("keydown", self.focus): return
            self.focus.attributes["value"] += char
            self.render()


    def __repr__(self):
        return f"Tab(history={self.history})"
 