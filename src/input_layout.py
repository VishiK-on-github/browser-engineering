from draw import Rect, DrawRect, DrawText, DrawLine
from text import Text
from helpers import get_font


INPUT_WIDTH_PX = 200


class InputLayout:
    def __init__(self, node, parent, previous) -> None:
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []
        self.font = None

        # sizing, position
        self.width = 0
        self.height = 0
        self.x = 0
        self.y = 0


    def layout(self):
        """
        determining how to add InputLayour object to the layout tree
        """

        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]

        if style == "normal": style = "roman"

        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = get_font(size, weight, style)

        self.width = INPUT_WIDTH_PX

        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + space + self.previous.width
        else:
            self.x = self.parent.x

        self.height = self.font.metrics("linespace")


    def self_rect(self):
        return Rect(self.x, self.y, 
                    self.x + self.width, 
                    self.y + self.height)
    

    def should_paint(self):
        return True


    def paint(self):
        """
        determine which types need to be drawn for input types
        """

        cmds = []

        bg_color = self.node.style.get("background-color", "transparent")

        if bg_color != "transparent":
            rect = DrawRect(self.self_rect(), bg_color)
            cmds.append(rect)

        if self.node.tag == "input":
            text = self.node.attributes.get("value", "")

        elif self.node.tag == "button":
            if len(self.node.children) == 1 and isinstance(self.node.children[0], Text):
                text = self.node.children[0].text

            else:
                print("Ignoring HTML contents inside button")
                text = ""

        color = self.node.style["color"]
        cmds.append(DrawText(self.x, self.y, text, self.font, color))

        if self.node.is_focused:
            cx = self.x + self.font.measure(text)
            cmds.append(DrawLine(cx, self.y, cx, self.y + self.height, "black", 1))

        return cmds
