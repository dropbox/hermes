/**
 * directive for building quest progress bars with Raphael
 */
(function() {
    angular.module('hermesApp').directive('questProgressBar', ['$window', '$timeout',
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
                    var graphHeight = parseInt($attrs.graphHeight) || 30;
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
                            var topPadding = graphHeight * .05;
                            var barWidth = width;
                            var barBaseLine = graphHeight * 1;
                            var barHeight = graphHeight * .3;
                            var percentXLoc = data[0].percent * barWidth / 100;

                            // erase everything
                            raphael.clear();

                            // draw the full bar, which shows the full extent of the progress bar
                            var fullBar = raphael.rect(
                                0, barBaseLine - barHeight,
                                barWidth, barHeight
                            );
                            fullBar.attr({'fill': '#7b8994'});
                            fullBar.attr({'stroke-width': 0});

                            // color in the part to represent the percentage complete
                            var percentBar = raphael.rect(
                                0, barBaseLine - barHeight,
                                percentXLoc, barHeight
                            );
                            percentBar.attr({'fill': '#3d464d'});
                            percentBar.attr({'stroke-width': 0});

                            // draw the little line that points up to the percentage label
                            var pathStr = "M" + percentXLoc + "," + (barBaseLine - (barHeight * 1.5))
                                + " L" + percentXLoc + "," + barBaseLine;
                            raphael.path(pathStr).attr({'stroke': '#3d464d'});

                            // add the percentage amount text
                            var label = raphael.text(
                                width/2,
                                (barBaseLine - (barHeight * 2)),
                                data[0].percent + "%"
                            ).attr({
                                'font-size': barHeight
                            });

                            var bb = label.getBBox();
                            var labelWidth = Math.abs(bb.x2) - Math.abs(bb.x) + 1;
                            if (percentXLoc - (labelWidth / 2) <= 0) {
                                label.attr({'x': labelWidth / 2});
                            } else if (percentXLoc + (labelWidth / 2) >= barWidth) {
                                label.attr({'x': barWidth - (labelWidth/2)});
                            } else {
                                label.attr({'x': percentXLoc});
                            }

                        }, 0);
                    };
                }
            }
        }]);
})();