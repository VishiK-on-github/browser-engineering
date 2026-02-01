import skia
from draw import DrawRRect
from compositing import VisualEffect, parse_transform, Transform
import config


class Blend(VisualEffect):
    def __init__(self, opacity, blend_mode, node, children) -> None:
        super().__init__(skia.Rect.MakeEmpty(), children, node)
        self.opacity = opacity
        self.blend_mode = blend_mode
        self.should_save = self.blend_mode or self.opacity < 1
        
        self.rect = skia.Rect.MakeEmpty()

        if config.USE_COMPOSITING and self.should_save:
            self.needs_compositing = True

        self.children = children
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


    def clone(self, child):
        """
        make a copy of the Blend node
        """

        return Blend(self.opacity, self.blend_mode, 
                     self.node, [child])
    

    def map(self, rect):
        """
        returns the intersected between rect and last child node
        """

        if self.children and isinstance(self.children[-1], Blend) and \
           self.children[-1].blend_mode == "destination-in":
    
            bounds = rect.makeOffset(0.0, 0.0)

            # calculate overlapping area
            bounds.intersect(self.children[-1].rect)
            return bounds

        else:
            return rect
        

    def unmap(self, rect):
        """
        inverts the clipping, in this case keep as it is
        """

        return rect


    def __repr__(self) -> str:
        args = ""

        if self.opacity < 1:
            args += f", opacity={self.opacity}"

        if self.blend_mode:
            args += f", blend_mode={self.blend_mode}"

        if not args:
            args = ", <no-op>"

        return f"Blend({args[2:]})"


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

    translation = parse_transform(node.style.get("transform", ""))
    opacity = float(node.style.get("opacity", "1.0"))
    blend_mode = node.style.get("mix-blend-mode")

    if node.style.get("overflow", "visible") == "clip":

        border_radius = float(node.style.get("border-radius", "0px")[:-2])

        if not blend_mode:
            blend_mode = "source-over"

        cmds.append(Blend(1.0, "destination-in", None,
                          [DrawRRect(rect, border_radius, "white")]))


    blend_op = Blend(opacity, blend_mode, node, cmds)
    node.blend_op = blend_op
    return [Transform(translation, rect, node, [blend_op])]
