import skia
from draw import DrawRRect


class Blend:
    def __init__(self, opacity, blend_mode, children) -> None:
        self.opacity = opacity
        self.blend_mode = blend_mode
        self.children = children
        self.should_save = self.blend_mode or self.opacity < 1
        
        self.rect = skia.Rect.MakeEmpty()

        for cmd in self.children:
            self.rect.join(cmd.rect)

    
    def execute(self, canvas):
        """
        draw surface blended with child surfaces using blend mode
        """

        paint = skia.Paint(Alphaf=self.opacity, 
                           BlendMode=parse_blend_mode(self.blend_mode))

        if self.should_save:
            canvas.saveLayer(None, paint)

        for cmd in self.children:
            cmd.execute(canvas)

        if self.should_save:
            canvas.restore()


def parse_blend_mode(blend_mode_str):
    """
    to determine which blend mode to be 
    used to when combining two surfaces
    """

    if blend_mode_str == "multiply":
        return skia.BlendMode.kMultiply
    
    elif blend_mode_str == "difference":
        return skia.BlendMode.kDifference
    
    elif blend_mode_str == "destination-in":
        return skia.BlendMode.kDstIn
    
    elif blend_mode_str == "source-over":
        return skia.BlendMode.kSrcOver
    
    else:
        return skia.BlendMode.kSrcOver
    

def paint_visual_effects(node, cmds, rect):
    """
    helps create blend node
    """

    opacity = float(node.style.get("opacity", "1.0"))
    blend_mode = node.style.get("mix-blend-mode")

    if node.style.get("overflow", "visible") == "clip":

        border_radius = float(node.style.get("border-radius", "0px")[:-2])

        if not blend_mode:
            blend_mode = "source-over"

        cmds.append(Blend(1.0, "destination-in", 
                          [DrawRRect(rect, border_radius, "white")]))

    # first transperancy then blending
    return [Blend(opacity, blend_mode, cmds)]
