(function() {

    'use strict';

    function NumFilter() {
        return function (input) {
            return parseInt(input, 10);
        };
    }

    angular.module('hermesApp').filter('num', NumFilter);

})();