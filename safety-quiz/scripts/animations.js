document.addEventListener("DOMContentLoaded", function(event){
    // var progressbars = document.getElementsByClassName("progress-bar")
    // if(progressbars.length != 0){
    //     var final_progress_values = []
    //     console.log("progressbars.length = ", progressbars.length)
    //         for (var i = 0; i < progressbars.length; i++) {
    //             final_progress_values.push(progressbars[i].getAttribute("final_width"))
    //             progressbars[i].style.width = "0%";
    //
    //     }
    //     for(var i=0; i< progressbars.length; i++){
    //         animate_progress(progressbars[i],final_progress_values[i], i)
    //     }
    //
    //     function animate_progress (target, value, delay_weight){
    //             anime({
    //                 targets: target,
    //                 width: value,
    //                 easing: 'spring',
    //                 autoplay: true,
    //                 delay: 500*delay_weight,
    //                 round: 1,
    //                 update: function(){
    //                     target.innerHTML = "<div style='color: black; font-weight: bold'>" + JSON.stringify((value)) + "</div>"
    //                 }
    //             })
    //     }

        console.log("Progress bars:", progressbars)
        console.log("final_progress_values:", final_progress_values)
    }

    var first_loop = true;
    anime({
      targets: 'svg path',
      endDelay: 1000,
      strokeDashoffset: [anime.setDashoffset, 0],
      easing: 'easeInOutCirc',
      duration: 1500,
      delay: function(el, i) { return i * 100 },
      direction: 'alternate',
      loop: 1,
      loopComplete: function(anim) {
          if(first_loop){
              anime({
            targets: 'svg path',
            fill:['rgba(0,0,0,0)', 'rgba(0,158,209,1)'],
            easing: 'linear',
            // complete: function(anim) {
            //     anime({
            //       targets: 'svg path',
            //       fill: ['rgba(0,158,209,1)', 'rgba(88,56,149,1)', '#cc0000'],
            //       direction: 'alternate',
            //       easing: 'linear',
            //       delay: 5000,
            //       duration: 24000,
            //       loop: true
            //     })
            // }
          });
          first_loop=false
          }

      }
    });

});
