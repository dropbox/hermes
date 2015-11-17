/**
 * directive for building quest progress bars with Raphael
 */
(function() {
    function fateGraph (hermesService, $timeout, $window) {
        return {
            restrict: 'A',
            scope: {
                onClick: '&'
            },
            link: function ($scope, $ele, $attrs) {
                var fates;
                var graphData;
                var paper;
                var renderTimeout;

                hermesService.getFates().then(function (fateData) {
                    fates = fateData;
                    hermesService.getFatesGraph().then(function (data) {
                        graphData = data;
                        return data;
                    }).then(function(graphData){
                        // create our canvas
                        var width = $ele[0].clientWidth;
                        var height = $ele[0].clientHeight;
                        paper = new Raphael($ele[0], width, height);
                        $scope.render();
                    });
                });

                $window.onresize = function () {
                    $scope.$apply();
                };

                $scope.$watch(function () {
                    return angular.element($window)[0].innerWidth;
                }, function () {
                    $scope.render();
                });

                $scope.render = function () {
                    if (!graphData) return;
                    if (renderTimeout) clearTimeout(renderTimeout);

                    renderTimeout = $timeout(function () {
                        paper.clear();

                        var graphSet = paper.set();
                        var svg = document.querySelector("svg");
                        svg.removeAttribute("width");
                        svg.removeAttribute("height");

                        // we declare our settings here so they can be changed dynamically as needed
                        var settings = {
                            'xScale': 600,
                            'xOffset': 100,
                            'yScale': 500,
                            'yOffset': 90,
                            'padding': 20,
                            'rootNodeStyle': {
                                'fill': "#000"
                            },
                            'childNodeStyle': {
                                'fill': "#fff",
                                'stroke': "#000",
                                'stroke-width': 4
                            },
                            'endNodeStyle': {
                                'fill': "#666",
                                'stroke': '#000',
                                'stroke-width': 4
                            }
                        };

                        // draw our edges
                        for (var idx in graphData.edges) {
                            var edge = graphData.edges[idx];

                            drawEdge(paper, settings, edge, graphSet);
                        }

                        // draw our nodes
                        for (var idx in graphData.nodes) {
                            var node = graphData.nodes[idx];
                            switch (node["type"]) {
                                case "rootNode":
                                    drawRootNode(
                                        paper, settings, node, graphSet
                                    );
                                    break;
                                case "childNode":
                                    drawChildNode(
                                        paper, settings, node, graphSet
                                    );
                                    break;
                                case "endNode":
                                    drawEndNode(
                                        paper, settings, node, graphSet
                                    );
                                    break;
                            }

                            addNodeLabel(paper, settings, node, graphSet);
                        }

                        var paperBox = graphSet.getBBox();
                        var xPad = paperBox.x - settings['padding'];
                        var yPad = paperBox.y - settings['padding'];

                        paper.setViewBox(xPad, yPad, paperBox.width + (settings['padding'] * 2),
                            paperBox.height + (settings['padding'] * 2), true);
                        paper.setSize(paperBox.width + (settings['padding'] * 2),
                            paperBox.height + (settings['padding'] * 2));

                    }, 0);
                };

                /**
                 * Draws the root node on our canvas
                 * @param paper the Raphael instance
                 * @param settings the settings to use
                 * @param style the style to use for this node
                 * @param node the node to draw
                 */
                function drawRootNode(paper, settings, node, graphSet) {

                    var x = node['x'] * settings['xScale'] + settings['xOffset'];
                    var y = node['y'] * settings['yScale'] + settings['yOffset'];

                    var circle = paper.circle(x, y, 8);
                    circle.attr({'fill': '#000'});

                    graphSet.push(circle);
                }

                /**
                 * Draws the child node on our canvas
                 * @param paper the Raphael instance
                 * @param settings the settings to use
                 * @param style the style to use for this node
                 * @param node the node to draw
                 */
                function drawChildNode(paper, settings, node, graphSet) {
                    var x = node['x'] * settings['xScale'] + settings['xOffset'];
                    var y = node['y'] * settings['yScale'] + settings['yOffset'];

                    var circle = paper.circle(x, y, 8);
                    circle.attr({'fill': '#000'});
                    graphSet.push(circle);

                    var circle2 = paper.circle(x, y, 6);
                    circle2.attr({ 'fill': '#fff'});
                }

                /**
                 * Draws the end node on our canvas
                 * @param paper the Raphael instance
                 * @param settings the settings to use
                 * @param style the style to use for this node
                 * @param node the node to draw
                 */
                function drawEndNode(paper, settings, node, graphSet) {
                    var x = node['x'] * settings['xScale'] + settings['xOffset'];
                    var y = node['y'] * settings['yScale'] + settings['yOffset'];

                    var circle = paper.circle(x, y, 8);
                    circle.attr({'fill': '#000'});
                    graphSet.push(circle);

                    var circle2 = paper.circle(x, y, 6);
                    circle2.attr({'fill': '#fff'});

                    var circle3 = paper.circle(x, y, 4);
                    circle3.attr({'fill': '#000'});
                }

                /**
                 * Add a node label for the given now
                 * @param paper the Raphael instance
                 * @param settings the settings to use
                 * @param node the node to label
                 */
                function addNodeLabel(paper, settings, node, graphSet) {
                    var x = node['x'] * settings['xScale'] + settings['xOffset'];
                    var y = node['y'] * settings['yScale'] + settings['yOffset'] - 32;
                    var label = paper.text(x, y, node["label"]);


                    var maxWidth = (settings['xScale'] / 2);
                    // do some word wrapping here by testing the bounding box

                    var labelWords = node['label'].replace(/(\r\n|\n|\r)/gm, '').split(" ");
                    var wrappedText = '';
                    for (var idx in labelWords) {
                        label.attr("text", wrappedText + " " + labelWords[idx]);
                        if (label.getBBox().width > maxWidth) {
                            wrappedText += '\n' + labelWords[idx];
                        } else {
                            wrappedText += ' ' + labelWords[idx];
                        }
                    }
                    label.attr({
                        'font-size': 16
                    });
                    var bb = label.getBBox();
                    var h = Math.abs(bb.y2) - Math.abs(bb.y);
                    label.attr({
                        'y': node['y'] * settings['yScale'] + settings['yOffset'] - 16 - (h/2)
                    });
                    graphSet.push(label);
                }

                /**
                 * Draw an edge between two nodes
                 * @param paper the Raphael canvas
                 * @param settings our settings
                 * @param edge the edge we want to draw
                 */
                function drawEdge(paper, settings, edge, graphSet) {
                    var node1 = getNodeById(edge['source']);
                    var node2 = getNodeById(edge['target']);
                    if (!node1 || !node2) {
                        return;
                    }

                    var indent = settings['xScale'] /10;
                    var x1 = node1['x'] * settings['xScale'] + settings['xOffset'];
                    var y1 = node1['y'] * settings['yScale'] + settings['yOffset'];
                    var x2 = node2['x'] * settings['xScale'] + settings['xOffset'];
                    var y2 = node2['y'] * settings['yScale'] + settings['yOffset'];

                    var pathStr = "M" + x1 + "," + y1
                        + " C" + (x1 + indent) + "," + y1 + "," + x1 + ","
                        + y2 + "," + (x1 + indent) + "," + y2
                        + " L" + x2 + "," + y2;
                    graphSet.push(paper.path(pathStr).attr({'stroke': '#000'}));

                    addEdgeLabel(paper, settings, edge, (x1 + indent), y2);
                }

                /**
                 * Add a label to our edge
                 * @param paper the Raphael canvas
                 * @param settings our settings
                 * @param edge the edge we want to label
                 * @param x the base x coord of where the label goes
                 * @param y the base y coord of where the label goes
                 */
                function addEdgeLabel(paper, settings, edge, x, y) {
                    var labelOffsetX = settings['xScale'] / 100;
                    var labelOffsetY = settings['yScale'] / 100;
                    var maxWidth = (settings['xScale'] / 3) - (labelOffsetX * 3);

                    // anchor our text so it is left justified
                    var label = paper.text(x, y + labelOffsetY);
                    label.attr({
                        'text-anchor': 'start',
                    });

                    // do some word wrapping here by testing the bounding box
                    var labelWords = edge['label'].split(" ");
                    var wrappedText = '';
                    for (var idx in labelWords) {
                        label.attr("text", wrappedText + " " + labelWords[idx]);
                        if (label.getBBox().width > maxWidth) {
                            wrappedText += '\n' + labelWords[idx];
                        } else {
                            wrappedText += ' ' + labelWords[idx];
                        }
                    }

                    var bb = label.getBBox();
                    var h = Math.abs(bb.y2) - Math.abs(bb.y) + 1;
                    label.attr({
                        'y': bb.y + h
                    });
                }

                /**
                 * Find a node with a given ID
                 * @param id the ID to search for
                 * @returns {*}
                 */
                function getNodeById(id) {
                    for (var idx in graphData.nodes) {
                        if (graphData.nodes[idx]["id"] == id) {
                            return graphData.nodes[idx];
                        }
                    }

                    return null;
                }
            }
        }
    }

    angular.module('hermesApp').directive('fateGraph', fateGraph);
    fateGraph.$inject = ['HermesService', '$timeout', '$window'];
})();