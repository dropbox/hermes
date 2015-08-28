(function() {

    'use strict';

    function HermesService($http, $q) {
        var fates;
        var service = {
            getFates: getFates
        };

        return service;

        //////////////


        function getFates() {
            return $http.get("/api/v1/fates?expand=eventtypes&limit=all")
                .then(getFatesComplete)
                .catch(getFatesFailed);

            function getFatesComplete(response) {
                console.log("Got Fates! " + response.data.fates);
                return response.data.fates;
            }

            function getFatesFailed(error) {
                console.error("API call to get Fates failed. " + error.code)
            }
        }
    };

    angular.module('hermesApp')
        .factory('HermesService', ["$http", "$q", HermesService]);

})();