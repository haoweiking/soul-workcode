(function() {
    $(".btn-action").click(function(){
      var id = $(this).data("id"),
          action_url = $(this).data("url"),
          confirm_msg = $(this).data("confirm"),
          success_msg = $(this).data("success"),
          action = $(this).data("action");

        alertify.okBtn("确定")
          .cancelBtn("放弃")
          .confirm(confirm_msg, function () {
            $.post(action_url, {"action": action, "id": id}, function(data){
              if("status" in data && data['status'] == "ok") {
                toastr.success(success_msg, "", {
                  "positionClass": "toast-top-center",
                  "timeOut": 1000
                });

                setTimeout(function(){
                  location.reload();
                }, 1100);
              }
            }, "json").fail(function(e){
              console.log(e);
            });
        }, function() {
            // user clicked "cancel"
        });
    }); 
})()
