from helpers import get_font
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

        if style == "normal": style = "roman"

        size = int(float(self.node.style["font-size"][:-2]) * 0.75)

        self.font = get_font(size, weight, style)

        self.width = self.font.measure(self.word)

        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width

        else:
            self.x = self.parent.x

        self.height = self.font.metrics("linespace")

    
    def paint(self) -> List[DrawText]:
        """
        compute and return text be layed out in layout tree
        """

        color = self.node.style["color"]
        return [DrawText(self.x, self.y, self.word, self.font, color)]


    def __repr__(self):
        return f"TextLayout(x={self.x}, y={self.y}, width={self.width}, height={self.height}, word={self.word})"