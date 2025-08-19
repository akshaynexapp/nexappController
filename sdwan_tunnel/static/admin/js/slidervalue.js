// # --- Static File: static/admin/js/slider_value_display.js ---
// Attach live value display for each range input
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('input[type=range]').forEach(function(slider) {
        var output = document.createElement('span');
        output.className = 'slider-value';
        slider.parentNode.insertBefore(output, slider.nextSibling);
        var update = function() { output.textContent = slider.value + '%'; };
        slider.addEventListener('input', update);
        update();
    });
});