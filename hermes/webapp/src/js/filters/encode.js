(function() {

    'use strict';

    function EncodeFilter() {
        return window.encodeURIComponent;
    }

    angular.module('hermesApp').filter('encode', EncodeFilter);
})();