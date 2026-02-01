import skia
from helpers import parse_color
from compositing import PaintCommand


class DrawText(PaintCommand):
    def __init__(self, x1: int, y1: int,
                 text: str, font, color: str):

        self.text = text
        self.color = color
        self.font = font
        super().__init__(skia.Rect.MakeLTRB(x1, y1,
            x1 + font.measureText(text),
            y1 - font.getMetrics().fAscent + font.getMetrics().fDescent))


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


class DrawRect(PaintCommand):
    def __init__(self, rect, color: str) -> None:

        super().__init__(rect)
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


class DrawLine(PaintCommand):
    def __init__(self, x1: int, y1: int, x2: int, y2: int,
                 color: str, thickness: int) -> None:

        super().__init__(skia.Rect.MakeLTRB(x1, y1, x2, y2))
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
    

class DrawRRect(PaintCommand):
    def __init__(self, rect, radius: float, color: str):
    
        super().__init__(rect)
        self.rrect = skia.RRect.MakeRectXY(rect, radius, radius)
        self.color = color


    def execute(self, canvas):
        """
        draw rounded rectangle on canvas
        """

        paint = skia.Paint(Color=parse_color(self.color))
        canvas.drawRRect(self.rrect, paint)

    
    def __repr__(self):
        return f"DrawRRect(rect={str(self.rrect)}, color={self.color})"
