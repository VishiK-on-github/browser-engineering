## Some notes

On a high level the browser does the following:

1. Based on the url, browser fetches content from server
2. The fetched text content is parsed to create a tree of html nodes
3. Styling information is fetched and applied to the nodes in the tree of html nodes
4. The html node tree is parsed to build a layout tree
5. The contents of the layout tree are flattened to render into our tkinter canvas