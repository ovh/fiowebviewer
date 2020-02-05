function sendRenamingRequest(resultid, newName){
    return $.ajax({
        type: 'PUT',
        dataType: 'json',
        url: `/api/${resultid}`,
        contentType: 'application/json',
        data: JSON.stringify({ name: newName }),
    });
}

function declareEditPopup(resultid){
    $( "#bn-edit" ).click(function() {
        $( "p#change-name" ).text('');
        $( "#edit-popup" ).toggle();
    });
    $( "#bn-edit-close" ).click(function() {
        $( "#edit-popup" ).toggle();
    });
    $( "#change-name" ).click(function() {
        var newName = $( "#name" ).val()
        sendRenamingRequest(resultid, newName).catch(function(e){
            if(e.status == 200){
                window.location.reload(true);
            }
            else {
                $( "p#change-name" ).text(`Error, backed responded with ${e.status}`);
            }
        });
    });
}
