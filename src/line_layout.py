class LineLayout:
    def __init__(self, node, parent, previous) -> None:
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []

        self.x = 0
        self.y = 0
        self.height = 0
        self.width = 0

    
    def layout(self):
        """
        laying out LineLayout objects in the layout tree
        """

        self.width = self.parent.width
        self.x = self.parent.x

        # if prior nodes, add their current y + height
        if self.previous:
            self.y = self.previous.y + self.previous.height

        # if node prior nodes, same as parent
        else:
            self.y = self.parent.y

        # run layout for TextLayout nodes under the LineLayout parent
        for word in self.children:
            word.layout()

        # if no children do not compute font metrics, 
        # since there will be no TextLayout child nodes
        if not self.children:
            self.height = 0
            return

        # compute ascent, descent to layout words accurately
        max_ascent = max([word.font.metrics("ascent") for word in self.children])
        baseline = self.y + 1.25 * max_ascent

        for word in self.children:
            word.y = baseline - word.font.metrics("ascent")

        max_descent = max([word.font.metrics("descent") for word in self.children])

        self.height = 1.25 * (max_ascent + max_descent)

    
    def paint(self):

        return []
    

    def should_paint(self):
        return True
    

    def __repr__(self) -> str:
        return f"LineLayout(x={self.x}, y={self.y}, width={self.width}, height={self.height})"
