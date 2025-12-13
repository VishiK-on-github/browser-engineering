import tkinter
import tkinter.font

from text import Text
from element import Element
from draw import DrawText, DrawRect

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
        self.x = None
        self.y = None
        self.width = None
        self.height = None


    def flush(self):
        """
        This method recomputes the y axis for text to prevent
        text from looking like its hanging from the top
        irrespective of size
        """

        if not self.line: return

        # calculate max ascent
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])

        # calculating baseline using max ascent
        baseline = self.cursor_y + 1.25 * max_ascent

        for rel_x, word, font in self.line:
            x = self.x + rel_x
            y = self.y + baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))

        # moving up to accomodate words ascent
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

        # rest back to start
        self.cursor_x = 0
        self.line = []


    def open_tag(self, tag):
        """
        setting nodes attributes based on tags
        """

        if tag == "i":
            self.style = "italic"

        elif tag == "b":
            self.weight = "bold"

        elif tag == "small":
            self.size -= 2

        elif tag == "big":
            self.size += 4

        elif tag == "br":
            self.flush()


    def close_tag(self, tag):
        """
        resetting nodes attributes based on tags
        """

        if tag == "i":
            self.style = "roman"
        
        elif tag == "b":
            self.weight = "normal"

        elif tag == "small":
            self.size += 2

        elif tag == "big":
            self.size -= 4

        elif tag == "p":
            self.flush()
            self.cursor_y += VSTEP


    def recurse(self, tree):
        """
        recursively building tree of html nodes
        """

        if isinstance(tree, Text):
                
            for word in tree.text.split():

                self.word(word)

        else:

            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)


    def word(self, word):
        """
        this method estimates when to break onto next line
        by making use of font & screen width
        """

        font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)
        
        # break and next line when we reach blocks width
        if self.cursor_x + w >= self.width:
            self.flush()

        self.line.append((self.cursor_x, word, font))
        self.cursor_x += w + font.measure(" ")


    def layout_intermediate(self):
        """
        this method converts html nodes into block layout nodes
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
        method to determine if a node is block or inline
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
        cmds = []

        if self.layout_mode() == "inline":
            for x, y, word, font in self.display_list:
                cmds.append(DrawText(x, y, word, font))

        if isinstance(self.node, Element) and self.node.tag == "pre":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, "blue")
            cmds.append(rect)

        return cmds


def get_font(size, weight, style):
    """
    caching fonts to reuse instead of creating new objects
    cheaper when we have a lot of text
    """

    key = (size, weight, style)

    if key not in FONTS:
        font = tkinter.font.Font(
            size=size,
            weight=weight,
            slant=style
        )

        label = tkinter.Label(font=font)

        FONTS[key] = (font, label)

    return FONTS[key][0]
