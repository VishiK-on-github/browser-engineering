import tkinter.font


FONTS = {}


def print_tree(node, indent=0):
    """
    prints tree of html nodes in terminal
    """
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent+2)


def paint_tree(layout_object, display_list):
    """
    traverse layout objects compute DrawText, DrawRect nodes
    """

    display_list.extend(layout_object.paint())

    for child in layout_object.children:
        paint_tree(child, display_list)


def get_font(size, weight, style):
    """
    caching fonts to reuse instead of creating new objects. 
    cheaper when we have a lot of text and font repeating frequently
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


def tree_to_list(tree, list):
    """
    flattens a tree of nodes into a list
    """

    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)

    return list