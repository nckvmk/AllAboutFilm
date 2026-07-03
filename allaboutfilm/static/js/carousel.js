//When recording a click from the user within the area of the carousel, the target image is opened in a new tab.

$(document).ready(function() {
    $(".carousel-item img").on("click", function() {
        window.open($(this).attr("src"), "_blank");
    });
});