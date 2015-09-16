/**
 * directive for having a div's height based on the size of the viewport
 */
(function() {
    function viewportHeight ($window) {
        return {
            restrict: 'A',
            scope: {
            },
            link: function ($scope, $ele, $attrs) {
                var minHeight = $attrs.minHeight || 200;
                var padding = $attrs.padding || 120;

                $ele.css('overflow', 'scroll');

                angular.element($window).bind('resize', function() {
                    fixHeight();
                });

                function fixHeight() {
                    var innerHeight = $window.innerHeight;
                    var height = minHeight;
                    if (innerHeight > minHeight) {
                        height = innerHeight - padding - 80;
                    }

                    $ele.css('height', height + 'px');
                }

                fixHeight();
            }
        }
    }

    angular.module('hermesApp').directive('viewportHeight', viewportHeight);
    viewportHeight.$inject = ['$window'];
})();