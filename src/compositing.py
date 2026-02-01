import skia
from helpers import parse_color
from config import SHOW_COMPOSITED_LAYER_BORDERS


class PaintCommand:
    def __init__(self, rect) -> None:
        self.rect = rect
        self.children = []


class VisualEffect:
    def __init__(self, rect, children, node=None) -> None:
        self.rect = rect.makeOffset(0.0, 0.0)
        self.children = children

        # we merge rects of the child elements with parent
        for child in self.children:
            self.rect.join(child.rect)

        self.node = node

        # checking if an element needs compositing
        # this is done by checking if any of the child 
        # nodes needs compositing provided they are Visual Effect nodes
        self.needs_compositing = any([
            child.needs_compositing for child in self.children
            if isinstance(child, VisualEffect)])


class CompositedLayer:
    """
    This is our custom surface where we cache the child 
    contents before apply effects and copying them to the root surface
    """

    def __init__(self, skia_context, display_item) -> None:
        self.skia_context = skia_context
        self.surface = None
        self.display_items = [display_item]
        self.parent = display_item.parent


    def composited_bounds(self):
        """
        compute the bounds of the composited layer
        """

        rect = skia.Rect.MakeEmpty()

        for item in self.display_items:
            rect.join(absolute_to_local(
                item, local_to_absolute(item, item.rect)))

        rect.outset(1, 1)

        return rect
    

    def raster(self):
        """
        draw display list items onto composited layer
        """

        bounds = self.composited_bounds()

        if bounds.isEmpty(): return
        irect = bounds.roundOut()

        # create surface if there is none
        if not self.surface:
            self.surface = skia.Surface.MakeRenderTarget(
                self.skia_context, skia.Budgeted.kNo,
                skia.ImageInfo.MakeN32Premul(
                    irect.width(), irect.height()))
            
            if not self.surface:
                self.surface = skia.Surface(irect.width(), irect.height())
            
            assert self.surface

        canvas = self.surface.getCanvas()
        canvas.clear(skia.ColorTRANSPARENT)
        canvas.save()
        canvas.translate(-bounds.left(), -bounds.top())

        # draw display list items to canvas
        for item in self.display_items:
            item.execute(canvas)

        canvas.restore()

        # use to draw bounds of the composited layer
        if SHOW_COMPOSITED_LAYER_BORDERS:
            border_rect = skia.Rect.MakeXYWH(1, 1, irect.width() - 2, irect.height() - 2)
            DrawOutline(border_rect, "red", 1).execute(canvas)


    def add(self, display_item):
        """
        add display list items to the same composited layer.
        this is done to reduce number of composited layers.
        """

        assert self.can_merge(display_item)
        self.display_items.append(display_item)


    def can_merge(self, display_item):
        """
        to determine if display list items are compatible 
        to be added into the same composited layers.
        """

        # display items can be merged if it has same parents 
        # as existing ones in the composited layer
        return display_item.parent == self.display_items[0].parent
    

    def absolute_bounds(self):
        """
        compute global bounds of the composited layer
        """

        rect = skia.Rect.MakeEmpty()
        for item in self.display_items:
            rect.join(local_to_absolute(item, item.rect))
        return rect
    

    def __repr__(self):
        return ("layer: composited_bounds={} " +
            "absolute_bounds={} first_chunk={}").format(
            self.composited_bounds(), self.absolute_bounds(),
            self.display_items if len(self.display_items) > 0 else 'None')


class DrawCompositedLayer(PaintCommand):
    def __init__(self, composited_layer) -> None:
        self.composited_layer = composited_layer
        super().__init__(self.composited_layer.composited_bounds())


    def execute(self, canvas):
        """
        draw composited layer onto its associated surface
        """

        layer = self.composited_layer
        if not layer.surface: return
        bounds = layer.composited_bounds()
        layer.surface.draw(canvas, bounds.left(), bounds.top())


    def __repr__(self) -> str:
        return "DrawCompositedLayer()"
    

