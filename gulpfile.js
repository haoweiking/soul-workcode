var gulp         = require('gulp');
var autoprefixer = require('gulp-autoprefixer');
var cssnano      = require('gulp-cssnano');
var csscomb      = require('gulp-csscomb');
var rename       = require("gulp-rename");
var plumber      = require('gulp-plumber');
var header       = require('gulp-header');
var uglify       = require('gulp-uglify');
var concat       = require('gulp-concat');
var gutil        = require('gulp-util');
var sequence     = require('run-sequence');
var del          = require('del');
var notifier     = require('node-notifier');

var options = {
  "destination": {
    "js": "yiyun/static/js",
    "css": "yiyun/static/css",
    "fonts": "yiyun/static/fonts",
    "vendor": "yiyun/static/vendor"
  },
  "source": {
    "path": "yiyun/static",
    "js": "yiyun/static/js",
    "css": "yiyun/static/css",
    "sass": "yiyun/static/sass",
    "fonts": "yiyun/static/fonts",
    "vendor": "yiyun/static/vendor"
  },
  "autoprefixerBrowsers": [
    "Android 2.3",
    "Android >= 4",
    "Chrome >= 20",
    "Firefox >= 24",
    "Explorer >= 8",
    "iOS >= 6",
    "Opera >= 12",
    "Safari >= 6"
  ]
}

var notifaker = function (message) {
  gutil.log(
    gutil.colors.cyan('gulp-notifier'),
    '[' + gutil.colors.blue('Gulp notification') + ']',
    gutil.colors.green(message)
  );

  notifier.notify({
    title: 'Gulp notification',
    message: message,
    onLast: true
  });
};

var pumped = function (achievement) {
  var exclamations = [
    'Sweet',
    'Awesome',
    'Epic',
    'Wow',
    'High Five',
    'Yay',
    'YEAH!',
    'Booyah'
  ];

  var randomIndex = Math.floor(Math.random() * exclamations.length);

  return [exclamations[randomIndex], '! ', achievement].join('');
};

// gulpfile booting message
gutil.log(gutil.colors.green('Starting to Gulp! Please wait...'));

/**
 * Vendor distribution
 */
gulp.task('vendor:clean', function(){
    del([options.destination.css + '/vendor.js',
        options.destination.css + '/vendor.min.js',
        options.destination.css + '/vendor.css',
        options.destination.css + '/vendor.min.css'
        ], { force: true }).then(paths => {
        done();
    });
});

gulp.task('vendor:styles', function(){
    gulp.src([
        options.source.css + '/bootstrap.css',
        options.source.css + '/bootstrap-extend.css',
        options.source.vendor + '/*/*.css',
        "!"+options.source.vendor + '/*/*.min.css',
        options.source.css + '/site.css'
    ])
    .pipe(autoprefixer(options.autoprefixer))
    .pipe(csscomb())
    .pipe(concat('vendor.css'))
    .pipe(gulp.dest(options.destination.css))
    .pipe(cssnano())
    .pipe(rename({
      extname: '.min.css'
    }))
    .pipe(gulp.dest(options.destination.css));
});

gulp.task('vendor:scripts', function(){
    gulp.src([
        "!"+options.source.vendor + '/animsition/jquery.animsition.js',
        options.source.vendor + '/*/*.js',
        options.source.vendor + '/*/*/*.js',
        "!"+options.source.vendor + '/*/*/*.min.js',
        "!"+options.source.vendor + '/*/*.min.js',
        "!"+options.source.vendor + '/jquery/jquery.js',
        "!"+options.source.vendor + '/bootstrap/bootstrap.js',
        "!"+options.source.vendor + '/html5shiv/*.js',
        "!"+options.source.vendor + '/media-match/*.js',
        "!"+options.source.vendor + '/respond/*.js',
        "!"+options.source.vendor + '/modernizr/*.js',
        "!"+options.source.vendor + '/breakpoints/breakpoints.js',
        options.source.vendor + '/toastr/toastr.js',
    ])
    .pipe(plumber())
    .pipe(concat('vendor.js'))
    .pipe(gulp.dest(options.destination.js))

    .pipe(uglify())
    .pipe(rename({
      extname: '.min.js'
    }))
    .pipe(gulp.dest(options.destination.js)); 
});

gulp.task('dist-vendor', function(done){
  sequence('vendor:clean', 'vendor:styles', 'vendor:scripts', function(){
    done();

    notifaker(pumped('Vendor Generated!'));
  });
});

gulp.task('dist-components', function(){
    gulp.src([
        options.source.js + '/components/*.js',
        options.source.js + '/plugins/*.js'
    ])
    .pipe(plumber())
    .pipe(concat('components.js'))
    .pipe(gulp.dest(options.destination.js))

    .pipe(uglify())
    .pipe(rename({
      extname: '.min.js'
    }))
    .pipe(gulp.dest(options.destination.js)); 
});

/**
 * Default
 */
gulp.task('default', ['dist-vendor', 'dist-components']);
