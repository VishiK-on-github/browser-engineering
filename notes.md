## Some notes

### High Level Flow

1. Based on the url, browser fetches content from server
2. The fetched text content is parsed to create a tree of html nodes
3. Styling information is fetched and applied to the nodes in the tree of html nodes
4. The html node tree + styling info is parsed to build a layout tree, which is a tree of blocks which will be rendered to the screen
5. The contents of the layout tree are flattened to render skia objects onto the SDL window
6. We have a lightweight javascript interpreter which executes scripts used by the webpage
7. we have cookies and security policies to access them to ensure secure access to servers 

### Security

Cookies have been implemented, to prevent misuse we have the following mechanisms:

1. Cross-Site Request: to prevent malicious cross site request we enforce XMLHttpRequest to check origin of the to be request is same as the current tabs url origin on the browser side
2. CSRF: to prevent CSRF while submitting forms we ensure there are server side nonce added to forms. We also add SameSite cookies to specify browser side rules on who can access our cookies in our case we implement lax which allows same site POST and cross site GET request
3. Cross-Site Scripting: To prevent cookies from being misued by js scripts we encode user posted data in html.encode method
4. Content-Security-Policies: These are server side headers which specify origins from which content can be downloaded. This is to prevent malicious scripts from executing if they have somehow been injected

### Rendering

1. Order of operations is extremely important when compositing layers
2. Skia has two main components, canvas and surfaces. Canvas is the tools/apis used to write on surface. Surface is where the actions/drawing is performed, it holds the pixel data.
3. Canvas is bound to a surface because different surfaces allow different actions to be performed on them
4. canvas.save(), canvas.restore() are used to save and pop state from the surface stack
5. After the process of drawing is complete we create an immutable image using the root surface, copy the bytes to the SDL window and refresh the SDL window to show new contents.
6. Refer to Browser classes draw method to get more details
- Cool find: https://ciechanow.ski/cameras-and-lenses/

### JS - Python Co-Execution Flow

When a website's JS script is downloaded and evaluated the execution flow generally happens in the following fashion:

1. When a piece of websites JS Script is evaluated using the dukpy interpreter, its implementation in the runtime is invoked
2. The JS runtime implementation generally has a call_python("<method-name>") within them it leads to bridging of the execution between the JS runtime & browser runtime
3. The python browser has its own implementation which is bridged using export functions in the JSContext
4. The browser implementation schedules task in its task queue to make necessary changes (typically DOM changes) to redraw changes onto the browser window in response to JS invocation

### Threading Running
1. The code running in the main thread requests an animation frame with set_needs_animation_frame, perhaps in response to an event handler or due to requestAnimationFrame.
2. The browser thread event loop schedules an animation frame on the main thread TaskRunner.
3. The main thread executes its part of rendering, then calls browser.commit.
4. The browser thread rasters the display list and draws to the screen.
- Chromes way: https://developer.chrome.com/docs/chromium/renderingng-architecture#process_and_thread_structure

### When to Raster & Draw vs Schedule Animation Frame - Gemini's Suggestion

#### When to Raster and Draw:
Rastering and Drawing is the act of taking your layout objects and turning them into pixels on the screen. This should be reactive. You only do this when the "state" of what the user sees has changed.

- You should trigger set_needs_raster_and_draw() in these specific moments:
- Browser UI Changes: When the user types in the address bar or switches tabs (Chrome changes).
- Tab Content "Commit": When the Tab thread finishes a new Layout and sends a CommitData object to the Browser.
- Scrolling: When the user moves the scrollbar, the offset changes, so the pixels must be recalculated.
- Resizing: If you were to change the window size, the layout would shift.

Key Rule: Never raster if nothing has changed. Your if not self.needs_raster_and_draw: return guard clause in raster_and_draw is exactly how you enforce this.

#### When to Schedule Animation Frames:
Scheduling Animation Frames is the act of "poking" the JavaScript engine to ask if it wants to change anything for the next refresh of the screen. This should be proactive but throttled.

You should schedule an animation frame when:

- JavaScript requested it: The JS code specifically called requestAnimationFrame(). This sets the needs_animation_frame flag.
- Ongoing Animations: If an animation is mid-way (like your counter), each frame should schedule the next one.
- User input requires a JS response: If a user clicks a button that has a JS event listener, you might schedule a frame to handle the visual update resulting from that click.