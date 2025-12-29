import dukpy
import traceback
from css_parser import CSSParser
from helpers import tree_to_list
from html_parser import HTMLParser


RUNTIME_JS = open("runtime.js").read()
EVENT_DISPATCH_JS = "new Node(dukpy.handle).dispatchEvent(new Event(dukpy.type))"


class JSContext:
    def __init__(self, tab) -> None:
        
        # specifying tab for which js context is being defined
        self.tab = tab

        self.interp = dukpy.JSInterpreter()

        # we bridge js - python execution by specifying which function
        # should execute in python when console.log is encountered in js script

        # exporting log function
        self.interp.export_function("log", print)
        
        # DOM API functions
        self.interp.export_function("querySelectorAll", self.querySelectorAll)

        self.interp.export_function("getAttribute", self.getAttribute)

        self.interp.export_function("innerHTML_set", self.innerHTML_set)

        # js runtime, executes before any other js code/scripts
        self.interp.evaljs(RUNTIME_JS)

        # keeps track of functions which bridge python 
        # based element nodes and js based node tree nodes
        self.node_to_handle = {}
        self.handle_to_node = {}


    def run(self, script: str, code: str):
        """
        execute javascript code/scripts
        """

        try:
            return self.interp.evaljs(code)

        except dukpy.JSRuntimeError as e:
            print("script", script, "crashed :(\n\n", e)

    
    def querySelectorAll(self, selector_text):
        """
        implements querySelectorAll DOM API.
        used to fetch all the selectors for a selector name
        """

        try:
            selector = CSSParser(selector_text).selector()

            # get all nodes in tree which match node type
            nodes = [node for node in tree_to_list(self.tab.nodes, [])
                    if selector.matches(node)]
            
            return [self.get_handle(node) for node in nodes]
        
        except:
            traceback.print_exc()
            raise


    def getAttribute(self, handle, attr):
        """
        implements getAttribute DOM API.
        used to fetch attributes for an html element
        """

        try:

            elt = self.handle_to_node[handle]
            attr = elt.attributes.get(attr, None)
            return attr if attr else ""
        
        except:
            traceback.print_exc()
            raise


    def get_handle(self, elt):
        """
        fetches functions which translate js dom 
        to browser dom actions
        """

        if elt not in self.node_to_handle:
            handle = len(self.node_to_handle)
            self.node_to_handle[elt] = handle
            self.handle_to_node[handle] = elt

        else:
            handle = self.node_to_handle[elt]

        return handle
    

    def dispatch_event(self, type, elt):
        # TODO: docstring

        handle = self.node_to_handle.get(elt, -1)

        do_default = self.interp.evaljs(EVENT_DISPATCH_JS, 
                                        type=type, handle=handle)

        return not do_default


    def innerHTML_set(self, handle, s):
        """
        implements innerHTML DOM API.
        Used to set the text with a pair of html tags
        """

        try:

            # parse text content to be added
            doc = HTMLParser("<html><body>" + s + "</body></html>").parse()
            new_nodes = doc.children[0].children

            # get element using handle
            elt = self.handle_to_node[handle]

            # add the text content as a child node
            elt.children = new_nodes

            for child in elt.children:
                child.parent = elt

            # re render
            self.tab.render()

        except:
            traceback.print_exc()
            raise
