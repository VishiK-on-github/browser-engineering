import tkinter
from client import URL
from browser import Browser


if __name__ == "__main__":
    import sys

    browser = Browser()
    url_str = sys.argv[1]
    url = URL(url_str)
    browser.new_tab(url)

    # event loop to keep the window alive and listen to events
    tkinter.mainloop()