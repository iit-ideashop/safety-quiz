
function flipCard(object) {
        object.classList.toggle("flipCard")
        console.log("in handler")
}

document.addEventListener('DOMContentLoaded', () => {
    const cnc = document.getElementById('cnc_card')
    const laser = document.getElementById('laser_card')
    const printers = document.getElementById('print_card')

    printers.addEventListener("mousedown", function() {
        flipCard(printers)
    })
    laser.addEventListener("mousedown", function() {
        flipCard(laser)
    })
    cnc.addEventListener("mousedown", function() {
        flipCard(cnc)
    })


});

document.addEventListener('DOMContentLoaded', () => {
    $(function () {
        $("#locationPopover").popover({
            html: true,
            content: function () {
                return $("#locationPopoverContent").html();
            }
        });
    });
});


