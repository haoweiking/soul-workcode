(function(document, window, $){
    'use strict';
    var is_mobile = !!(navigator.userAgent.match(/Mobile/i));
    var Site = window.Site;

    $('#rules').summernote({
        toolbar: [
            // [groupName, [list of button]]
            ['style', ['bold', 'italic', 'underline', 'strikethrough', 'clear']],
            ['fontsize', ['fontsize', 'height']],
            ['color', ['color']],
            ['para', ['ul', 'ol', 'paragraph']],
            ['insert', ['hr', 'link', 'picture', 'table']]
            // ['msic', ['emoji']]
            // ['msic', ['fullscreen']]
        ],
        lang: "zh-CN",
        callbacks: {
            onImageUpload: function (files) {
                var url = window.yiyun.apis['match_upload_image'];
                var editor = $(this);
                var data = new FormData();
                if (Blob && files[0] instanceof Blob
                    && files[0].type.split("/")[0] == "image"
                    && files[0].type.split("/")[1]){
                    data.append('image', files[0], "blob."+files[0].type.split("/")[1])
                } else {
                    data.append('image', files[0])
                }
                $.ajax({
                    url: url,
                    method: 'POST',
                    data: data,
                    processData: false,
                    contentType: false,
                    success: function (data) {
                        editor.summernote('insertImage', data)
                    },
                    error: function (data) {
                        alert('上传图片失败，请重试')
                    }
                })
            }
        }
    });
    
    var updateAddress = function(name, address, lat, lng) {
        console.log(name, address, lat, lng)
     
        $("#lat").val(lat)
        $("#lng").val(lng)
        $("#formatted_address").val(name)
        $("#address").val(address)
        $('#address').typeahead('val', address)
    }

    $(document).ready(function(){
      Site.run();

      $("#province").on("select2:select", function(){
        var province = $(this).val();
        $("#city").find('option').remove();

        $.each(cities[province],function(key, value) {
            $("#city").append('<option value=' + value + '>' + value + '</option>');
        });

        $('#city').trigger('change')
      });

      $('#sports').select2()

      var marker = [];
      var map = new AMap.Map('map-container', {
        zoom: 13,
        center: [116.39, 39.9]
      })

      AMap.plugin(['AMap.ToolBar','AMap.Scale'],function(){
        var toolBar = new AMap.ToolBar();
        var scale = new AMap.Scale();
        map.addControl(toolBar);
        map.addControl(scale);
      })

      var aMapQuery = function(query, syncresults, process) {
          return AMap.service(['AMap.Autocomplete','AMap.PlaceSearch'], function(){
            var autocomplete = new AMap.Autocomplete({
                city: $("#city").val()
            });

            autocomplete.search(query, function(status, result) {
                if (status === 'complete' && result.info === 'OK') {
                    var addresses = []
                    $.each(result.tips, function(key, tip){
                        addresses.push(tip)
                    })
                    process(addresses)
                }
            })
          })
      }

      var getAddressDetail = function(city, name, location, update) {
          AMap.service('AMap.PlaceSearch', function(){
            var placeSearch = new AMap.PlaceSearch({
                city: city,
                map:map,
                extensions: "all",
            });

            setMarkerPosition(location)

            placeSearch.getDetails(name, function(status, result){
                console.log(result)
                var poi = result['poiList']['pois'][0],
                    formattedAddress = poi['adname']+poi['address']+poi['name'],
                    location = poi.location;

                setMarkerPosition(location)

                if (update) {
                  updateAddress(poi['name'], formattedAddress, location.lat, location.lng)
                }
            })
        })
      }

      var addressSearch = function(city, name, location, update) {
          AMap.service('AMap.PlaceSearch', function(){
            var placeSearch = new AMap.PlaceSearch({
                city: city,
                extensions: "all",
            });

            setMarkerPosition(location)

            placeSearch.search(name, function(status, result){
                if (result['poiList'] && result['poiList']['pois']) {
                  var poi = result['poiList']['pois'][0],
                      formattedAddress = poi['adname']+poi['address']+poi['name'],
                      location = poi.location;

                  setMarkerPosition(location)
                  if (update){
                    updateAddress(poi['name'], formattedAddress, location.lat, location.lng)
                  }
                }
            })
        })
      }

      var regeocodeLnglat = function(lat, lng, update){
            AMap.service('AMap.Geocoder', function(){
                var geocoder = new AMap.Geocoder({
                    city: $("#city").val(),
                    map:map,
                    extensions: "all",
                })

                var lnglat = new AMap.LngLat(lng, lat)

                geocoder.getAddress(lnglat, function(status, result) {
                    console.log(result)
                    if (status === 'complete' && result.info === 'OK') {
                        console.log(result['regeocode'])

                        var poi = result['regeocode']['pois'][0],
                            addressComponent = result['regeocode']['addressComponent'],
                            formattedAddress = result['regeocode']['formattedAddress'],
                            location = poi.location;

                         formattedAddress = formattedAddress.replace(addressComponent['province'], "")
                         formattedAddress = formattedAddress.replace(addressComponent['city'], "")

                        if (update){
                          updateAddress(poi['name'], formattedAddress, location.lat, location.lng)
                        }
                    }
                })
            })
      }

      var regeocodeAddress = function(address, callback){
            AMap.service('AMap.Geocoder', function(){
                var geocoder = new AMap.Geocoder({
                    city: $("#city").val(),
                    map:map,
                    extensions: "all",
                })

                geocoder.getLocation(address, function(status, result) {
                    if (status === 'complete' && result.info === 'OK') {
                        callback(result['geocodes'][0]['location'])
                    }
                })
            })
      }

      var marker = new AMap.Marker({
            draggable: true,
            cursor: 'move',
            raiseOnDrag: true
        })

      marker.on("dragend", function(e){
            map.setCenter(e.lnglat)
            regeocodeLnglat(e.lnglat.getLat(), e.lnglat.getLng(), true)
      })

      var setMarkerPosition = function(location) {
          if (!location) return

          marker.setPosition(location)
          marker.setMap(map)
          map.setCenter(location)
      }

      $('#address').typeahead({
            minLength: 1,
            highlight: true
        }, {
            name: 'my-dataset',
            display: 'name',
            source: aMapQuery,
            async: true,
            templates: {
                empty: [
                '<div class="empty-message">',
                    '没有匹配地址',
                '</div>'
                ].join('\n'),
                suggestion: Handlebars.compile('<div><strong>{{name}}</strong> – {{district}}</div>')
            }
      })

      $('#address').on("typeahead:select", function(e, suggestion){
            map.setCenter(suggestion.location)
            getAddressDetail(suggestion.adcode, suggestion["id"], suggestion.location, true)
      })

      var curLat = parseFloat($("#lat").val()),
          curLng = parseFloat($("#lng").val()),
          curAddress = $("#address").val();

      if(curAddress) {
          addressSearch($("#city").val(), curAddress, null, false)
      }
      else if (curLat && curLng){
          regeocodeLnglat(curLat, curLng, false)
          var lnglat = new AMap.LngLat(curLng, curLat)
          setMarkerPosition(lnglat)
          map.setCenter(lnglat)
      } else {
          addressSearch($("#city").val(), $("#city").val(), null, false)
      }
    })

    Vue.directive('select', {
      twoWay: true,
      priority: 1000,

      params: ['options'],

      bind: function () {
        var self = this
        $(this.el)
          .select2({
            data: this.params.options
          })
          .on('change', function () {
            self.set(this.value)
          })
      },
      update: function (value) {
        $(this.el).val(value).trigger('change')
      },
      unbind: function () {
        $(this.el).off().select2('destroy')
      }
    })

    var app = new Vue({
      el: "#vue-app",
      data: function() {
          return {
            groups: window.match_groups||[],
            options: window.match_options||[],
            can_change_goups: can_change_goups,
            group_type: group_type,
          }
      },
      ready: function(){
        if(this.groups.length == 0) {
          this.groups.push({})
        }
        if(this.options.length == 0) {
          this.options.push({})
        }
      },
      methods: {
          addGroup: function(){
            if(this.groups.length >= 100) {
              return
            }
            this.groups.push({})
            return false
          },
          removeGroup: function(idx){
            this.groups.splice(idx, 1)
          },
          addOption: function(){
            if(this.options.length >= 100) {
              return
            }
            this.options.push({})
            return false
          },
          removeOption: function(idx){
            this.options.splice(idx, 1)
          },
          submit: function(){
            $("#match-form").submit()
          }
      }
    });
 })(document, window, jQuery);
