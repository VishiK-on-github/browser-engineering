from block_layout import BlockLayout


HSTEP = 13
VSTEP = 18
WIDTH = 800


class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []

        self.x = 0
        self.y = 0
        self.height = 0
        self.width = 0


    def layout(self):
        """
        builds the layout tree
        """

        child = BlockLayout(self.node, self, None)
        self.children.append(child)

        self.width = WIDTH - 2 * HSTEP
        self.x = HSTEP
        self.y = VSTEP
        child.layout()
        self.height = child.height


    def paint(self):
        return []
