var count = 0;

// callback to update counter & make XHR
var output = document.querySelectorAll("div")[1];
function callback() {
    if (count == 0)
        requestXHR();

    for (var i = 0; i < 5e6; i++);

    output.innerHTML = "count: " + (count++);
    if (count < 100)
        requestAnimationFrame(callback);
}
requestAnimationFrame(callback);

var request;

// XHR call
function requestXHR() {
    request = new XMLHttpRequest();
    request.open('GET', '/xhr', true);
    request.onload = function(evt) {
        document.querySelectorAll("div")[2].innerHTML = 
            "XHR result: " + this.responseText;
    };
    request.send();
}