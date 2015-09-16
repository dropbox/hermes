(function() {
    function scrollWatch ($anchorScroll, $timeout) {
        return {
            restrict: 'A',
            transclude: true,
            link: function ($scope, $ele, $attrs) {
                if ($scope.$last === true) {
                    $timeout(function () {
                        $anchorScroll();
                    }, 100);
                }
            }
        }
    }

    angular.module('hermesApp').directive('scrollWatch', scrollWatch);
    scrollWatch.inject = ['$anchorScroll', '$timeout'];
})();