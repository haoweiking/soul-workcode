/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
(function(document, window, $) {
  'use strict';

  window.AppCalendar = App.extend({
    handlePagination: function() {
    },
    run: function() {
      this.items = [];
      // this.handlePagination();
    }
  });

  $(document).ready(function() {
    AppCalendar.run();

    $("#search-form select").change(function(){
        $(this).parents("form").submit();
    });

    $(".btn-action").click(function(){
      var activity_id = $(this).data("id"),
          action_url = $(this).data("url"),
          confirm_msg = $(this).data("confirm"),
          success_msg = $(this).data("success"),
          action = $(this).data("action");

        alertify.okBtn("确定")
          .cancelBtn("放弃")
          .confirm(confirm_msg, function () {
            $.post(action_url, {"action": action}, function(data){
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

  });
})(document, window, jQuery);
