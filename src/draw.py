from tkinter.font import Font
from tkinter import Canvas

class DrawText:
    def __init__(self, x1: int, y1: int,
                 text: str, font: Font, color: str):

        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.color = color

        self.bottom = y1 + font.metrics("linespace")


    def execute(self, scroll: int, canvas: Canvas):
        """
        make text object
        """

        canvas.create_text(
            self.left, self.top - scroll,
            text=self.text,
            font=self.font,
            fill=self.color,
            anchor="nw")


class DrawRect:
    def __init__(self, x1: int, y1: int,
                 x2: int, y2: int, color: str):

        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color


    def execute(self, scroll: int, canvas: Canvas):
        """
        make rectangle object
        """

        canvas.create_rectangle(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            width=0,
            fill=self.color)