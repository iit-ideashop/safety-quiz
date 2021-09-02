var tag = document.createElement('script');
var elem = document.querySelector('#video_data')
var captions = false;
console.log(elem)
      tag.src = "https://www.youtube.com/iframe_api";
      const progress = document.getElementById("vid_progress");
      var firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
      var vid_id=elem.getAttribute('data-video-path')
      var video_duration =elem.getAttribute('data-video-length');
      var player;
      function onYouTubeIframeAPIReady() {
        player = new YT.Player('player', {
            width: '100%',
            height: '100%',
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
      }

      function toggleCaptions() {
          if (captions){
              player.loadModule("captions");
          }
          else {
              player.unloadModule("captions");
          }
          captions = !captions;
      }

      function progressLoop() {
          setInterval(function() {
              progress.value = Math.round((player.getCurrentTime() / video_duration) * 100)
              progress.innerHTML = progress.value + '%';
          })
      }


      function onPlayerStateChange(event) {
          if (event.data === YT.PlayerState.PAUSED) {
          }
          if (event.data === YT.PlayerState.PLAYING) {
              player.setVolume(100);
              progressLoop();

          }
          if (event.data === YT.PlayerState.ENDED) {

                    var form = document.createElement('form');
                    document.body.appendChild(form);
                    form.method = 'post';
                    form.action = '';
                    var input = document.createElement('sid');
                    input.type = 'hidden';
                    input.name = 'sid';
                    input.value = { session:['sid'] };
                    form.appendChild(input);
                    form.submit();
                }
          //}
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
