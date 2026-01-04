import skia


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

    # check if a layout object should be painted or not
    # important to check for input / button html elements
    if layout_object.should_paint():
        cmds = layout_object.paint()

    for child in layout_object.children:
        paint_tree(child, cmds)

    if layout_object.should_paint():
        cmds = layout_object.paint_effects(cmds)

    display_list.extend(cmds)


def get_font(size, weight, style):
    """
    caching fonts to reuse instead of creating new objects. 
    cheaper when we have a lot of text and font repeating frequently
    """

    key = (weight, style)

    if key not in FONTS:
        if weight == "bold":
            skia_weight = skia.FontStyle.kBold_Weight

        else:
            skia_weight = skia.FontStyle.kNormal_Weight

        if style == "italic":
            skia_style = skia.FontStyle.kItalic_Slant

        else:
            skia_style = skia.FontStyle.kUpright_Slant

        skia_width = skia.FontStyle.kNormal_Width
        style_info = skia.FontStyle(skia_weight, skia_width, skia_style)

        font = skia.Typeface('Aria', style_info)
        FONTS[key] = font

    return skia.Font(FONTS[key], size)


def tree_to_list(tree, list):
    """
    flattens a tree of nodes into a list
    """

    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)

    return list


NAMED_COLORS = {
    "black": "#000000",
    "white": "#ffffff",
    "red": "#ff0000",
    "green": "#00ff00",
    "blue": "#0000ff",
    "lightblue": "#add8e6",
    "lightgreen": "#90ee90",
    "orange": "#ffa500",
}


def parse_color(color):
    """
    parse color hex/string to skia color
    """

    if color.startswith("#") and len(color) == 7:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)

        return skia.Color(r, g, b)
    
    if color.startswith("#") and len(color) == 9:
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        a = int(color[7:9], 16)

        return skia.Color(r, g, b, a)
    
    elif color in NAMED_COLORS:
        return parse_color(NAMED_COLORS[color])
    
    else:
        return skia.ColorBLACK


def linespace(font):
    """
    get font height for a given font
    """

    metrics = font.getMetrics()
    return metrics.fDescent - metrics.fAscent