class NumericAnimation:
    def __init__(self, old_value: str, 
                 new_value: str, num_frames: int) -> None:

        self.old_value = float(old_value)
        self.new_value = float(new_value)
        self.num_frames = num_frames

        self.frame_count = 1
        total_change = self.new_value - self.old_value
        self.change_per_frame = total_change / num_frames


    def animate(self):
        """
        determine new value of property depending 
        on change per frame and current frames
        """

        self.frame_count += 1
        if self.frame_count >= self.num_frames: return
        current_value = self.old_value + self.change_per_frame * self.frame_count

        return str(current_value)
    

    def __repr__(self):
        return f"NumericAnimation(old_value={self.old_value}, change_per_frame={self.change_per_frame}, num_frames={self.num_frames})"
    

class Transform(VisualEffect):
    def __init__(self, translation, rect, node, children):
        super().__init__(rect, children, node)
        self.self_rect = rect
        self.translation = translation


    def execute(self, canvas):
        """
        draw items onto surface
        """
    
        if self.translation:
            (x, y) = self.translation
            canvas.save()
            canvas.translate(x, y)

        for cmd in self.children:
            cmd.execute(canvas)

        if self.translation:
            canvas.restore()


    def clone(self, child):
        """
        create a copy of the transform
        """

        return Transform(self.translation, self.self_rect, 
                         self.node, [child])
    

    def map(self, rect):
        """
        move rect by translation factor
        """

        return map_translation(rect, self.translation)
    

    def unmap(self, rect):
        """
        move rect by -1 * translation factor
        """

        return map_translation(rect, self.translation, True)


    def __repr__(self):
        if self.translation:
            (x, y) = self.translation
            return f"Transform(translate(x={x}, y={y}))"

        else:
            return "Transform(<no-op>)"
        

class DrawOutline(PaintCommand):
    def __init__(self, rect, color: str, thickness: int) -> None:

        super().__init__(rect)
        self.color = color
        self.thickness = thickness

    
    def execute(self, canvas):
        """
        draw rectangle with borders on canvas
        """

        paint = skia.Paint(Color=parse_color(self.color),
                           StrokeWidth=self.thickness,
                           Style=skia.Paint.kStroke_Style)
        
        canvas.drawRect(self.rect, paint)
        
    
    def __repr__(self):
        return f"DrawOutline({self.rect.left()}, {self.rect.top()}, {self.rect.right()}, \
            {self.rect.bottom()}, color={self.color}, thickness={self.thickness})"
    

def parse_transform(transform_str):
    """
    parsing function in transform css property.
    currently only supports translate.
    ref: https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/transform
    """

    if transform_str.find('translate(') < 0:
        return None
    
    left_paren = transform_str.find('(')
    right_paren = transform_str.find(')')

    (x_px, y_px) = transform_str[left_paren + 1: right_paren].split(",")

    return (float(x_px[-2:]), float(y_px[-2:]))


def map_translation(rect, translation, reversed=False):
    """
    used to move our rect by the translation factor
    """

    if not translation:
        return rect

    else:
        (x, y) = translation
        matrix = skia.Matrix()

        if reversed:
            matrix.setTranslate(-x, -y)

        else:
            matrix.setTranslate(x, y)

        return matrix.mapRect(rect)
    

def absolute_bounds_for_obj(obj):
    """
    apply all of the parent transformation on the objects rect
    """

    rect = skia.Rect.MakeXYWH(
        obj.x, obj.y, obj.width, obj.height)

    cur = obj.node

    while cur:
        rect = map_translation(rect, parse_transform(cur.style.get("transform", "")))
        cur = cur.parent

    return rect


def local_to_absolute(display_item, rect):
    """
    determines where an item is positioned globally
    """

    # iterate up the tree until no parent nodes
    while display_item.parent:

        # get the rect at the translate position
        rect = display_item.parent.map(rect)

        # get parent of the current display list
        display_item = display_item.parent

    return rect


def absolute_to_local(display_item, rect):
    """
    determines relative position of an item using the tree hierarchy
    """

    parent_chain = []

    while display_item.parent:
        parent_chain.append(display_item.parent)
        display_item = display_item.parent

    for parent in reversed(parent_chain):
        rect = parent.unmap(rect)

    return rect
