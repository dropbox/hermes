/**
 * Module for working with D3 visualization library
 */
(function() {
    angular.module('d3', [])
        .factory('d3Service', ['$document', '$window', '$q', '$rootScope',
            function ($document, $window, $q, $rootScope) {
                var d = $q.defer(),
                    d3service = {
                        d3: function () {
                            return d.promise;
                        }
                    };

                function onScriptLoad() {
                    // Load client in the browser
                    $rootScope.$apply(function () {
                        d.resolve($window.d3);
                    });
                }

                var scriptTag = $document[0].createElement('script');
                scriptTag.type = 'text/javascript';
                scriptTag.async = true;
                scriptTag.src = 'https://monitor.dropbox.com/cdnjs/ajax/libs/d3/3.5.5/d3.min.js';
                scriptTag.onreadystatechange = function () {
                    if (this.readyState == 'complete') onScriptLoad();
                }
                scriptTag.onload = onScriptLoad;

                var s = $document[0].getElementsByTagName('body')[0];
                s.appendChild(scriptTag);

                return d3service;
            }]);

    /**
     * Create the d3-bars directive
     */
    angular.module('hermesApp').directive('d3Bars', ['$window', '$timeout', 'd3Service', '$rootScope',
        function ($window, $timeout, d3Service, $rootScope) {
            return {
                restrict: 'A',
                scope: {
                    data: '=',
                    vizwatch: '=',
                    label: '@',
                    onClick: '&'
                },
                link: function ($scope, $ele, $attrs) {
                    d3Service.d3().then(function (d3) {

                        var renderTimeout;
                        var lastData;
                        var isVisible = true;
                        var graphHeight = parseInt($attrs.graphHeight) || 200;
                        var barPadding = parseInt($attrs.barPadding) || 10;
                        var graphUnit = $attrs.graphUnit;
                        var graphThreshold = $attrs.threshold;
                        var graphThresholdIsLower = $attrs.tIsLower;
                        var yFormat = function (d) {
                            return d + graphUnit;
                        };

                        var svg = d3.select($ele[0])
                            .append('svg')
                            .style('width', '100%');

                        var axisG = svg.append('g');

                        var thresholdPath = svg.append('g').attr("class", "thresholdLine").append('path');


                        $window.onresize = function () {
                            $scope.$apply();
                        };

                        $scope.$watch(function () {
                            return angular.element($window)[0].innerWidth;
                        }, function () {
                            $scope.render($scope.data);
                        });

                        $scope.$watch('data', function (newData) {
                            lastData = newData
                            $scope.render(newData);
                        }, true);

                        $scope.$watch('vizwatch', function (newData) {
                            if (newData) {
                                isVisible = true;
                                $scope.render(lastData);
                            } else {
                                isVisible = false;
                            }
                        });

                        $scope.render = function (data) {
                            //svg.selectAll('*').remove();

                            if (!data || !isVisible) return;
                            if (renderTimeout) clearTimeout(renderTimeout);

                            renderTimeout = $timeout(function () {
                                var width = d3.select($ele[0])[0][0].offsetWidth;
                                var height = graphHeight;
                                var barClass = function (d) {
                                    if (d && (graphThresholdIsLower == 1 && d < graphThreshold)
                                        || (graphThresholdIsLower == 0 && d > graphThreshold)) {
                                        return "badValueBar";
                                    } else {
                                        return "goodValueBar";
                                    }
                                };
                                var barFill = function (d) {
                                    if (d && (graphThresholdIsLower == 1 && d < graphThreshold)
                                        || (graphThresholdIsLower == 0 && d > graphThreshold)) {
                                        return "#ed7a6f";
                                    } else {
                                        return "#72b6ec";
                                    }
                                }

                                var topPadding = graphHeight * .05;
                                var leftPadding = width * .05;
                                var barWidth = (width - leftPadding) / data.length;
                                var barBaseLine = graphHeight * .75;
                                var barHeight = barBaseLine - topPadding;

                                var maxValue = d3.max(data, function (d) {
                                    if (graphUnit === "%")
                                        return 100;
                                    return d.kpi * 1.10;
                                });
                                var yScale = d3.scale.linear()
                                    .domain([0, maxValue])
                                    .range([0, barHeight]);
                                var yAxisScale = d3.scale.linear()
                                    .domain([0, maxValue])
                                    .range([barHeight, 0]);

                                svg.attr('height', graphHeight);

                                /** ADD/REMOVE/TRANSITION BARS **/
                                var svgData = svg.selectAll('rect').data(data);

                                svgData
                                    .enter()
                                    .append('rect')
                                    .on('click', function (d) {
                                        return $scope.onClick({item: d});
                                    })
                                    .attr('height', 0)
                                    .attr('width', function (d, i) {
                                        return (barWidth - barPadding);
                                    })
                                    .attr('x', function (d, i) {
                                        return leftPadding + (barPadding / 2) + i * (barWidth);
                                    })
                                    .attr('y', barBaseLine)
                                    .attr('fill', function (d) {
                                        return barFill(d.kpi);
                                    });


                                svgData.exit().remove();

                                svg.selectAll('rect')
                                    .transition()
                                    .duration(500)
                                    .delay(function (d, i) {
                                        return i * 25;
                                    })
                                    .attr('width', function () {
                                        return (barWidth - barPadding);
                                    }).attr('x', function (d, i) {
                                        return leftPadding + (barPadding / 2) + i * (barWidth);
                                    })
                                    .attr('y', function (d) {
                                        return barBaseLine - yScale(d.kpi);
                                    })
                                    .attr('height', function (d) {
                                        return yScale(d.kpi);
                                    })
                                    .attr('class', function (d) {
                                        return barClass(d.kpi);
                                    })
                                    .attr('fill', function (d) {
                                        return barFill(d.kpi);
                                    });

                                /** ADD/REMOVE/TRANSITION DATE LABELS **/
                                var svgLabel = svg.selectAll('.label').data(data);

                                svgLabel.exit().remove();

                                svgLabel
                                    .enter()
                                    .append('text')
                                    .attr('class', 'label')
                                    .attr('font-size', function () {
                                        return (height) / 30;
                                    })
                                    .attr("text-anchor", "end")
                                    .attr('transform', function (d, i) {
                                        var x = leftPadding + (i) * (barWidth) + (barWidth) * .5;
                                        return "translate(" + x + "," + (barBaseLine) + ") rotate(-90)";
                                    })
                                    .attr("dx", "-.8em");


                                svg.selectAll('.label')
                                    .transition()
                                    .duration(500)
                                    .delay(function (d, i) {
                                        return i * 25;
                                    })
                                    .attr('font-size', function () {
                                        return (height) / 30;
                                    })
                                    .attr('transform', function (d, i) {
                                        var x = leftPadding + (i) * (barWidth) + (barWidth) * .5;
                                        return "translate(" + x + "," + (barBaseLine) + ") rotate(-90)";
                                    })
                                    .text(function (d) {
                                        return d.date;
                                    });

                                /** ADD/REMOVE/TRANSITION BAR VALUES **/
                                var svgValue = svg.selectAll('.value').data(data);

                                svgValue.exit().remove();

                                var barValueFontSize = 0;
                                if (barWidth > 100) barValueFontSize = 20;
                                else if (barWidth > 40) barValueFontSize = barWidth / 5;

                                svgValue
                                    .enter()
                                    .append('text')
                                    .attr('class', 'value')
                                    .attr("dy", "-.15em")
                                    .attr('font-size', function () {
                                        return barValueFontSize;
                                    })
                                    .attr('transform', function (d, i) {
                                        var y = barBaseLine;
                                        var x = leftPadding + (barPadding / 2)
                                            + (i * barWidth)
                                            + (barWidth) * .5;
                                        return "translate(" + x + "," + y + ")";
                                    });


                                svg.selectAll('.value')
                                    .transition()
                                    .duration(500)
                                    .delay(function (d, i) {
                                        return i * 25;
                                    })
                                    .attr('transform', function (d, i) {
                                        var y = barBaseLine - yScale(d.kpi);

                                        var x = leftPadding + (barPadding / 2) + (i)
                                            * (barWidth)
                                            + (barWidth) * .5;
                                        return "translate(" + x + "," + y + ")";
                                    })
                                    .attr('font-size', function () {
                                        return barValueFontSize;
                                    })
                                    .text(function (d) {
                                        if (d.kpi) {
                                            return d.kpi.toFixed(2) + graphUnit;
                                        } else {
                                            return "N/A";
                                        }
                                    });

                                /** DRAW THE THRESHOLD LINE **/
                                if ($attrs.threshold != 0) {
                                    var tLineGen = d3.svg.line().x(function (d, i) {
                                        return i == 0 ? 0 : width;
                                    }).y(function (d) {
                                        return barBaseLine - yScale(graphThreshold);
                                    });

                                    thresholdPath.transition().duration(500).attr('d', tLineGen([graphThreshold, graphThreshold]));
                                }

                                /** ADD THE GRAPH AXIS **/
                                var axis = d3.svg.axis().scale(yAxisScale).tickSize(width)
                                    .tickFormat(yFormat).orient("right");

                                axisG.attr("class", "axis")
                                    .attr("transform", "translate(0," + (topPadding) + ")")
                                    .call(axis);

                                axisG.selectAll("g").filter(function (d) {
                                    return d;
                                }).classed("minor", true);

                                axisG.selectAll("text")
                                    .attr("x", leftPadding - barPadding)
                                    .attr("dy", -4)
                                    .attr('font-size', function () {
                                        return (height) / 30;
                                    })
                            }, 0);
                        };
                    });
                }
            }
        }]);
})();