from tkinter.font import Font
from tkinter import Canvas

class DrawText:
    def __init__(self, x1: int, y1: int,
                 text: str, font: Font, color: str):

        self.rect = Rect(x1, y1, x1 + font.measure(text),
                         y1 + font.metrics("linespace"))
        self.text = text
        self.font = font
        self.color = color

        self.bottom = y1 + font.metrics("linespace")


    def execute(self, scroll: int, canvas: Canvas):
        """
        make text object
        """

        canvas.create_text(
            self.rect.left, self.rect.top - scroll,
            text=self.text,
            font=self.font,
            fill=self.color,
            anchor="nw")


    def __repr__(self):
        return f"DrawText(text={self.text})"


class Rect:
    def __init__(self, left, top, right, bottom) -> None:
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom


    def contains_point(self, x, y):
        """
        check if a point lies in the bounds of rectangle
        """

        return x >= self.left and x < self.right \
            and y >= self.top and y < self.bottom


class DrawRect:
    def __init__(self, rect: Rect, color: str):

        self.rect = rect
        self.color = color


    def execute(self, scroll: int, canvas: Canvas):
        """
        make rectangle object
        """

        canvas.create_rectangle(
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            width=0,
            fill=self.color)
        
    
    def __repr__(self):
        return f"DrawRect(top={self.rect.top} left={self.rect.left} bottom={self.rect.bottom} right={self.rect.right} color={self.color})"


class DrawOutline:
    def __init__(self, rect, color, thickness) -> None:
        self.rect = rect
        self.color = color
        self.thickness = thickness

    
    def execute(self, scroll: int, canvas: Canvas):
        """
        draw outline for the rectangle
        """

        canvas.create_rectangle(
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            width=self.thickness,
            outline=self.color)
        
    
    def __repr__(self):
        return f"DrawOutline({self.rect.left}, {self.rect.top}, {self.rect.right}, {self.rect.bottom}, color={self.color}, thickness={self.thickness})"


class DrawLine:
    def __init__(self, x1: int, y1: int, x2: int, y2: int,
                 color: str, thickness: int) -> None:

        self.rect = Rect(x1, y1, x2, y2)
        self.color = color
        self.thickness = thickness

    
    def execute(self, scroll: int, canvas: Canvas):
        """
        draw line
        """

        canvas.create_line(
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            fill=self.color, width=self.thickness)


    def __repr__(self):
        return f"DrawLine({self.rect.left}, {self.rect.top}, {self.rect.right}, {self.rect.bottom}, color={self.color}, thickness={self.thickness})"