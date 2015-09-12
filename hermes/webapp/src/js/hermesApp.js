(function() {

    'use strict';

    var app = angular.module('hermesApp', ['d3', 'ngAnimate', 'ngRoute']);

    app.config(['$routeProvider', '$locationProvider', function($routeProvider, $locationProvider) {
        $routeProvider.when('/', {
            templateUrl: '/templates/questStatus.html',
            reloadOnSearch: false
        }).when('/fates', {
            templateUrl: '/templates/fateViewer.html',
            reloadOnSearch: false
        }).otherwise({redirectTo: '/'});

        // use the HTML5 History API
        $locationProvider.html5Mode({
            enabled: true,
            requireBase: false
        });
    }]);

})();