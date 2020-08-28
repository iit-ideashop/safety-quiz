//Javascript functions for reservation select boxes

function updateDate(e) {
    //reset select boxes when date changes in myCalendar
    $('#reservation_type').val('');
    $('#start_times').attr('disabled', true).val('');
    $('#end_times').attr('disabled', true).val('');
    $('#extra-people').attr('hidden', true);
    $('.auto-email').remove();
}

function updateReservationType(e) {
    $('#start_times').attr('disabled', true).val('');
    $('#start_times>.auto-start').remove();
    $('#end_times').attr('disabled', true).val('');
    $('#end_times>.auto-end').remove();
    $('#extra-people').attr('hidden', true);
    $('.auto-email').remove();

    let type_id = $('#reservation_type').val();
    let date = $('#current-date').val();

    if (type_id && type_id !== 'none') {
        $.getJSON('reservations/api/type', {type_id: type_id},function (data) {
            if (typeof data !== 'undefined' && data !== null) {
                var emailList = document.getElementById('extra-people');
                if (data['capacity'] > 1) {
                    emailList.removeAttribute('hidden');
                    for (let i = 1; i < data['capacity']; i++) {
                        var newInput = document.createElement('div');
                        newInput.innerHTML = '<input class="auto-email" type="email" id="user' + i + '" name="user' + i + '" value="" placeholder="Optional">' + '\n' +
                            '<small><label for="user' + i + '" name="user' + i + '" id="user' + i + 'help" class="form-text auto-email"></label></small>';
                        emailList.appendChild(newInput);
                    }
                }
            }
        })
        $.getJSON('reservations/api/start_times',{type_id: type_id, date: date},function (data) {
            if (data.length > 0) {
                let startList = $('#start_times').removeAttr('disabled');
                for (let x of data) {
                    startList.append('<option class="auto-start" value="' + x.date + ' ' + x.time + '">' + x.time + '</option>');
                }
            }
            console.log('Retrieved start times for reservation type ' + type_id);
        })
    }
}

function checkEmail(event) {
    if (event['currentTarget'] && event['currentTarget']['validity']['valid'] && event['currentTarget']['value'] !== '') {
        let label = document.getElementById(event['currentTarget']['labels'][0]['id']);
        if (event['currentTarget']['value'].includes('iit.edu')) {
            $.getJSON('reservations/api/checkEmail',{'email': event['currentTarget']['value']},function (data) {
                if (typeof data !== 'undefined' && data !== null) {
                    if (data['valid'] === true) {
                        label.textContent = data['reason'];
                        label.style.color = 'green';
                    }
                    else if (data['valid'] === false) {
                        label.textContent = data['reason'];
                        label.style.color = 'red';
                    }
                }
                else {
                   label.textContent = "Error: Invalid response from server.";
                   label.style.color = 'red';
                }
            });
        }
        else {
            label.textContent = "Not an IIT Email";
            label.style.color = 'red';
        }
    }
    else if (event['currentTarget']['value'] == '') {
        let label = document.getElementById(event['currentTarget']['labels'][0]['id']);
        label.textContent = "";
    }
}

function updateReservationStart(e) {
    $('#end_times').attr('disabled', true).val('');
    $('#end_times>.auto-end').remove();

    let type_id = $('#reservation_type').val();
    let start_time = $('#start_times').val();

    if (start_time && start_time !== 'none') {
        $.getJSON('reservations/api/end_times',{type_id:type_id, start_time:start_time}, function (data) {
            if (data.length > 0) {
                let endList = $('#end_times').removeAttr('disabled');
                for (let x of data) {
                    endList.append('<option class="auto-end" value="' + x.date + ' ' + x.time + '">' + x.time + '</option>');
                }
            }
            console.log('Retrieved end times for reservation type ' + type_id + 'starting at ' + start_time);
        })
    }
}

$(function() {
    $('#reservation_type').val('').change(updateReservationType);
    $('#start_times').val('').change(updateReservationStart);
    $(document).on('change',"input[type='email']",checkEmail);
    $('document').ready(updateDate());
});