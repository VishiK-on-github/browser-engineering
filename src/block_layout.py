from text import Text
from element import Element
from draw import DrawText, DrawRect, Rect
from helpers import get_font
from text_layout import TextLayout
from line_layout import LineLayout


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

        # position info
        self.x = 0
        self.y = 0
        self.width = 0
        self.height = 0


    def recurse(self, node):
        """
        recursively split nodes based on html node type
        """

        if isinstance(node, Text):
                
            for word in node.text.split():
                self.word(node, word)

        else:

            if node.tag == "br":
                self.new_line()
            
            for child in node.children:
                self.recurse(child)


    def word(self, node, word):
        """
        estimates when to break onto next line
        by making use of font & screen width
        """

        weight = node.style["font-weight"]
        style = node.style["font-style"]

        if style == "normal": style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        font = get_font(size, weight, style)

        w = font.measure(word)

        # if cursor goes beyond a limit break 
        # content into a new line
        if self.cursor_x + w > self.width:
            self.new_line()
        
        line = self.children[-1]
        prev_word = line.children[-1] if line.children else None
        text = TextLayout(node, word, line, prev_word)
        line.children.append(text)
        self.cursor_x += w + font.measure(" ")


    def new_line(self):
        """
        creates a new LineLayout object when 
        we exceed screen width bounds
        """

        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)


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
        recursively building block layout nodes based on html nodes
        """

        # compute width
        self.x = self.parent.x
        self.width = self.parent.width

        # compute x, y if sibling
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
            self.new_line()
            self.recurse(self.node)

        # lay down nodes
        for child in self.children:
            child.layout()

        # calculate height
        self.height = sum([child.height for child in self.children])
    

    def self_rect(self):
        return Rect(self.x, self.y, self.x + self.width, self.y + self.height)


    def paint(self):
        """
        creates DrawRect, DrawText nodes based on layout modes
        """

        cmds = []

        bg_color = self.node.style.get("background-color", "transparent")

        if bg_color != "transparent":
            rect = DrawRect(self.self_rect(), bg_color)
            cmds.append(rect)

        return cmds


    def __repr__(self):
        return f"BlockLayout[{self.layout_mode()}](x={self.x}, y={self.y}, width={self.width}, height={self.height})"
