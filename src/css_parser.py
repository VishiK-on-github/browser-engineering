from element import Element
from tag_selector import TagSelector
from descendent_selector import DescendantSelector
from compositing import NumericAnimation


INHERITED_PROPERTIES = {
    "font-size": "16px",
    "font-style": "normal",
    "font-weight": "normal",
    "color": "black",
}
REFRESH_RATE_SEC = 0.033


class CSSParser:
    def __init__(self, s: str):
        self.s = s
        self.i = 0
    

    def whitespace(self):
        """
        skips whitespaces while parsing
        """

        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    
    def word(self):
        """
        returns parsed word
        """

        start = self.i
        in_quote = False

        while self.i < len(self.s):

            cur = self.s[self.i]

            if cur == "'":
                in_quote = not in_quote

            if cur.isalnum() or cur in ",/#-.%()\"'" or (in_quote and cur == ":"):
                self.i += 1

            else:
                break

        if not (self.i > start):
            raise Exception("Parsing error")
        
        return self.s[start:self.i]


    def literal(self, literal: str):
        """
        checks if a string is equal to a character
        """

        if not (self.i < len(self.s) and self.s[self.i] == literal):
            raise Exception("Parsing Error")
        
        self.i += 1


    def pair(self, until):
        """
        extract one property value pairs
        which describe styling info of elements
        """

        prop = self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        val = self.until_chars(until)
        return prop.casefold(), val.strip()
    

    def body(self):
        """
        extract multiple property value pairs
        """

        pairs = {}
        while self.i < len(self.s) and self.s[self.i] != "}":

            try:
                prop, value = self.pair([";", "}"])
                pairs[prop] = value
                self.whitespace()
                self.literal(";")
                self.whitespace()

            except Exception:
                why = self.ignore_until([";", "}"])

                if why == ";":
                    self.literal(";")
                    self.whitespace()

                else:
                    break

        return pairs
    

    def ignore_until(self, chars):
        """
        ignore characters till we reach the 
        next supported instance of the character
        """
        
        while self.i < len(self.s):
            if self.s[self.i] in chars:
                return self.s[self.i]
            
            else:
                self.i += 1

        return None


    def selector(self):
        """
        parses selectors in css files
        """

        out = TagSelector(self.word().casefold())
        self.whitespace()
        while self.i < len(self.s) and self.s[self.i] != "{":
            tag = self.word()
            descendant = TagSelector(tag.casefold())
            out = DescendantSelector(out, descendant)
            self.whitespace()

        return out
    

    def parse(self):
        """
        parses css files. files can be on device or stylesheets links by webpage authors
        """

        rules = []

        while self.i < len(self.s):

            try:
                self.whitespace()
                selector = self.selector()
                self.literal("{")
                self.whitespace()
                body = self.body()
                self.literal("}")
                rules.append((selector, body))

            except Exception:
                why = self.ignore_until(["}"])
                if why == "}":
                    self.literal("}")
                    self.whitespace()

                else:
                    break

        return rules
    

    def until_chars(self, chars):
        """
        gather string content
        """

        start = self.i

        while self.i < len(self.s) and self.s[self.i] not in chars:
            self.i += 1

        return self.s[start:self.i]
    

def parse_transition(value):
    """
    parsing function in transform css property.
    currently only supports translate.
    ref: https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/transition
    """

    properties = {}
    
    if not value: return properties

    for item in value.split(","):

        property, duration = item.split(" ", 1)
        frames = int(float(duration[:-1]) / REFRESH_RATE_SEC)
        properties[property] = frames

    return properties


def style(node, rules, tab):
    """
    parses attributes of a node and add them as style property
    """
    
    old_style = node.style
    node.style = {}
    
    # we apply the inherited properties
    for prop, default_val in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[prop] = node.parent.style[prop]
        else:
            node.style[prop] = default_val

    # we iterate over the set of rules from stylesheets - browser and content
    for selector, body in rules:
        if not selector.matches(node): continue
        for prop, value in body.items():
            node.style[prop] = value

    # we get styling information of the html node's attribute,
    # parse and add it into the styling info
    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()

        for prop, value in pairs.items():
            node.style[prop] = value

    # we resolve font-size info from percentage to pixel
    if node.style["font-size"].endswith("%"):
        if node.parent:
            parent_font_size = node.parent.style["font-size"]
        
        else:
            parent_font_size = INHERITED_PROPERTIES["font-size"]

        node_pct = float(node.style["font-size"][:-1]) / 100
        parent_px = float(parent_font_size[:-2])
        node.style["font-size"] = str(node_pct * parent_px) + "px"

    # if we have an old style, check difference and re-render
    if old_style:
        transitions = diff_styles(old_style, node.style)

        for property, (old_value, new_value, num_frames) in transitions.items():
            if property == "opacity":
                tab.set_needs_render()
                animation = NumericAnimation(old_value, new_value, num_frames)
                node.animations["property"] = animation
                node.style[property] = animation.animate()

    # we recursively apply the styling info
    for child in node.children:
        style(child, rules, tab)


def cascade_priority(rule):
    """
    returns selectors priority in case of multiple css rules
    """
    selector, _ = rule
    return selector.priority


def diff_styles(old_style, new_style):
    """
    This method is used to check which css properties 
    have been updated between two runs of style
    """

    transition = {}

    for property, num_frames in parse_transition(new_style.get("transition")).items():
        if property not in old_style: continue
        if property not in new_style: continue

        old_value = old_style[property]
        new_value = new_style[property]

        # checking if properties have changed
        if old_value == new_value: continue

        transition[property] = (old_value, new_value, num_frames)

    return transition
