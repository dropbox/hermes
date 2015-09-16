(function() {

    'use strict';

    var app = angular.module('hermesApp', ['ngAnimate', 'ngRoute', 'ngLocationUpdate']);

    app.config(['$routeProvider', '$locationProvider', function($routeProvider, $locationProvider) {
        $routeProvider.when('/v1/quests/:questId?', {
            templateUrl: '/templates/questStatus.html',
            reloadOnSearch: false
        }).when('/fates', {
            templateUrl: '/templates/fateViewer.html',
            reloadOnSearch: false
        }).otherwise({redirectTo: '/v1/quests/'});

        // use the HTML5 History API
        $locationProvider.html5Mode({
            enabled: true,
            requireBase: false
        });
    }]);

})();