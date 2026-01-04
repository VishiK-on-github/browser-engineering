import skia
from helpers import parse_color


class DrawText:
    def __init__(self, x1: int, y1: int,
                 text: str, font, color: str):

        self.rect = skia.Rect.MakeLTRB(x1, y1, x1 + font.measureText(text),
                                       y1 - font.getMetrics().fAscent + \
                                        font.getMetrics().fDescent)

        self.text = text
        self.color = color
        self.font = font


    def execute(self, canvas):
        """
        draw text on canvas
        """

        paint = skia.Paint(AntiAlias=True,
                           Color=parse_color(self.color))
        
        baseline = self.rect.top() - self.font.getMetrics().fAscent

        canvas.drawString(self.text, float(self.rect.left()), 
                          baseline, self.font, paint)


    def __repr__(self):
        return f"DrawText(text={self.text})"


class DrawRect:
    def __init__(self, rect, color: str) -> None:

        self.rect = rect
        self.color = color


    def execute(self, canvas):
        """
        draw rectangle on canvas
        """

        paint = skia.Paint(Color=parse_color(self.color))
        canvas.drawRect(self.rect, paint)
        
    
    def __repr__(self):
        return f"DrawRect(top={self.rect.top()}, left={self.rect.left()}, \
            bottom={self.rect.bottom()}, right={self.rect.right()}, color={self.color})"


class DrawOutline:
    def __init__(self, rect, color: str, thickness: int) -> None:

        self.rect = rect
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
        return f"DrawOutline({self.rect.left}, {self.rect.top}, {self.rect.right}, \
            {self.rect.bottom}, color={self.color}, thickness={self.thickness})"


class DrawLine:
    def __init__(self, x1: int, y1: int, x2: int, y2: int,
                 color: str, thickness: int) -> None:

        self.rect = skia.Rect.MakeLTRB(x1, y1, x2, y2)
        self.color = color
        self.thickness = thickness

    
    def execute(self, canvas):
        """
        draw line on canvas
        """

        path = skia.Path().moveTo(self.rect.left(), self.rect.top())\
            .lineTo(self.rect.right(), self.rect.bottom())
        
        # style set to stroke to specify that to draw 
        # along the path instead of filling inside path
        paint = skia.Paint(Color=parse_color(self.color), 
                           StrokeWidth=self.thickness, 
                           Style=skia.Paint.kStroke_Style)
        
        canvas.drawPath(path, paint)


    def __repr__(self):
        return f"DrawLine({self.rect.left()}, {self.rect.top()}, {self.rect.right()}, \
            {self.rect.bottom()}, color={self.color}, thickness={self.thickness})"
    

class DrawRRect:
    def __init__(self, rect, radius: float, color: str):
    
        self.rect = rect
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        self.color = color
        self.radius = radius


    def execute(self, canvas):
        """
        draw rounded rectangle on canvas
        """

        paint = skia.Paint(Color=parse_color(self.color))
        canvas.drawRRect(self.rrect, paint)

    
    def __repr__(self):
        return f"DrawRRect(top={self.rect.top()}, left={self.rect.left()}, \
            bottom={self.rect.bottom()}, right={self.rect.right()}, color={self.color}), radius={self.radius}"
