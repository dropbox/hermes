/**
 * directive for building quest progress bars with Raphael
 */
(function() {
    angular.module('hermesApp').directive('questProgressChart', ['$window', '$timeout',
        function ($window, $timeout) {
            return {
                restrict: 'A',
                scope: {
                    data: '=',
                    onClick: '&'
                },
                link: function ($scope, $ele, $attrs) {
                    var renderTimeout;
                    var lastData;
                    var isVisible = true;
                    var graphHeight = parseInt($attrs.graphHeight) || 200;
                    var raphael = new Raphael($ele[0], "100%", graphHeight);

                    $scope.$watch('data', function (newData) {
                        lastData = [newData];
                        $scope.render([newData]);
                    }, true);

                    $scope.render = function (data) {
                        if (!data || !isVisible) return;
                        if (renderTimeout) clearTimeout(renderTimeout);

                        renderTimeout = $timeout(function () {
                            var width = $ele[0].offsetWidth;

                            // erase everything
                            raphael.clear();
                        }, 0);
                    };
                }
            }
        }]);
})();