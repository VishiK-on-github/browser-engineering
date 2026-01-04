from helpers import get_font, linespace
from draw import DrawText
from typing import List


class TextLayout:
    def __init__(self, node, word, parent, previous) -> None:
        self.node = node
        self.word = word
        self.parent = parent
        self.previous = previous
        self.children = []

        self.x = 0
        self.y = 0
        self.height = 0
        self.width = 0

    
    def layout(self):
        """
        compute where text must be placed before adding to layout tree
        """

        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        size = int(float(self.node.style["font-size"][:-2]) * 0.75)
        self.font = get_font(size, weight, style)

        self.width = self.font.measureText(self.word)

        if self.previous:
            space = self.previous.font.measureText(" ")
            self.x = self.previous.x + space + self.previous.width

        else:
            self.x = self.parent.x

        self.height = linespace(self.font) + 20

    
    def paint(self) -> List[DrawText]:
        """
        compute and return text be layed out in layout tree
        """

        cmds = []
        color = self.node.style["color"]
        cmds.append(DrawText(self.x, self.y, self.word, self.font, color))

        return cmds


    def should_paint(self):
        return True
    

    def paint_effects(self, cmds):

        return cmds


    def __repr__(self):
        return f"TextLayout(x={self.x}, y={self.y}, width={self.width}, \
            height={self.height}, word={self.word})"