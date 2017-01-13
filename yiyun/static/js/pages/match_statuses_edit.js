(function() {

var $deletePhotoKeysInput = $('input[name="delete-photo-keys"]')
var $oldPhotos = $('.old-photos')
var deletePhotoKeys = []

$oldPhotos.on('click', '.photo', function(e) {
  var $img = $(e.currentTarget)
  var photoKey = $img.data('key')

  if ($img.hasClass('delete-photo')) {
    $img.removeClass('delete-photo')
    var indexOfKey = deletePhotoKeys.indexOf(photoKey)
    if (indexOfKey >= 0) {
      deletePhotoKeys.splice(indexOfKey, 1)
    }
  } else {
    deletePhotoKeys.push(photoKey)
    $img.addClass('delete-photo')
  }

  $deletePhotoKeysInput.val(deletePhotoKeys.join(','))
})

})()
