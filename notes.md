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
2. Cool find: https://ciechanow.ski/cameras-and-lenses/
3. Skia has two main components, canvas and surfaces. Canvas is the tools/apis used to write on surface. Surface is where the actions/drawing is performed, it holds the pixel data.
4. Canvas is bound to a surface because different surfaces allow different actions to be performed on them
5. canvas.save(), canvas.restore() are used to save and pop state from the surface stack
6. After the process of drawing is complete we create an immutable image using the root surface, copy the bytes to the SDL window and refresh the SDL window to show new contents.
7. Refer to Browser classes draw method to get more details