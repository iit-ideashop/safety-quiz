

function showCNC(){
        var $ = function( id ) { return document.getElementById( id ); };
        console.log('CNC button Clicked!')
        if($('cnc-Info').style.getPropertyValue('display') != 'none'){
            $('cnc-Info').style.setProperty('display', 'none')
            $('cnc-CTA').style.setProperty('opacity',1)
            console.log('CNC details shown!')
        }
        else{
            $('cnc-Info').style.setProperty('display', 'block')
            $('cnc-CTA').style.setProperty('opacity',0)
            console.log('CNC details hidden!')
        }
    }

function showBack(id, show){
        var $ = function( id ) { return document.getElementById( id ); };
        console.log('LP button Clicked!, show = ',show, 'id = ', id)
        if (show){
            id.style.setProperty('transform','rotateY(180deg)')
        }
        else{
            id.style.setProperty('transform','rotateY(0deg)')
        }

        // $('lp-front').style.setProperty('transform', 'rotateY(180deg)')
    }


document.addEventListener('DOMContentLoaded', () => {
    $(function () {
      $("#locationPopover").popover({
          html: true,
          content: function(){
              return $("#locationPopoverContent").html();
          }
      });
    });

    var location = document.getElementById('locationPopover')
});