from element import Element


class TagSelector:
    def __init__(self, tag):
        self.tag = tag
        self.priority = 1
    

    def matches(self, node):
        """
        checks and matches tags
        """

        return isinstance(node, Element) and self.tag == node.tag