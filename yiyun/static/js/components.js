/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("alertify", {
  mode: "api",
  defaults: {
    type: "alert",
    delay: 5000,
    theme: 'bootstrap'
  },
  api: function() {
    if (typeof alertify === "undefined") return;

    var defaults = $.components.getDefaults("alertify");

    alertify.theme("bootstrap");

    $(document).on('click.site.alertify', '[data-plugin="alertify"]', function() {
      var $this = $(this),
        options = $.extend(true, {}, defaults, $this.data());

      if (options.labelOk) {
        options.okBtn = options.labelOk;
      }

      if (options.labelCancel) {
        options.cancelBtn = options.labelCancel;
      }

      if (typeof options.delay !== 'undefined') {
        alertify.delay(options.delay);
      }

      if (typeof options.theme !== 'undefined') {
        alertify.theme(options.theme);
      }

      if (typeof options.cancelBtn !== 'undefined') {
        alertify.cancelBtn(options.cancelBtn);
      }

      if (typeof options.okBtn !== 'undefined') {
        alertify.okBtn(options.okBtn);
      }

      if (typeof options.placeholder !== 'undefined') {
        alertify.delay(options.placeholder);
      }

      if (typeof options.defaultValue !== 'undefined') {
        alertify.delay(options.defaultValue);
      }

      if (typeof options.maxLogItems !== 'undefined') {
        alertify.delay(options.maxLogItems);
      }

      if (typeof options.closeLogOnClick !== 'undefined') {
        alertify.delay(options.closeLogOnClick);
      }

      switch (options.type) {
        case "alert":
          alertify.alert(options.alertMessage);
          break;
        case "confirm":
          alertify.confirm(options.confirmTitle, function() {
            alertify.success(options.successMessage);
          }, function() {
            alertify.error(options.errorMessage);
          });
          break;
        case "prompt":
          alertify.prompt(options.promptTitle, function(str, ev) {
            var message = options.successMessage.replace('%s', str);
            alertify.success(message);
          }, function(ev) {
            alertify.error(options.errorMessage);
          });
          break;
        case "log":
          alertify.log(options.logMessage);
          break;
        case "success":
          alertify.success(options.successMessage);
          break;
        case "error":
          alertify.error(options.errorMessage);
          break;
      }
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("animate-list", {
  mode: 'init',

  defaults: {
    child: '.panel',
    duration: 250,
    delay: 50,
    animate: 'scale-up',
    fill: 'backwards'
  },

  init: function() {
    var self = this;

    $('[data-plugin=animateList]').each(function() {
      var $this = $(this),
        options = $.extend({}, self.defaults, $this.data(), true);


      var animatedBox = function($el, opts) {
        this.options = opts;
        this.$children = $el.find(opts.child);
        this.$children.addClass('animation-' + opts.animate);
        this.$children.css('animation-fill-mode', opts.fill);
        this.$children.css('animation-duration', opts.duration + 'ms');

        var delay = 0,
          self = this;

        this.$children.each(function() {

          $(this).css('animation-delay', delay + 'ms');
          delay += self.options.delay;
        });
      };

      animatedBox.prototype = {
        run: function(type) {
          var self = this;
          this.$children.removeClass('animation-' + this.options.animate);
          if (typeof type !== 'undefined') this.options.animate = type;
          setTimeout(function() {
            self.$children.addClass('animation-' + self.options.animate);
          }, 0);
        }
      };

      $this.data('animateList', new animatedBox($this, options));
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("animsition", {
  mode: "manual",
  defaults: {
    inClass: 'fade-in',
    outClass: 'fade-out',
    inDuration: 800,
    outDuration: 500,
    linkElement: '.animsition-link',
    loading: true,
    loadingParentElement: "body",
    loadingClass: "loader",
    loadingType: "default",
    timeout: false,
    timeoutCountdown: 5000,
    onLoadEvent: true,
    browser: ['animation-duration', '-webkit-animation-duration'],
    overlay: false,
    // random: true,
    overlayClass: 'animsition-overlay-slide',
    overlayParentElement: "body",

    inDefaults: [
      'fade-in',
      'fade-in-up-sm', 'fade-in-up', 'fade-in-up-lg',
      'fade-in-down-sm', 'fade-in-down', 'fade-in-down-lg',
      'fade-in-left-sm', 'fade-in-left', 'fade-in-left-lg',
      'fade-in-right-sm', 'fade-in-right', 'fade-in-right-lg',
      // 'overlay-slide-in-top', 'overlay-slide-in-bottom', 'overlay-slide-in-left', 'overlay-slide-in-right',
      'zoom-in-sm', 'zoom-in', 'zoom-in-lg'
    ],
    outDefaults: [
      'fade-out',
      'fade-out-up-sm', 'fade-out-up', 'fade-out-up-lg',
      'fade-out-down-sm', 'fade-out-down', 'fade-out-down-lg',
      'fade-out-left-sm', 'fade-out-left', 'fade-out-left-lg',
      'fade-out-right-sm', 'fade-out-right', 'fade-out-right-lg',
      // 'overlay-slide-out-top', 'overlay-slide-out-bottom', 'overlay-slide-out-left', 'overlay-slide-out-right'
      'zoom-out-sm', 'zoom-out', 'zoom-out-lg'
    ]
  },

  init: function(context, callback) {
    var options = $.components.getDefaults("animsition");

    if (options.random) {
      var li = options.inDefaults.length,
        lo = options.outDefaults.length;

      var ni = parseInt(li * Math.random(), 0),
        no = parseInt(lo * Math.random(), 0);

      options.inClass = options.inDefaults[ni];
      options.outClass = options.outDefaults[no];
    }

    var $this = $(".animsition", context);

    $this.animsition(options);

    $("." + options.loadingClass).addClass('loader-' + options.loadingType);

    if ($this.animsition('supportCheck', options)) {
      if ($.isFunction(callback)) {
        $this.one('animsition.end', function() {
          callback.call();
        });
      }

      return true;
    } else {
      if ($.isFunction(callback)) {
        callback.call();
      }
      return false;
    }
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("breadcrumb", {
  mode: "init",
  defaults: {
    namespace: "breadcrumb"
  },
  init: function(context) {
    if (!$.fn.asBreadcrumbs) return;
    var defaults = $.components.getDefaults("breadcrumb");

    $('[data-plugin="breadcrumb"]', context).each(function() {
      var options = $.extend({}, defaults, $(this).data());

      $(this).asBreadcrumbs(options);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("paginator", {
  mode: "init",
  defaults: {
    namespace: "pagination",
    currentPage: 1,
    itemsPerPage: 10,
    disabledClass: "disabled",
    activeClass: "active",

    visibleNum: {
      0: 3,
      480: 5
    },

    tpl: function() {
      return '{{prev}}{{lists}}{{next}}';
    },

    components: {
      prev: {
        tpl: function() {
          return '<li class="' + this.namespace + '-prev"><a href="javascript:void(0)"><span class="icon wb-chevron-left-mini"></span></a></li>';
        }
      },
      next: {
        tpl: function() {
          return '<li class="' + this.namespace + '-next"><a href="javascript:void(0)"><span class="icon wb-chevron-right-mini"></span></a></li>';
        }
      },
      lists: {
        tpl: function() {
          var lists = '',
            remainder = this.currentPage >= this.visible ? this.currentPage % this.visible : this.currentPage;
          remainder = remainder === 0 ? this.visible : remainder;
          for (var k = 1; k < remainder; k++) {
            lists += '<li class="' + this.namespace + '-items" data-value="' + (this.currentPage - remainder + k) + '"><a href="javascript:void(0)">' + (this.currentPage - remainder + k) + '</a></li>';
          }
          lists += '<li class="' + this.namespace + '-items ' + this.classes.active + '" data-value="' + this.currentPage + '"><a href="javascript:void(0)">' + this.currentPage + '</a></li>';
          for (var i = this.currentPage + 1, limit = i + this.visible - remainder - 1 > this.totalPages ? this.totalPages : i + this.visible - remainder - 1; i <= limit; i++) {
            lists += '<li class="' + this.namespace + '-items" data-value="' + i + '"><a href="javascript:void(0)">' + i + '</a></li>';
          }

          return lists;
        }
      }
    }
  },
  init: function(context) {
    if (!$.fn.asPaginator) return;

    var defaults = $.components.getDefaults("paginator");

    $('[data-plugin="paginator"]', context).each(function() {
      var $this = $(this),
        options = $this.data();

      var total = $this.data("total");

      options = $.extend({}, defaults, options);
      $this.asPaginator(total, options);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("pieProgress", {
  mode: "init",
  defaults: {
    namespace: "pie-progress",
    speed: 30,
    classes: {
      svg: "pie-progress-svg",
      element: "pie-progress",
      number: "pie-progress-number",
      content: "pie-progress-content"
    }
  },
  init: function(context) {
    if (!$.fn.asPieProgress) return;

    var defaults = $.components.getDefaults("pieProgress");

    $('[data-plugin="pieProgress"]', context).each(function() {
      var $this = $(this),
        options = $this.data();

      options = $.extend(true, {}, defaults, options);

      $this.asPieProgress(options);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("progress", {
  mode: "init",
  defaults: {
    bootstrap: true,

    onUpdate: function(n) {
      var per = (n - this.min) / (this.max - this.min);
      if (per < 0.5) {
        this.$target.addClass('progress-bar-success').removeClass('progress-bar-warning progress-bar-danger');
      } else if (per >= 0.5 && per < 0.8) {
        this.$target.addClass('progress-bar-warning').removeClass('progress-bar-success progress-bar-danger');
      } else {
        this.$target.addClass('progress-bar-danger').removeClass('progress-bar-success progress-bar-warning');
      }
    },

    labelCallback: function(n) {
      var label;
      var labelType = this.$element.data("labeltype");

      if (labelType === "percentage") {
        var percentage = this.getPercentage(n);
        label = percentage + '%';
      } else if (labelType === "steps") {
        var total = this.$element.data("totalsteps");
        if (!total) {
          total = 10;
        }
        var step = Math.round(total * (n - this.min) / (this.max - this.min));
        label = step + ' / ' + total;
      } else {
        label = n;
      }

      if (this.$element.parent().hasClass('contextual-progress')) {
        this.$element.parent().find('.progress-label').html(label);
      }

      return label;
    }
  },

  init: function(context) {
    if (!$.fn.asProgress) return;

    var defaults = $.components.getDefaults("progress");

    $('[data-plugin="progress"]', context).each(function() {
      var $this = $(this),
        options = $this.data();

      options = $.extend({}, defaults, options);
      $this.asProgress(options);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("scrollable", {
  mode: "init",
  defaults: {
    namespace: "scrollable",
    contentSelector: "> [data-role='content']",
    containerSelector: "> [data-role='container']"
  },
  init: function(context) {
    if (!$.fn.asScrollable) return;
    var defaults = $.components.getDefaults("scrollable");

    $('[data-plugin="scrollable"]', context).each(function() {
      var options = $.extend({}, defaults, $(this).data());

      $(this).asScrollable(options);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("datepicker", {
  mode: "default",
  defaults: {
    autoclose: true,
    language: "zh-CN"
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("maxlength", {
  mode: "default",
  defaults: {}
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("sweetalert", {
  mode: "api",
  api: function() {
    if (typeof swal === "undefined") return;

    var defaults = $.components.getDefaults("sweetalert");

    $(document).on('click.site.sweetalert', '[data-plugin="sweetalert"]', function() {
      var options = $.extend(true, {}, defaults, $(this).data());

      swal(options);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("tokenfield", {
  mode: "default",
  defaults: {}
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("TouchSpin", {
  mode: "default",
  defaults: {
    verticalupclass: "wb-plus",
    verticaldownclass: "wb-minus",
    buttondown_class: "btn btn-outline btn-default",
    buttonup_class: "btn btn-outline btn-default"
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("treeview", {
  mode: "init",
  defaults: {
    injectStyle: false,
    expandIcon: "icon wb-plus",
    collapseIcon: "icon wb-minus",
    emptyIcon: "icon",
    nodeIcon: "icon wb-folder",
    showBorder: false,
    // color: undefined, // "#000000",
    // backColor: undefined, // "#FFFFFF",
    borderColor: $.colors("blue-grey", 200),
    onhoverColor: $.colors("blue-grey", 100),
    selectedColor: "#ffffff",
    selectedBackColor: $.colors("primary", 600),

    searchResultColor: $.colors("primary", 600),
    searchResultBackColor: "#ffffff"
  },
  init: function(context) {
    if (!$.fn.treeview) return;

    var defaults = $.components.getDefaults("treeview");

    $('[data-plugin="treeview"]', context).each(function() {
      var $this = $(this);
      var options = $this.data();
      if (typeof options.source === "string" && $.isFunction(window[options.source])) {
        options.data = window[options.source]();
        delete options.source;
      } else if ($.isFunction(options.souce)) {
        options.data = options.source();
        delete options.source;
      }

      options = $.extend(true, {}, defaults, options);
      $this.treeview(options);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("buttons", {
  mode: "api",
  defaults: {},
  api: function() {
    $(document).on('click.site.loading', '[data-loading-text]', function() {
      var $btn = $(this),
        text = $btn.text(),
        i = 20,
        loadingText = $btn.data('loadingText');

      $btn.text(loadingText + '(' + i + ')').css('opacity', '.6');

      var timeout = setInterval(function() {
        $btn.text(loadingText + '(' + (--i) + ')');
        if (i === 0) {
          clearInterval(timeout);
          $btn.text(text).css('opacity', '1');
        }
      }, 1000);
    });

    $(document).on('click.site.morebutton', '[data-more]', function() {
      var $target = $($(this).data('more'));
      $target.toggleClass('show');
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("dataTable", {
  defaults: {
    responsive: true,
    language: {
      "sSearchPlaceholder": "Search..",
      "lengthMenu": "_MENU_",
      "search": "_INPUT_",
      "paginate": {
        "previous": '<i class="icon wb-chevron-left-mini"></i>',
        "next": '<i class="icon wb-chevron-right-mini"></i>'
      }
    }
  },
  api: function() {
    if (!$.fn.dataTable) return;

    if ($.fn.dataTable.TableTools) {
      // Set the classes that TableTools uses to something suitable for Bootstrap
      $.extend(true, $.fn.dataTable.TableTools.classes, {
        "container": "DTTT btn-group btn-group pull-left",
        "buttons": {
          "normal": "btn btn-outline btn-default",
          "disabled": "disabled"
        },
        "print": {
          "body": "site-print DTTT_Print"
        }
      });
    }
  },
  init: function(context) {
    if (!$.fn.dataTable) return;

    var defaults = $.components.getDefaults("dataTable");

    $('[data-plugin="dataTable"]', context).each(function() {
      var options = $.extend(true, {}, defaults, $(this).data());

      $(this).dataTable(options);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("datepair", {
  mode: "default",
  defaults: {
    startClass: 'datepair-start',
    endClass: 'datepair-end',
    timeClass: 'datepair-time',
    dateClass: 'datepair-date'
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("formatter", {
  mode: "init",
  defaults: {
    persistent: true
  },

  init: function(context) {
    if (!$.fn.formatter) return;

    var defaults = $.components.getDefaults("formatter"),
      browserName = navigator.userAgent.toLowerCase(),
      ieOptions;

    if (/msie/i.test(browserName) && !/opera/.test(browserName)) {
      ieOptions = {
        persistent: false
      };
    } else {
      ieOptions = {};
    }

    $('[data-plugin="formatter"]', context).each(function() {

      var options = $.extend({}, defaults, ieOptions, $(this).data());
      if (options.pattern) {
        options.pattern = options.pattern.replace(/\[\[/g, '{{').replace(/\]\]/g, '}}');
      }
      $(this).formatter(options);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("sortable", {
  defaults: {},
  mode: "default"
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("input-group-file", {
  api: function() {
    $(document).on("change", ".input-group-file [type=file]", function() {
      var $this = $(this);
      var $text = $(this).parents('.input-group-file').find('.form-control');
      var value = "";

      $.each($this[0].files, function(i, file) {
        value += file.name + ", ";
      });
      value = value.substring(0, value.length - 2);

      $text.val(value);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("appear", {
  defaults: {},
  api: function(context) {
    if (!$.fn.appear) return;

    $(document).on("appear", '[data-plugin="appear"]', function() {
      var $item = $(this),
        animate = $item.data("animate");

      if ($item.hasClass('appear-no-repeat')) return;
      $item.removeClass("invisible").addClass('animation-' + animate);

      if ($item.data("repeat") === false) {
        $item.addClass('appear-no-repeat');
      }
    });

    $(document).on("disappear", '[data-plugin="appear"]', function() {
      var $item = $(this),
        animate = $item.data("animate");

      if ($item.hasClass('appear-no-repeat')) return;

      $item.addClass("invisible").removeClass('animation-' + animate);
    });
  },

  init: function(context) {
    if (!$.fn.appear) return;

    var defaults = $.components.getDefaults("appear");

    $('[data-plugin="appear"]', context).appear(defaults);
    $('[data-plugin="appear"]', context).not(':appeared').addClass("invisible");
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("floatThead", {
  mode: "default",
  defaults: {
    top: function() {
      return $('.site-navbar').outerHeight();
    },
    position: 'absolute'
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("labelauty", {
  mode: "default",
  defaults: {
    same_width: true
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("placeholder", {
  mode: "init",
  init: function(context) {
    if (!$.fn.placeholder) return;

    $('input, textarea', context).placeholder();
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("strength", {
  mode: "default",
  defaults: {
    showMeter: true,
    showToggle: false,

    templates: {
      toggle: '<div class="checkbox-custom checkbox-primary show-password-wrap"><input type="checkbox" class="{toggleClass}" title="Show/Hide Password" id="show_password" /><label for="show_password">Show Password</label></div>',
      meter: '<div class="{meterClass}">{score}</div>',
      score: '<div class="{scoreClass}"></div>',
      main: '<div class="{containerClass}">{input}{meter}{toggle}</div>'
    },

    classes: {
      container: 'strength-container',
      status: 'strength-{status}',
      input: 'strength-input',
      toggle: 'strength-toggle',
      meter: 'strength-meter',
      score: 'strength-score'
    },

    scoreLables: {
      invalid: 'Invalid',
      weak: 'Weak',
      good: 'Good',
      strong: 'Strong'
    },

    scoreClasses: {
      invalid: 'strength-invalid',
      weak: 'strength-weak',
      good: 'strength-good',
      strong: 'strength-strong'
    }
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("timepicker", {
  mode: "default",
  defaults: {}
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("vectorMap", {
  mode: "default",
  defaults: {
    map: "world_mill_en",
    backgroundColor: '#fff',
    zoomAnimate: true,
    regionStyle: {
      initial: {
        fill: $.colors("primary", 600)
      },
      hover: {
        fill: $.colors("primary", 500)
      },
      selected: {
        fill: $.colors("primary", 800)
      },
      selectedHover: {
        fill: $.colors("primary", 500)
      }
    },
    markerStyle: {
      initial: {
        r: 8,
        fill: $.colors("red", 600),
        "stroke-width": 0
      },
      hover: {
        r: 12,
        stroke: $.colors("red", 600),
        "stroke-width": 0
      }
    }
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("ladda", {
  mode: "init",
  defaults: {
    timeout: 2000
  },
  init: function() {
    if (typeof Ladda === "undefined") return;

    var defaults = $.components.getDefaults("ladda");
    Ladda.bind('[data-plugin="ladda"]', defaults);
  }
});

$.components.register("laddaProgress", {
  mode: "init",
  defaults: {
    init: function(instance) {
      var progress = 0;
      var interval = setInterval(function() {
        progress = Math.min(progress + Math.random() * 0.1, 1);
        instance.setProgress(progress);

        if (progress === 1) {
          instance.stop();
          clearInterval(interval);
        }
      }, 200);
    }
  },
  init: function() {
    if (typeof Ladda === 'undefined') return;

    var defaults = $.components.getDefaults("laddaProgress");
    // Bind progress buttons and simulate loading progress
    Ladda.bind('[data-plugin="laddaProgress"]', defaults);
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("magnificPopup", {
  mode: "default",
  defaults: {
    type: "image",
    closeOnContentClick: true,
    image: {
      verticalFit: true
    }
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("matchHeight", {
  mode: "init",
  defaults: {},
  init: function(context) {
    if (typeof $.fn.matchHeight === "undefined") return;
    var defaults = $.components.getDefaults('matchHeight');

    $('[data-plugin="matchHeight"]', context).each(function() {
      var $this = $(this),
        options = $.extend(true, {}, defaults, $this.data()),
        matchSelector = $this.data('matchSelector');

      if (matchSelector) {
        $this.find(matchSelector).matchHeight(options);
      } else {
        $this.children().matchHeight(options);
      }

    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("multiSelect", {
  mode: "default",
  defaults: {}
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("nestable", {
  mode: "default"
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("panel", {
  api: function() {
    $(document).on('click.site.panel', '[data-toggle="panel-fullscreen"]', function(e) {
      e.preventDefault();
      var $this = $(this),
        $panel = $this.closest('.panel');

      var api = $panel.data('panel-api');
      api.toggleFullscreen();
    });

    $(document).on('click.site.panel', '[data-toggle="panel-collapse"]', function(e) {
      e.preventDefault();
      var $this = $(this),
        $panel = $this.closest('.panel');

      var api = $panel.data('panel-api');
      api.toggleContent();
    });

    $(document).on('click.site.panel', '[data-toggle="panel-close"]', function(e) {
      e.preventDefault();
      var $this = $(this),
        $panel = $this.closest('.panel');

      var api = $panel.data('panel-api');
      api.close();
    });

    $(document).on('click.site.panel', '[data-toggle="panel-refresh"]', function(e) {
      e.preventDefault();
      var $this = $(this);
      var $panel = $this.closest('.panel');

      var api = $panel.data('panel-api');
      var callback = $this.data('loadCallback');

      if ($.isFunction(window[callback])) {
        api.load(window[callback]);
      } else {
        api.load();
      }
    });
  },

  init: function(context) {
    $('.panel', context).each(function() {
      var $this = $(this);

      var isFullscreen = false;
      var isClose = false;
      var isCollapse = false;
      var isLoading = false;

      var $fullscreen = $this.find('[data-toggle="panel-fullscreen"]');
      var $collapse = $this.find('[data-toggle="panel-collapse"]');
      var $loading;
      var self = this;

      if ($this.hasClass('is-collapse')) {
        isCollapse = true;
      }

      var api = {
        load: function(callback) {
          var type = $this.data('loader-type');
          if (!type) {
            type = 'default';
          }

          $loading = $('<div class="panel-loading">' +
            '<div class="loader loader-' + type + '"></div>' +
            '</div>');

          $loading.appendTo($this);

          $this.addClass('is-loading');
          $this.trigger('loading.uikit.panel');
          isLoading = true;

          if ($.isFunction(callback)) {
            callback.call(self, this.done);
          }
        },
        done: function() {
          if (isLoading === true) {
            $loading.remove();
            $this.removeClass('is-loading');
            $this.trigger('loading.done.uikit.panel');
          }
        },
        toggleContent: function() {
          if (isCollapse) {
            this.showContent();
          } else {
            this.hideContent();
          }
        },

        showContent: function() {
          if (isCollapse !== false) {
            $this.removeClass('is-collapse');

            if ($collapse.hasClass('wb-plus')) {
              $collapse.removeClass('wb-plus').addClass('wb-minus');
            }

            $this.trigger('shown.uikit.panel');

            isCollapse = false;
          }
        },

        hideContent: function() {
          if (isCollapse !== true) {
            $this.addClass('is-collapse');

            if ($collapse.hasClass('wb-minus')) {
              $collapse.removeClass('wb-minus').addClass('wb-plus');
            }

            $this.trigger('hidden.uikit.panel');
            isCollapse = true;
          }
        },

        toggleFullscreen: function() {
          if (isFullscreen) {
            this.leaveFullscreen();
          } else {
            this.enterFullscreen();
          }
        },
        enterFullscreen: function() {
          if (isFullscreen !== true) {
            $this.addClass('is-fullscreen');

            if ($fullscreen.hasClass('wb-expand')) {
              $fullscreen.removeClass('wb-expand').addClass('wb-contract');
            }

            $this.trigger('enter.fullscreen.uikit.panel');
            isFullscreen = true;
          }
        },
        leaveFullscreen: function() {
          if (isFullscreen !== false) {
            $this.removeClass('is-fullscreen');

            if ($fullscreen.hasClass('wb-contract')) {
              $fullscreen.removeClass('wb-contract').addClass('wb-expand');
            }

            $this.trigger('leave.fullscreen.uikit.panel');
            isFullscreen = false;
          }
        },
        toggle: function() {
          if (isClose) {
            this.open();
          } else {
            this.close();
          }
        },
        open: function() {
          if (isClose !== false) {
            $this.removeClass('is-close');
            $this.trigger('open.uikit.panel');

            isClose = false;
          }
        },
        close: function() {
          if (isClose !== true) {

            $this.addClass('is-close');
            $this.trigger('close.uikit.panel');

            isClose = true;
          }
        }
      };

      $this.data('panel-api', api);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("peityBar", {
  mode: "init",
  defaults: {
    delimiter: ",",
    fill: [$.colors("primary", 400)],
    height: 22,
    max: null,
    min: 0,
    padding: 0.1,
    width: 44
  },
  init: function(context) {
    if (!$.fn.peity) return;

    var defaults = $.components.getDefaults("peityBar");

    $('[data-plugin="peityBar"]', context).each(function() {
      var $this = $(this),
        options = $this.data();

      if (options.skin) {
        if ($.colors(options.skin)) {
          var skinColors = $.colors(options.skin);
          defaults.fill = [skinColors[400]];
        }
      }

      options = $.extend(true, {}, defaults, options);

      $this.peity('bar', options);
    });
  }
});

$.components.register("peityDonut", {
  mode: "init",
  defaults: {
    delimiter: null,
    fill: [$.colors("primary", 700), $.colors("primary", 400), $.colors("primary", 200)],
    height: null,
    innerRadius: null,
    radius: 11,
    width: null
  },
  init: function(context) {
    if (!$.fn.peity) return;

    var defaults = $.components.getDefaults("peityDonut");

    $('[data-plugin="peityDonut"]', context).each(function() {
      var $this = $(this),
        options = $this.data();

      if (options.skin) {
        if ($.colors(options.skin)) {
          var skinColors = $.colors(options.skin);
          defaults.fill = [skinColors[700], skinColors[400], skinColors[200]];
        }
      }

      options = $.extend(true, {}, defaults, options);

      $this.peity('donut', options);
    });
  }
});

$.components.register("peityLine", {
  mode: "init",
  defaults: {
    delimiter: ",",
    fill: [$.colors("primary", 200)],
    height: 22,
    max: null,
    min: 0,
    stroke: $.colors("primary", 600),
    strokeWidth: 1,
    width: 44
  },
  init: function(context) {
    if (!$.fn.peity) return;

    var defaults = $.components.getDefaults("peityLine");

    $('[data-plugin="peityLine"]', context).each(function() {
      var $this = $(this),
        options = $this.data();

      if (options.skin) {
        if ($.colors(options.skin)) {
          var skinColors = $.colors(options.skin);
          defaults.fill = [skinColors[200]];
          defaults.stroke = skinColors[600];
        }
      }

      options = $.extend(true, {}, defaults, options);

      $this.peity('line', options);
    });
  }
});

$.components.register("peityPie", {
  mode: "init",
  defaults: {
    delimiter: null,
    fill: [$.colors("primary", 700), $.colors("primary", 400), $.colors("primary", 200)],
    height: null,
    radius: 11,
    width: null
  },
  init: function(context) {
    if (!$.fn.peity) return;

    var defaults = $.components.getDefaults("peityPie");

    $('[data-plugin="peityPie"]', context).each(function() {

      var $this = $(this),
        options = $this.data();

      if (options.skin) {
        if ($.colors(options.skin)) {
          var skinColors = $.colors(options.skin);
          defaults.fill = [skinColors[700], skinColors[400], skinColors[200]];
        }
      }

      options = $.extend(true, {}, defaults, options);

      $this.peity('pie', options);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("rating", {
  mode: "init",
  defaults: {
    targetKeep: true,
    icon: "font",
    starType: "i",
    starOff: "icon wb-star",
    starOn: "icon wb-star orange-600",
    cancelOff: "icon wb-minus-circle",
    cancelOn: "icon wb-minus-circle orange-600",
    starHalf: "icon wb-star-half orange-500"
  },
  init: function(context) {
    if (!$.fn.raty) return;

    var defaults = $.components.getDefaults("rating");

    $('[data-plugin="rating"]', context).each(function() {
      var $this = $(this);
      var options = $.extend(true, {}, defaults, $this.data());

      if (options.hints) {
        options.hints = options.hints.split(',');
      }

      $this.raty(options);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("select2", {
  mode: "default",
  defaults: {
    width: "style"
    // dropdownAutoWidth : true,
    // dropdownCssClass : 'bigdrop'
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("selectable", {
  mode: "init",
  defaults: {
    allSelector: '.selectable-all',
    itemSelector: '.selectable-item',
    rowSelector: 'tr',
    rowSelectable: false,
    rowActiveClass: 'active',
    onChange: null
  },
  init: function(context) {
    if (!$.fn.asSelectable) return;
    var defaults = $.components.getDefaults('selectable');

    $('[data-plugin="selectable"], [data-selectable="selectable"]', context).each(function() {
      var options = $.extend({}, defaults, $(this).data());
      $(this).asSelectable(options);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("slidePanel", {
  mode: "manual",
  defaults: {
    closeSelector: '.slidePanel-close',
    mouseDragHandler: '.slidePanel-handler',
    loading: {
      template: function(options) {
        return '<div class="' + options.classes.loading + '">' +
          '<div class="loader loader-default"></div>' +
          '</div>';
      },
      showCallback: function(options) {
        this.$el.addClass(options.classes.loading + '-show');
      },
      hideCallback: function(options) {
        this.$el.removeClass(options.classes.loading + '-show');
      }
    }
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("switchery", {
  mode: "init",
  defaults: {
    color: $.colors("primary", 600)
  },
  init: function(context) {
    if (typeof Switchery === "undefined") return;

    var defaults = $.components.getDefaults("switchery");

    $('[data-plugin="switchery"]', context).each(function() {
      var options = $.extend({}, defaults, $(this).data());

      new Switchery(this, options);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("table", {
  mode: "api",
  api: function(context) {
    /* section */
    $(document).on('click', '.table-section', function(e) {
      if ("checkbox" !== e.target.type && "button" !== e.target.type && "a" !== e.target.tagName.toLowerCase() && !$(e.target).parent("div.checkbox-custom").length) {
        if ($(this).hasClass("active")) {
          $(this).removeClass("active")
        } else {
          $(this).siblings('.table-section').removeClass("active");
          $(this).addClass("active");
        }
      }
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("verticalTab", {
  mode: "init",
  init: function(context) {
    if (!$.fn.matchHeight) return;

    $('.nav-tabs-vertical', context).each(function() {
      $(this).children().matchHeight();
    });
  }
});

$.components.register("horizontalTab", {
  mode: "init",
  init: function(context) {
    if (!$.fn.responsiveHorizontalTabs) return;

    $('.nav-tabs-horizontal', context).responsiveHorizontalTabs();
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("toastr", {
  mode: "api",
  api: function() {
    if (typeof toastr === "undefined") return;
    var defaults = $.components.getDefaults("toastr");

    $(document).on('click.site.toastr', '[data-plugin="toastr"]', function(e) {
      e.preventDefault();

      var $this = $(this);
      var options = $.extend(true, {}, defaults, $this.data());
      var message = options.message || '';
      var type = options.type || "info";
      var title = options.title || undefined;

      switch (type) {
        case "success":
          toastr.success(message, title, options);
          break;
        case "warning":
          toastr.warning(message, title, options);
          break;
        case "error":
          toastr.error(message, title, options);
          break;
        case "info":
          toastr.info(message, title, options);
          break;
        default:
          toastr.info(message, title, options);
      }
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
$.components.register("toolbar", {
  mode: "init",
  init: function(context) {
    if (!$.fn.toolbar) return;

    var defaults = $.components.getDefaults("toolbar");

    $('[data-plugin="toolbar"]', context).each(function() {
      var $this = $(this);
      var content = $this.data("toolbar");

      var options = $.extend(true, {}, defaults);

      if (content) {
        options.content = content;
      }

      $this.toolbar(options);
    });
  }
});

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
(function(window, document, $) {
  'use strict';

  var pluginName = 'actionBtn';

  var Plugin = $[pluginName] = function(element, options) {
    this.element = element;
    this.$element = $(element);

    this.options = $.extend({}, Plugin.defaults, options, this.$element.data());

    this.init();
  };

  Plugin.defaults = {
    trigger: 'click', // click, hover
    toggleSelector: '.site-action-toggle',
    listSelector: '.site-action-buttons',
    activeClass: 'active',
    onShow: function() {},
    onHide: function() {}
  };

  Plugin.prototype = {
    constructor: Plugin,
    init: function() {
      this.showed = false;

      this.$toggle = this.$element.find(this.options.toggleSelector);
      this.$list = this.$element.find(this.options.listSelector);

      var self = this;

      if (this.options.trigger === 'hover') {
        this.$element.on('mouseenter', this.options.toggleSelector, function() {
          if (!self.showed) {
            self.show();
          }
        });
        this.$element.on('mouseleave', this.options.toggleSelector, function() {
          if (self.showed) {
            self.hide();
          }
        });
      } else {
        this.$element.on('click', this.options.toggleSelector, function() {
          if (self.showed) {
            self.hide();
          } else {
            self.show();
          }
        });
      }
    },

    show: function() {
      if (!this.showed) {
        this.$element.addClass(this.options.activeClass);
        this.showed = true;

        this.options.onShow.call(this);
      }
    },
    hide: function() {
      if (this.showed) {
        this.$element.removeClass(this.options.activeClass);
        this.showed = false;

        this.options.onHide.call(this);
      }
    }
  };

  $.fn[pluginName] = function(options) {
    if (typeof options === 'string') {
      var method = options;
      var method_arguments = Array.prototype.slice.call(arguments, 1);

      if (/^\_/.test(method)) {
        return false;
      } else if ((/^(get)$/.test(method))) {
        var api = this.first().data(pluginName);
        if (api && typeof api[method] === 'function') {
          return api[method].apply(api, method_arguments);
        }
      } else {
        return this.each(function() {
          var api = $.data(this, pluginName);
          if (api && typeof api[method] === 'function') {
            api[method].apply(api, method_arguments);
          }
        });
      }
    } else {
      return this.each(function() {
        if (!$.data(this, pluginName)) {
          $.data(this, pluginName, new Plugin(this, options));
        }
      });
    }
  };
})(window, document, jQuery);

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
+ function($) {
  'use strict';

  // TAB CLOSE CLASS DEFINITION
  // ==========================

  var dismiss = '[data-close="tab"]'
  var TabClose = function(el) {
    $(el).on('click', dismiss, this.close);
  }

  TabClose.TRANSITION_DURATION = 150

  TabClose.prototype.close = function(e) {
    var $this = $(this);
    var $toggle = $this.closest('[data-toggle="tab"]');
    var selector = $toggle.data('target');
    var $li = $toggle.parent('li');

    if (!selector) {
      selector = $toggle.attr('href');
      selector = selector && selector.replace(/.*(?=#[^\s]*$)/, '');
    }

    if ($li.hasClass('active')) {
      var $next = $li.siblings().eq(0).children('[data-toggle="tab"]');
      if ($next.length > 0) {
        var api = $next.tab().data('bs.tab');
        api.show();
      }
    }

    var $parent = $(selector);
    if (e) e.preventDefault();

    $parent.trigger(e = $.Event('close.bs.tab'))

    if (e.isDefaultPrevented()) return

    $parent.removeClass('in')

    function removeElement() {
      // detach from parent, fire event then clean up data
      $parent.detach().trigger('closed.bs.tab').remove();
      $li.detach().remove();
    }

    $.support.transition && $parent.hasClass('fade') ?
      $parent
      .one('bsTransitionEnd', removeElement)
      .emulateTransitionEnd(TabClose.TRANSITION_DURATION) :
      removeElement()
  }


  // TAB CLOSE PLUGIN DEFINITION
  // ===========================

  function Plugin(option) {
    return this.each(function() {
      var $this = $(this)
      var data = $this.data('bs.tab.close')

      if (!data) $this.data('bs.tab.close', (data = new TabClose(this)))
      if (typeof option == 'string') data[option].call($this)
    })
  }

  var old = $.fn.tabClose

  $.fn.tabClose = Plugin
  $.fn.tabClose.Constructor = TabClose


  // TAB CLOSE NO CONFLICT
  // =====================

  $.fn.tabClose.noConflict = function() {
    $.fn.tabClose = old
    return this
  }


  // TAB CLOSE DATA-API
  // ==================

  $(document).on('click.bs.tab-close.data-api', dismiss, TabClose.prototype.close)

}(jQuery);

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
(function(window, document, $) {
  "use strict";

  var pluginName = 'responsiveHorizontalTabs',
    defaults = {
      navSelector: '.nav-tabs',
      itemSelector: '>li',
      dropdownSelector: '>.dropdown',
      dropdownItemSelector: 'li',
      tabSelector: '.tab-pane',
      activeClassName: 'active'
    };

  var Plugin = function(el, options) {
    var $tabs = this.$tabs = $(el);
    this.options = options = $.extend(true, {}, defaults, options);

    var $nav = this.$nav = $tabs.find(this.options.navSelector),
      $dropdown = this.$dropdown = $nav.find(this.options.dropdownSelector);
    var $items = this.$items = $nav.find(this.options.itemSelector).filter(function() {
      return !$(this).is($dropdown);
    });

    this.$dropdownItems = $dropdown.find(this.options.dropdownItemSelector);
    this.$tabPanel = this.$tabs.find(this.options.tabSelector);

    this.breakpoints = [];

    $items.each(function() {
      $(this).data('width', $(this).width());
    });

    this.init();
    this.bind();

  };

  Plugin.prototype = {
    init: function() {
      if (this.$dropdown.length === 0) return;

      this.$dropdown.show();
      this.breakpoints = [];

      var length = this.length = this.$items.length,
        dropWidth = this.dropWidth = this.$dropdown.width(),
        total = 0;

      this.flag = length;

      if (length <= 1) {
        this.$dropdown.hide();
        return;
      }

      for (var i = 0; i < length - 2; i++) {
        if (i === 0) this.breakpoints.push(this.$items.eq(i).outerWidth() + dropWidth);
        else this.breakpoints.push(this.breakpoints[i - 1] + this.$items.eq(i).width());
      }

      for (i = 0; i < length; i++) {
        total += this.$items.eq(i).outerWidth();
      }
      this.breakpoints.push(total);

      this.layout();
    },

    layout: function() {
      if (this.breakpoints.length <= 0) return;

      var width = this.$nav.width(),
        i = 0,
        activeClassName = this.options.activeClassName,
        active = this.$tabPanel.filter('.' + activeClassName).index();

      for (; i < this.breakpoints.length; i++) {
        if (this.breakpoints[i] > width) break;
      }

      if (i === this.flag) return;


      this.$items.removeClass(activeClassName);
      this.$dropdownItems.removeClass(activeClassName);
      this.$dropdown.removeClass(activeClassName);

      if (i === this.breakpoints.length) {
        this.$dropdown.hide();
        this.$items.show();
        this.$items.eq(active).addClass(activeClassName);
      } else {
        this.$dropdown.show();
        for (var j = 0; j < this.length; j++) {
          if (j < i) {
            this.$items.eq(j).show();
            this.$dropdownItems.eq(j).hide();
          } else {
            this.$items.eq(j).hide();
            this.$dropdownItems.eq(j).show();
          }
        }

        if (active < i) {
          this.$items.eq(active).addClass(activeClassName);
        } else {
          this.$dropdown.addClass(activeClassName);
          this.$dropdownItems.eq(active).addClass(activeClassName);
        }


      }

      this.flag = i;
    },

    bind: function() {
      var self = this;

      $(window).resize(function() {
        self.layout();
      });
    }

  };


  $.fn[pluginName] = function(options) {
    if (typeof options === 'string') {
      var method = options;
      var method_arguments = Array.prototype.slice.call(arguments, 1);
      if (/^\_/.test(method)) {
        return false;
      } else {
        return this.each(function() {
          var api = $.data(this, pluginName);
          if (api && typeof api[method] === 'function') {
            api[method].apply(api, method_arguments);
          }
        });
      }
    } else {
      return this.each(function() {
        if (!$.data(this, pluginName)) {
          $.data(this, pluginName, new Plugin(this, options));
        } else {
          $.data(this, pluginName).init();
        }
      });
    }
  };
})(window, document, jQuery);

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
(function(window, document, $) {
  'use strict';

  var pluginName = 'asSelectable';

  var Plugin = $[pluginName] = function(element, options) {
    this.element = element;
    this.$element = $(element);
    this.options = $.extend({}, Plugin.defaults, options, this.$element.data());

    this.init();
  };

  Plugin.defaults = {
    allSelector: '.selectable-all',
    itemSelector: '.selectable-item',
    rowSelector: 'tr',
    rowSelectable: false,
    rowActiveClass: 'active',
    onChange: null
  };

  Plugin.prototype = {
    constructor: Plugin,
    init: function() {
      var self = this;
      var options = this.options;

      self.$element.on('change', options.allSelector, function() {
        var value = $(this).prop("checked");
        self.getItems().each(function() {
          var $one = $(this);
          $one.prop("checked", value).trigger('change', [true]);;
          self.selectRow($one, value);
        });
      });

      self.$element.on('click', options.itemSelector, function(e) {
        var $one = $(this),
          value = $one.prop("checked");
        self.selectRow($one, value);
        e.stopPropagation();
      });

      self.$element.on('change', options.itemSelector, function() {
        var $all = self.$element.find(options.allSelector),
          $row = self.getItems(),
          total = $row.length,
          checked = self.getSelected().length;

        if (total === checked) {
          $all.prop('checked', true);
        } else {
          $all.prop('checked', false);
        }

        self._trigger('change', checked);

        if (typeof options.callback === 'function') {
          options.callback.call(this);
        }
      });

      if (options.rowSelectable) {
        self.$element.on('click', options.rowSelector, function(e) {
          if ("checkbox" !== e.target.type && "button" !== e.target.type && "a" !== e.target.tagName.toLowerCase() && !$(e.target).parent("div.checkbox-custom").length) {
            var $checkbox = $(options.itemSelector, this),
              value = $checkbox.prop("checked");
            $checkbox.prop("checked", !value);
            self.selectRow($checkbox, !value);
          }
        });
      }
    },

    selectRow: function(item, value) {
      if (value) {
        item.parents(this.options.rowSelector).addClass(this.options.rowActiveClass);
      } else {
        item.parents(this.options.rowSelector).removeClass(this.options.rowActiveClass);
      }
    },

    getItems: function() {
      return this.$element.find(this.options.itemSelector);
    },

    getSelected: function() {
      return this.getItems().filter(':checked');
    },

    _trigger: function(eventType) {
      var method_arguments = Array.prototype.slice.call(arguments, 1),
        data = [this].concat(method_arguments);

      // event
      this.$element.trigger(pluginName + '::' + eventType, data);

      // callback
      eventType = eventType.replace(/\b\w+\b/g, function(word) {
        return word.substring(0, 1).toUpperCase() + word.substring(1);
      });
      var onFunction = 'on' + eventType;
      if (typeof this.options[onFunction] === 'function') {
        this.options[onFunction].apply(this, method_arguments);
      }
    },
  };

  $.fn[pluginName] = function(options) {
    if (typeof options === 'string') {
      var method = options;
      var method_arguments = Array.prototype.slice.call(arguments, 1);

      if (/^\_/.test(method)) {
        return false;
      } else if ((/^(get)/.test(method))) {
        var api = this.first().data(pluginName);

        if (api && typeof api[method] === 'function') {
          return api[method].apply(api, method_arguments);
        }
      } else {
        return this.each(function() {
          var api = $.data(this, pluginName);
          if (api && typeof api[method] === 'function') {
            api[method].apply(api, method_arguments);
          }
        });
      }
    } else {
      return this.each(function() {
        if (!$.data(this, pluginName)) {
          $.data(this, pluginName, new Plugin(this, options));
        }
      });
    }
  };
})(window, document, jQuery);

/*!
 * remark (http://getbootstrapadmin.com/remark)
 * Copyright 2015 amazingsurge
 * Licensed under the Themeforest Standard Licenses
 */
(function($) {
  "use strict";

  var pluginName = 'stickyHeader',
    defaults = {
      headerSelector: '.header',
      changeHeaderOn: 100,
      activeClassName: 'active-sticky-header',
      min: 50,
      method: 'toggle'
    };

  var Plugin = function(el, options) {
    this.isActive = false;
    this.init(options);
    this.bind();
  };

  Plugin.prototype = {
    init: function(options) {
      var $el = this.$el.css('transition', 'none'),
        $header = this.$header = $el.find(options.headerSelector).css({
          position: 'absolute',
          top: 0,
          left: 0
        });

      this.options = $.extend(true, {}, defaults, options, $header.data());
      this.headerHeight = $header.outerHeight();
      // this.offsetTop()
      // $el.css('transition','all .5s linear');
      // $header.css('transition','all .5s linear');
      this.$el.css('paddingTop', this.headerHeight);
    },

    _toggleActive: function() {
      if (this.isActive) {
        this.$header.css('height', this.options.min);
      } else {
        this.$header.css('height', this.headerHeight);
      }
    },


    bind: function() {
      var self = this;
      this.$el.on('scroll', function() {
        if (self.options.method === 'toggle') {
          if ($(this).scrollTop() > self.options.changeHeaderOn && !self.isActive) {
            self.$el.addClass(self.options.activeClassName);
            self.isActive = true;
            self.$header.css('height', self.options.min);
            self.$el.trigger('toggle:sticky', [self, self.isActive]);
          } else if ($(this).scrollTop() <= self.options.changeHeaderOn && self.isActive) {
            self.$el.removeClass(self.options.activeClassName);
            self.isActive = false;
            self.$header.css('height', self.headerHeight);
            self.$el.trigger('toggle:sticky', [self, self.isActive]);
          }
        } else if (self.options.method === 'scroll') {
          var offset = Math.max(self.headerHeight - $(this).scrollTop(), self.options.min);
          if (offset === self.headerHeight) {
            self.$el.removeClass(self.options.activeClassName);
          } else {
            self.$el.addClass(self.options.activeClassName);
          }
          self.$header.css('height', offset);
          self.$el.trigger('toggle:sticky', [self]);
        }
      });
    }
  };

  $.fn[pluginName] = function(options) {
    if (typeof options === 'string') {
      var method = options;
      var method_arguments = Array.prototype.slice.call(arguments, 1);
      if (/^\_/.test(method)) {
        return false;
      } else {
        return this.each(function() {
          var api = $.data(this, pluginName);
          if (api && typeof api[method] === 'function') {
            api[method].apply(api, method_arguments);
          }
        });
      }
    } else {
      return this.each(function() {
        if (!$.data(this, pluginName)) {
          $.data(this, pluginName, new Plugin(this, options));
        } else {
          $.data(this, pluginName).init(options);
        }
      });
    }
  };
})(jQuery);
