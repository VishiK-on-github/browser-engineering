from text import Text
from element import Element
from draw import DrawText, DrawRect
from helpers import get_font


HSTEP = 13
VSTEP = 18
WIDTH = 800
HEIGHT = 600
FONTS = {}


BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]


class BlockLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.display_list = []
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0


    def flush(self):
        """
        This method recomputes the y axis for text to prevent
        text from looking like its hanging from the top
        irrespective of size
        """

        if not self.line: return

        # calculate max ascent
        metrics = [font.metrics() for _, _, font, _ in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])

        # calculating baseline using max ascent
        baseline = self.cursor_y + 1.25 * max_ascent

        for rel_x, word, font, color in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font, color))

        # rest back to start
        self.cursor_x = 0
        self.line = []

        # moving up to accomodate words ascent
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent


    def recurse(self, node):
        """
        recursively building tree of html nodes
        """

        if isinstance(node, Text):
                
            for word in node.text.split():
                self.word(node, word)

        else:

            if node.tag == "br":
                self.flush()
            
            for child in node.children:
                self.recurse(child)


    def word(self, node, word):
        """
        this method estimates when to break onto next line
        by making use of font & screen width
        """

        weight = node.style["font-weight"]
        style = node.style["font-style"]

        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = get_font(size, weight, style)

        w = font.measure(word)
        
        # break and next line when we reach blocks width
        if self.cursor_x + w >= self.width:
            self.flush()

        color = node.style["color"]

        self.line.append((self.cursor_x, word, font, color))
        self.cursor_x += w + font.measure(" ")


    def layout_intermediate(self):
        """
        converts html nodes into block layout nodes
        """

        prev = None

        # we take children from html tree 
        # and create nodes for the layout tree
        for child in self.node.children:
            next = BlockLayout(child, self,  prev)
            self.children.append(next)
            prev = next


    def layout_mode(self):
        """
        determines if a node is block or inline
        """

        if isinstance(self.node, Text):
            return "inline"
        
        elif any([isinstance(child, Element) and \
                  child.tag in BLOCK_ELEMENTS for child in self.node.children]):
            return "block"
        
        elif self.node.children:
            return "inline"
        
        else:
            return "block"


    def layout(self):
        """
        building block layout nodes based on html nodes
        """

        # compute width
        self.x = self.parent.x
        self.width = self.parent.width

        # compute x, y
        # if sibling
        if self.previous:
            self.y = self.previous.y + self.previous.height

        # if no sibling
        else:
            self.y = self.parent.y
    
        mode = self.layout_mode()
        if mode == "block":
            prev = None

            for child in self.node.children:
                next = BlockLayout(child, self, prev)
                self.children.append(next)
                prev = next

        else:
            self.cursor_x = 0
            self.cursor_y = 0
            self.weight = "normal"
            self.style = "roman"
            self.size = 12

            self.line = []
            self.recurse(self.node)
            self.flush()

        # lay down nodes
        for child in self.children:
            child.layout()

        # calculate height
        if mode == "block":
            self.height = sum([child.height for child in self.children])
        else:
            self.height = self.cursor_y


    def paint(self):
        """
        creates DrawRect, DrawText nodes based on layout modes
        """

        cmds = []

        bg_color = self.node.style.get("background-color", "transparent")

        if bg_color != "transparent":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, bg_color)
            cmds.append(rect)

        if self.layout_mode() == "inline":
            for x, y, word, font, color in self.display_list:
                cmds.append(DrawText(x, y, word, font, color))

        return cmds
