$(document).ready(function() {
    $('#a_myboards').click(function() {
        $('#myboards').toggle();
        $('#a_myboards').toggleClass('open').toggleClass('closed');
        if($('#a_myboards').is(".open")) {
            $.cookie('a_myboards', '1', {path: '/'});
        } else {
            $.cookie('a_myboards', '0', {path: '/'});
        }
    });

    $('#a_favorites').click(function() {
        $('#favorites').toggle();
        $('#a_favorites').toggleClass('open').toggleClass('closed');
        if($('#a_favorites').is(".open")) {
            $.cookie('a_favorites', '1', {path: '/'});
        } else {
            $.cookie('a_favorites', '0', {path: '/'});
        }
    });

    if($.cookie('a_myboards') == '0') {
        $('#myboards').hide();
        $('#a_myboards').removeClass('open').addClass('closed');
    }

    if($.cookie('a_favorites') == '0') {
        $('#favorites').hide();
        $('#a_favorites').removeClass('open').addClass('closed');
    }
});
