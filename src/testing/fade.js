var div = document.querySelectorAll("div")[0];
var total_frames = 120;
var current_frame = 0;
var change_per_frame = (0.999 - 0.1) / total_frames;

function animate() {
    current_frame++;
    var new_opacity = current_frame * change_per_frame + 0.1;
    
    for (var i = 0; i < 5e6; i++);

    div.style = "opacity:" + new_opacity;
    if (current_frame < total_frames) {
        requestAnimationFrame(animate);
    }
}
requestAnimationFrame(animate);