(function() {
    angular.module('hermesApp').directive('scrollWatch', ['$location', '$anchorScroll', '$timeout',
        function ($location, $anchorScroll, $timeout) {
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
    ]);
})();