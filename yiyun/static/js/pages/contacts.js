/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
(function(document, window, $) {
  'use strict';

  function showMsg(msg, type, cb) {
    toastr.info(msg);
    setTimeout(function() {
      if (cb instanceof Function) {
        cb();
      }
    }, 500);
  }

  function handleXhrError(xhr, cb) {
    showMsg('操作失败', 'info', function() {
      if (cb instanceof Function) {
        cb();
      }
    });
  }

  window.AppContacts = App.extend({
    handleAction: function() {

      var actionBtn = $('.site-action').actionBtn().data('actionBtn');
      var $selectable = $('[data-selectable]');

      $('.site-action-toggle', '.site-action').on('click', function(e) {
        var $selected = $selectable.asSelectable('getSelected');

        if ($selected.length === 0) {
          $('#addUserForm').modal('show');
          e.stopPropagation();
        }
      });

      $('[data-action="trash"]', '.site-action').on('click', function() {
        console.log('trash');
      });

      $('[data-action="folder"]', '.site-action').on('click', function() {
        console.log('folder');
      });

      $selectable.on('asSelectable::change', function(e, api, checked) {
        if (checked) {
          actionBtn.show();
        } else {
          actionBtn.hide();
        }
      });
    },

    handleEdit: function() {
      $(document).on('click', '[data-toggle=edit]', function() {
        var $button = $(this),
          $panel = $button.parents('.slidePanel'),
          $form = $panel.find('.user-info');

        $button.toggleClass('active');
        $form.toggleClass('active');
      });

      $(document).on('slidePanel::afterLoad', function(e, api) {
        $.components.init('material', api.$panel);
      });

      // 用户信息被修改后保存用户的修改
      $(document).on('change', '.user-info .form-group', function(e) {
        var $input = $(this).find('input');
        var $span = $(this).siblings('span');

        // select 的情况 (分组)
        if ($input.length === 0) {
          $input = $(this).find('select');
        }

        var $userInfo = $input.parents('.user-info');
        var memberId = $userInfo.data('member_id');
        var key = $input.data('key');
        var newValue = $input.val();

        if ($input[0].tagName === 'INPUT') {
          var showValue = $input.data('show_value');
        } else {
          var showValue = $input.find('option:selected').data('show_value');
        }

        if (!showValue) {
          showValue = newValue;
        }

        var updateParam = {
          member_id: memberId
        };
        updateParam[key] = newValue;

        $span.html(showValue);
        $.post(
          window.yiyun.apis.club_member_edit_xhr,
          updateParam

        ).done(function(res) {
          showMsg('信息修改成功', 'info', function() {
            window.location.reload();
          });

        }).fail(function(xhr) {
          handleXhrError(xhr);

        });
      });

    },

    // 分组列表
    handleListItem: function() {
      $('#addLabelToggle').on('click', function(e) {
        $('#addLabelForm').modal('show');
        e.stopPropagation();
      });

      $(document).on('click', '[data-tag=list-delete]', function(e) {
        var groupName = $(e.currentTarget).data('group_name');

        bootbox.dialog({
          message: "是否确定删除该分组？删除后，该分组中的成员都会恢复到默认分组。",
          buttons: {
            success: {
              label: "删除",
              className: "btn-danger",
              callback: function() {
                $.post(
                  window.yiyun.apis.club_member_groups_delete_xhr,
                  { group_name: groupName }

                ).done(function(res) {
                  $(e.target).closest('.list-group-item').remove();

                }).fail(function(xhr) {
                  handleXhrError(xhr);
                });
              }
            }
          }
        });
      });
    },

    // 添加分组
    handleAddLabel: function() {
      var $addLabelForm = $('#addLabelForm');
      var $lablenameInput = $(addLabelForm).find('input[name=lablename]');

      $addLabelForm.on('click', 'a.submit', function(e) {
        var groupName = $lablenameInput.val();

        if (groupName) {
          $.post(
            window.yiyun.apis.club_member_groups_xhr,
            { group_name: groupName }

          ).done(function(res) {
            showMsg('添加分组成功', 'info', function() {
              window.location.reload();
            });

          }).fail(function(xhr) {
            handleXhrError(xhr);
          });

        } else {
          showMsg('分组名称不能是空!', 'info');
        }
      })
    },

    handleAddUser: function() {
      var $addUserForm = $('#addUserForm');

      var $nameInput = $addUserForm.find('input[name="name"]');
      var $phoneInput = $addUserForm.find('input[name="phone"]');
      var $emailInput = $addUserForm.find('input[name="email"]');
      var $balanceInput = $addUserForm.find('input[name="balance"]');

      $addUserForm.on('click', '.submit', function(e) {
        var name = $nameInput.val();
        var phone = $phoneInput.val();
        var email = $emailInput.val();
        var balance = $balanceInput.val();

        if (name && phone && email && balance) {
          $.post(
            window.yiyun.apis.club_members_add_xhr,
            {
              nick: name,
              mobile: phone,
              email: email,
              balance: balance
            }

          ).done(function(res) {
            showMsg('添加成员成功', 'info', function() {
              window.location.reload();
            });

          }).fail(function(xhr) {
            showMsg('添加成员失败', 'info');

          });

        } else {
          showMsg('请填写完整的信息', 'info');
        }
      });
    },

    run: function(next) {
      this.handleAction();
      this.handleEdit();
      this.handleListItem();
      this.handleAddLabel();
      this.handleAddUser();

      $('#addlabelForm').modal({
        show: false
      });

      $('#addUserForm').modal({
        show: false
      });

      next();
    }
  });

  $(document).ready(function() {
    AppContacts.run();
  });
})(document, window, jQuery);
