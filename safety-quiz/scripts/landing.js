document.addEventListener("DOMContentLoaded", function(event) {
    $('#btnClick').on('click', function () {
        console.log('button Clicked!')
        if ($('#1').css('display') != 'none') {
            $('#2').html('Here is my dynamic content').show().siblings('div').hide();
        } else if ($('#2').css('display') != 'none') {
            $('#1').show().siblings('div').hide();
        }
    });
    console.log('Hello World')
})