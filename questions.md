## Questions

Noting some questions I have along the way:

1. Can a page be fetched from the browsers local cache without reaching out to a server multiple time, maybe for less frequently changing content?
2. How are adversarial attacks mitigated by browser some areas: memory/resource access, credential stealing, loading corrupted js scripts
3. How is rendering of websites made faster by browsers?
4. What networking optimizations are used in browsers?
- https://hpbn.co/
5. Why is requestAnimationFrame used?
- primarily used to support high performance animations
- rAF allows for sync with screens refresh rate to prevent calculating frames which a user would never see
- It allows supports automatically stop screen refresh incase a tab is inactive
6. In real world browsers how many types threads are used and for what purpose?
- https://developer.chrome.com/docs/chromium/renderingng-architecture#process_and_thread_structure
7. What are cons of using GPU based rendering?
- Any of the four steps can make GPU raster and draw slow. Large display lists take a while to upload. Complex display list commands take longer to compile. Raster can be slow if there are many surfaces, and draw can be slow if surfaces are deeply nested. On a CPU, the upload step and compile steps aren’t necessary, and more memory is available for raster and draw. Of course, many optimizations are available for both GPUs and CPUs, so choosing the best way to raster and draw a given page can be quite complex.