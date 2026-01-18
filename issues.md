## Issues

Some issues and notes on how i fixed them

1. Black screen due to issues in raster_tab method (maybe)
2. Fixed: When we scroll down at the start it works correctly, once we reach the end of the screen and then scroll up & scroll down it jumps to the end of the screen. There is some piece of code which is not getting updated which leads to this jumping
- Fix: My code to update scolling up used non threaded version, which did not update self.active_tab_scroll variable
3. Fixed: Server code breaks when browser started for https://localhost:8000/count
- This seems to be because of https protocol usage for the specific domain name.
- Fix: I need to use http instead of https while running the browsers main script
4. Fixed: eventloop.js script works correctly on chrome browser but does not animate correctly in my browser
- Fix: the issue was mainly because of __runRAFHandlers() function in runtime.js not having its for loop variable initialized correctly
5. Fixed: Render task does not end after looking at trace
- Fix: one instance where render was being profiled did not used the measure.time function instead of measure.stop, this has been fixed
6. Fixed: When I enter a new address in my browser the webpage stops for a long time and does not render the new page
- Fix: When pressing enter the section of code had a lock.acquire instead of a lock.release which resulted in the error