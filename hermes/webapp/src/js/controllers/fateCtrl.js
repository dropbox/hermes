(function() {
    'use strict';

    function FateCtrl(hermesService) {
        var vm = this;

        hermesService.getFates().then(function(fates) {
            vm.fates = fates;
        });
    }

    angular.module('hermesApp').controller('FateCtrl', ['HermesService', FateCtrl]);

})();