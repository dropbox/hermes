/**
 * Build tasks are broken up as either top-level tasks, for example `build`,
 * or sub-tasks, namespaced with a top-level task name and a color as a prefix,
 * for example, `build:js`
 *
 * You'll likely want to have gulp installed globally if you're using it regularly
 * though you'll be able to run it fron `node_modules/.bin/gulp` if you don't
 * use it often.
 *
 * Top Level Tasks
 * ---------------
 * gulp clean - Remove built assets
 * gulp build - Build all static assets for distribution
 * gulp lint - Lint JavaScript and CSS files
 * gulp bower - Update local cache for web dependencies
 */

var gulp = require('gulp');

// Plugin Imports
var jshint = require('gulp-jshint');
var concat = require('gulp-concat');
var ngAnnotate = require('gulp-ng-annotate');
var uglify = require('gulp-uglify');
var rename = require('gulp-rename');
var minifyCss = require('gulp-minify-css');
var csslint = require('gulp-csslint');
var mainBowerFiles = require('main-bower-files');
var bower = require('gulp-bower');
var sort = require('gulp-sort');
var del = require('del');
var watch = require('gulp-watch');

var SRC_ROOT = './hermes/webapp/src/';
var BUILD_DEST = './hermes/webapp/build/';

var JS_MAIN_SRC = SRC_ROOT + 'js/hermesApp.js';
var JS_SRC = SRC_ROOT + 'js/**/*.js';
var STYLE_SRC = SRC_ROOT + 'css/**/*.css';
var IMAGE_SRC = SRC_ROOT + 'img/**';
var HTML_SRC = SRC_ROOT + "**/*.html";


/**
 * Task to lint JavaScript files.
 */
gulp.task('lint:js', function() {
    return gulp.src([JS_MAIN_SRC, JS_SRC])
        .pipe(jshint())
        .pipe(jshint.reporter('jshint-stylish'));
});


/**
 * Task to lint CSS files.
 */
gulp.task('lint:style', function() {
    return gulp.src(STYLE_SRC)
        .pipe(csslint())
        .pipe(csslint.reporter());
});


/**
 * Top level Task to run all lint tasks.
 */
gulp.task('lint', ['lint:js', 'lint:style']);


/**
 * Updates the local cache of bower dependencies
 */
gulp.task('bower', function() {
    return bower({ cmd: 'update'});
});


/**
 * Task to build JavaScript files.
 */
gulp.task('build:js', function() {
    return gulp.src([JS_MAIN_SRC, JS_SRC])
        .pipe(ngAnnotate())
        //.pipe(sort())
        .pipe(concat('app.js'))
        .pipe(gulp.dest((BUILD_DEST + 'js')))
        .pipe(uglify())
        .pipe(rename('app.min.js'))
        .pipe(gulp.dest((BUILD_DEST + 'js')));
});

/**
 * Task to build our HTML files
 */
gulp.task('build:html', function() {
    return gulp.src(HTML_SRC)
        .pipe(gulp.dest((BUILD_DEST)))
});


/**
 * Task to build CSS files.
 */
gulp.task('build:style', function() {
    return gulp.src(STYLE_SRC)
        .pipe(sort())
        .pipe(concat('hermes.css'))
        .pipe(gulp.dest((BUILD_DEST + 'css')))
        .pipe(minifyCss())
        .pipe(rename('hermes.min.css'))
        .pipe(gulp.dest((BUILD_DEST + 'css')));
});


/**
 * Task to "build" images. While we're not doing anything interesting
 * now this opens up the option for building sprites if needed. This
 * also keeps our src separate from our build where we'll do things like
 * hash built files eventually.
 */
gulp.task('build:images', function() {
    return gulp.src(IMAGE_SRC)
        .pipe(gulp.dest((BUILD_DEST + 'img')))
});


/**
 * Uses bower to install the "main" files into our build. In most cases
 * the "main" files are manually specified in the `overrides` section
 * of bower.json
 */
gulp.task('build:3rdparty', ['bower'], function() {
    return gulp.src(mainBowerFiles(), {base: '_bc'})
        .pipe(gulp.dest(BUILD_DEST + 'vendor'))
});


/**
 * Create a hashed version of all built files. This is currently
 * just a placeholder and hasn't been finished yet.
 */
gulp.task('build:revisions', ['build:html', 'build:js', 'build:style', 'build:images', 'build:3rdparty'], function() {
    // TODO(gary): Do.
    return gulp.src(BUILD_DEST);
});


/**
 * Super task to build everything.
 */
gulp.task('build', ['build:revisions']);


/**
 * Remove the build directory
 */
gulp.task('clean', function(cb) {
    del([BUILD_DEST], cb);
});


gulp.task('watch', ['build'], function() {
    gulp.watch([JS_MAIN_SRC, JS_SRC, STYLE_SRC, IMAGE_SRC, HTML_SRC], ['build']);
});
