var i = 0;
function move() {
  if (i === 0) {
    i = 1;
    var elem = document.getElementById("video-bar-progress");
    var width = 10;
    var id = setInterval(frame, 10);
    function frame() {
      if (width >= 100) {
        clearInterval(id);
        i = 0;
      } else {
        width++;
        elem.style.width = width + "%";
        elem.innerHTML = width  + "%";
      }
    }
  }
}

var tag = document.createElement('script');
      tag.src = "https://www.youtube.com/iframe_api";
      var firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
      let vid_id='ldCBbAQkgfs';

      var player;
      function onYouTubeIframeAPIReady() {
        player = new YT.Player('player', {
            width: '75%',
            height: '500px',
            videoId: vid_id,
            playerVars: {
                'controls': 0,
                'cc_lang_pref': 1,
                'cc_load_policy': 1,
                'disablekb': 1,
                'rel': 0,
                'modestbranding': 1,
            },
            events: {
                'onStateChange': onPlayerStateChange
            }
        });
        let duration=player.getDuration();
      }
          /*var Progress = (function ($) {

        var Move = function () {
            if (i === 0) {
                i = 1;
                var elem = document.getElementById("video-bar-progress");
                var width = 0;
                var id = setInterval(frame, 10);

                function frame() {
                    if (width >= 100) {
                        clearInterval(id);
                        i = 0;
                    } else {
                        width++;
                        elem.style.width = width + "%";
                        elem.innerHTML = width + "%";
                    }
                }
            }
        };
        return {
            Move:Move
        };
    })(jQuery);*/


      function onPlayerStateChange(event) {
          if (event.data === YT.PlayerState.PAUSED) {
            CountDown.Pause();
          }
          if (event.data === YT.PlayerState.PLAYING) {
              Progress.Move();
              if (CountDown.IsStarted() === false) {
                  CountDown.Start(video_time_seconds*1000);
              }
              else {

              }
          }
          if (event.data === YT.PlayerState.ENDED) {
                CountDown.Pause();
                var secondsRemaining = CountDown.TimeRemaining();
                if (secondsRemaining > 10) {
                    alert("It looks like you may have tried to speed through the video. Please refresh the page to restart this online training.");
                }
                else {
                    var form = document.createElement('form');
                    document.body.appendChild(form);
                    form.method = 'post';
                    form.action = "{{ url_for('video.COVID') }}";
                    var input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = 'sid';
                    input.value = { session:['sid'] };
                    form.appendChild(input);
                    form.submit();
                }
          }
      }

      function stopVideo() {
        player.stopVideo();
      }

      // Set the name of the hidden property and the change event for visibility
      var hidden, visibilityChange;
      if (typeof document.hidden !== "undefined") { // Opera 12.10 and Firefox 18 and later support
          hidden = "hidden";
          visibilityChange = "visibilitychange";
      } else if (typeof document.msHidden !== "undefined") {
          hidden = "msHidden";
          visibilityChange = "msvisibilitychange";
      } else if (typeof document.webkitHidden !== "undefined") {
          hidden = "webkitHidden";
          visibilityChange = "webkitvisibilitychange";
      }

      var videoElement = document.getElementById("player");

      // If the page is hidden, pause the video;
      // if the page is shown, play the video
      function handleVisibilityChange() {
          if (document[hidden]) {
              player.pauseVideo();
          } else {
          }
      }

      // Warn if the browser doesn't support addEventListener or the Page Visibility API
      if (typeof document.addEventListener === "undefined" || hidden === undefined) {
          console.log("This demo requires a browser, such as Google Chrome or Firefox, that supports the Page Visibility API.");
      } else {
          // Handle page visibility change
          document.addEventListener(visibilityChange, handleVisibilityChange, false);

          // When the video pauses, set the title.
          // This shows the paused
          videoElement.addEventListener("pause", function(){
              document.title = 'Paused';
          }, false);

          // When the video plays, set the title.
          videoElement.addEventListener("play", function(){
              document.title = 'Playing';
          }, false);

      }

      //timer
      var CountDown = (function ($) {
          // Length ms
          var TimeOut = 10000;
          // Interval ms
          var TimeGap = 1000;

          var CurrentTime = ( new Date() ).getTime();
          var EndTime = ( new Date() ).getTime() + TimeOut;

          var GuiTimer = $('#countdown');

          var Started = false;
          var Running = true;

          var UpdateTimer = function() {
              // Run till timeout
              if( CurrentTime + TimeGap < EndTime ) {
                  setTimeout( UpdateTimer, TimeGap );
              }
              // Countdown if running
              if( Running ) {
                  CurrentTime += TimeGap;
                  if( CurrentTime >= EndTime ) {
                      GuiTimer.css('color','red');
                  }
              }
              // Update Gui
              var Time = new Date();
              Time.setTime( EndTime - CurrentTime );
              var Minutes = Time.getMinutes();
              var Seconds = Time.getSeconds();

              GuiTimer.html(
                  (Minutes < 10 ? '0' : '') + Minutes
                  + ':'
                  + (Seconds < 10 ? '0' : '') + Seconds );
          };

          var Pause = function() {
              Running = false;
          };

          var Resume = function() {
              Running = true;
          };

          var Start = function( Timeout ) {
              TimeOut = Timeout;
              CurrentTime = ( new Date() ).getTime();
              EndTime = ( new Date() ).getTime() + TimeOut;
              Started = true;
              UpdateTimer();
          };

          var IsStarted = function() {
              return Started;
          };

          var TimeRemaining = function() {
                var Time = new Date();
                Time.setTime( EndTime - CurrentTime );
                var secondsRemaining = (Time.getMinutes()*60)+(Time.getSeconds())
                console.log(secondsRemaining);
                return secondsRemaining;
          }

          return {
              Pause: Pause,
              Resume: Resume,
              Start: Start,
              IsStarted: IsStarted,
              TimeRemaining, TimeRemaining
          };
      })(jQuery);