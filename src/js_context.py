import dukpy
import traceback
from css_parser import CSSParser
from helpers import tree_to_list
from html_parser import HTMLParser
import threading
from task import Task


RUNTIME_JS = open("runtime.js").read()
# creates an event of type and for a node associated with a handler in js context
EVENT_DISPATCH_JS = "new Node(dukpy.handle).dispatchEvent(new Event(dukpy.type))"

SETTIMEOUT_JS = "__runSetTimeout(dukpy.handle)"
XHR_ONLOAD_JS = "__runXHROnload(dukpy.out, dukpy.handle)"


class JSContext:
    def __init__(self, tab) -> None:
        
        # specifying tab for which js context is being defined
        self.tab = tab

        # it is used to prevent async tasks completion on one 
        # tab from affecting behaviour of another tab
        self.discarded = False

        self.interp = dukpy.JSInterpreter()

        # we bridge js - python execution by specifying which function
        # should execute in python when console.log is encountered in js script

        # exporting log function
        self.interp.export_function("log", print)
        
        # DOM API functions
        self.interp.export_function("querySelectorAll", self.querySelectorAll)

        self.interp.export_function("getAttribute", self.getAttribute)

        self.interp.export_function("innerHTML_set", self.innerHTML_set)

        self.interp.export_function("XMLHttpRequest_send", self.XMLHttpRequest_send)

        self.interp.export_function("setTimeout", self.setTimeout)

        self.interp.export_function("requestAnimationFrame", self.requestAnimationFrame)

        self.interp.export_function("style_set", self.style_set)

        # start profiling js runtime eval
        self.tab.browser.measure.time('script-runtime')

        # js runtime, executes before any other js code/scripts
        self.interp.evaljs(RUNTIME_JS)

        # end profiling js runtime eval
        self.tab.browser.measure.stop('script-runtime')

        # keeps track of functions which bridge python 
        # based element nodes and js based node tree nodes
        self.node_to_handle = {}
        self.handle_to_node = {}


    def run(self, script: str, code: str):
        """
        execute javascript code/scripts
        """

        try:

            self.tab.browser.measure.time('script-load')
            self.interp.evaljs(code)
            self.tab.browser.measure.stop('script-load')

        except dukpy.JSRuntimeError as e:
            self.tab.browser.measure.stop('script-load')
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
        to browser dom element
        """

        if elt not in self.node_to_handle:
            handle = len(self.node_to_handle)
            self.node_to_handle[elt] = handle
            self.handle_to_node[handle] = elt

        else:
            handle = self.node_to_handle[elt]

        return handle
    

    def dispatch_event(self, type, elt):
        """
        Uses handles to dispatch events in js context
        """

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

            # re render, since we have modified the layout tree
            self.tab.set_needs_render()

        except:
            traceback.print_exc()
            raise


    def dispatch_xhr_onload(self, out, handle):
        """
        dispatch XHR request back to js runtime
        """

        if self.discarded: return

        self.tab.browser.measure.time('script-xhr')
        do_default = self.interp.evaljs(XHR_ONLOAD_JS, out=out, handle=handle)
        self.tab.browser.measure.stop('script-xhr')


    def XMLHttpRequest_send(self, method, url, body, is_async, handle):
        """
        implements XMLHttpRequest API.
        Used to make request to websites from a loaded page.
        """

        full_url = self.tab.url.resolve(url)

        if not self.tab.allowed_request(full_url):
            raise Exception("Cross-Origin XHR blocked by CSP !")

        # compare origins to prevent accessing 
        # other websites to steal info
        if full_url.origin() != self.tab.url.origin():
            raise Exception("Cross-Origin XHR request is not allowed !")
        
        def run_load():
            headers, response = full_url.request(self.tab.url, body)
            task = Task(self.dispatch_xhr_onload, response, handle)
            self.tab.task_runner.schedule_task(task)

            if not is_async:
                return response

        if not is_async:
            return run_load()
        
        else:
            threading.Thread(target=run_load).start()
    

    def dispatch_settimeout(self, handle):
        """
        dispatches an event from browser to js runtime
        """

        if self.discarded: return

        self.tab.browser.measure.time('script-settimeout')
        self.interp.evaljs(SETTIMEOUT_JS, handle=handle)
        self.tab.browser.measure.stop('script-settimeout')


    def setTimeout(self, handle, time):
        """
        browser side implementation of setTimeout JS API
        """

        def run_callback():

            task = Task(self.dispatch_settimeout, handle)
            self.tab.task_runner.schedule_task(task)
        
        # thread waits for specified timing and 
        # then schedules dispatch task
        threading.Timer(time / 1000.0, run_callback).start()


    def requestAnimationFrame(self):
        """
        browser side implementation of rAF JS API
        """

        self.tab.browser.set_needs_animation_frame(self.tab)


    def style_set(self, handle, s):
        """
        implements browser side method to 
        update style for an element
        """

        elt = self.handle_to_node[handle]
        elt.attributes["style"] = s;
        self.tab.set_needs_render()
