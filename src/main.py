import tkinter

from browser import Browser

if __name__ == "__main__":
    import sys

    browser = Browser(sys.argv[1])
    browser.load()

    # event loop to keep the window alive and listen to events
    tkinter.mainloop()