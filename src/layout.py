import tkinter
import tkinter.font

from text import Text

HSTEP = 13
VSTEP = 18
WIDTH = 800
HEIGHT = 600
FONTS = {}

class Layout:
    def __init__(self, tokens):
        self.tokens = tokens
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12
        self.line = []

        for tok in tokens:
            self.token(tok)

        # flushing after processing all tokens
        self.flush()


    def flush(self):
        """
        This method recomputes the y axis for text to prevent
        text from looking like its hanging from the top
        irrespective of size
        """
        if not self.line: return

        # calculate max ascent
        metrics = [font.metrics() for x, word, font in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])

        # calculating baseline using max ascent
        baseline = self.cursor_y + 1.25 * max_ascent

        for x, word, font in self.line:
            y = baseline - font.metrics("ascent")
            self.display_list.append((x, y, word, font))

        # moving up to accomodate words ascent
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

        # rest back to start
        self.cursor_x = HSTEP
        self.line = []


    def token(self, tok):

        if isinstance(tok, Text):
                
            for word in tok.text.split():
                self.word(word)

        elif tok.tag == "i":
            self.style = "italic"
        
        elif tok.tag == "/i":
            self.style = "roman"

        elif tok.tag == "b":
            self.weight = "bold"
        
        elif tok.tag == "/b":
            self.weight = "normal"

        elif tok.tag == "small":
            self.size -= 2

        elif tok.tag == "/small":
            self.size += 2

        elif tok.tag == "big":
            self.size += 4

        elif tok.tag == "/big":
            self.size -= 4

        elif tok.tag == "br":
            self.flush()

        elif tok.tag == "/p":
            self.flush()
            self.cursor_y += VSTEP


    def word(self, word):
        font = get_font(self.size, self.weight, self.style)
        w = font.measure(word)
        
        # break and next line
        if self.cursor_x + w >= WIDTH - HSTEP:
            self.flush()

        self.line.append((self.cursor_x, word, font))
        self.cursor_x += w + font.measure(" ")


def get_font(size, weight, style):
    """
    caching fonts to reuse instead of creating new objects
    cheaper when we have a lot of text
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
