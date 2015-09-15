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
                    types: '=',
                    colors: '=',
                    onClick: '&'
                },
                link: function ($scope, $ele, $attrs) {
                    var width = $ele[0].offsetWidth;
                    var graphHeight = 300;
                    var legendFontSize = graphHeight * .04;
                    var legendSpacing = graphHeight * .06;
                    var titleFontSize = graphHeight * .08;


                    var renderTimeout;
                    var types = null;
                    var numberOfTypes = 0;
                    var rad = Math.PI / 180;

                    // we don't pull this from the backend b/c the backend gives a total that
                    // includes completed intermediate labors
                    var totalLabors = 0;
                    var colors;
                    var raphael = new Raphael($ele[0], "100%", graphHeight);

                    $scope.$watch('data', function (newData) {
                        $scope.render([newData]);
                    }, true);

                    $scope.$watch('types', function (newData) {
                        types = newData;
                        numberOfTypes = 0;
                        totalLabors = 0;
                        for (var idx in types) {
                            numberOfTypes++;
                            totalLabors += types[idx];
                        }
                    });

                    $scope.$watch('colors', function (newData) {
                        colors = newData;
                    }, true);

                    $scope.render = function (data) {
                        if (!data) return;
                        if (renderTimeout) clearTimeout(renderTimeout);

                        function wrapText(text, textEle, maxWidth) {
                            text = text.replace(/\s+/g, ' ').trim();
                            text = text.replace('\n', ' ');
                            var words = text.split(" ");
                            var wrappedText = '';
                            for (var idx in words) {
                                textEle.attr("text", wrappedText + " " + words[idx]);
                                if (textEle.getBBox().width > maxWidth) {
                                    wrappedText += '\n' + words[idx];
                                } else {
                                    wrappedText += ' ' + words[idx];
                                }
                            }

                            var bb = textEle.getBBox();
                            var h = Math.abs(bb.y2) - Math.abs(bb.y) + 1;
                            textEle.attr({
                                'y': bb.y + h
                            });
                        }

                        renderTimeout = $timeout(function () {
                            var legendX = width * .75;
                            var legendY = ((graphHeight *.6) + ((numberOfTypes-1)* legendSpacing)) / 2;
                            var pieX = width * .5;
                            var pieY = graphHeight * .5;
                            var pieR = graphHeight * .45;

                            // erase everything
                            raphael.clear();

                            // add the quest info to the top left
                            var title = raphael.text(0, titleFontSize, "Quest " + data[0].id)
                                .attr('text-anchor', 'start')
                                .attr('font-size', titleFontSize);

                            // add the quest description
                            var desc = raphael.text(0, legendY)
                                .attr('text-anchor', 'start')
                                .attr('font-size', legendFontSize);
                            wrapText(data[0].description, desc, width *.25);

                            // draw out the legend on the right
                            var i = 0;
                            var lastAngle = 0;
                            for (var idx in types) {
                                var type = idx;
                                var x = legendX;
                                var y = legendY + (i * legendSpacing * 1.1);
                                var text = raphael.text(
                                    x, y, type
                                ).attr('font-size', legendFontSize).attr('text-anchor', 'start')

                                var boxX = x - legendSpacing- (legendSpacing/4);
                                var boxY = y - legendSpacing/2;

                                var box = raphael.rect(boxX, boxY, legendSpacing, legendSpacing)
                                    .attr('fill', colors[i])
                                    .attr('stroke-width', '0');

                                var angle = types[idx] / totalLabors * 360;
                                if (angle == 360) {
                                    var circle = raphael.circle(pieX, pieY, pieR)
                                        .attr({
                                            'fill': colors[i],
                                            'stroke': 'none'
                                        });
                                } else {
                                    var pie = sector(
                                        pieX, pieY, pieR, lastAngle, lastAngle + angle,
                                        {
                                            'fill': colors[i],
                                            'stroke': 'none'
                                        }
                                    );
                                    lastAngle += angle;
                                }
                                i++;
                            }
                        }, 0);
                    };

                    function sector(cx, cy, r, startAngle, endAngle, params) {
                        var x1 = cx + r * Math.cos(-startAngle * rad),
                            x2 = cx + r * Math.cos(-endAngle * rad),
                            y1 = cy + r * Math.sin(-startAngle * rad),
                            y2 = cy + r * Math.sin(-endAngle * rad);
                        return raphael.path(["M", cx, cy, "L", x1, y1, "A", r, r, 0, +(endAngle - startAngle > 180), 0, x2, y2, "z"]).attr(params);
                    }
                }
            }
        }]);
})();