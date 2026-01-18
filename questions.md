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