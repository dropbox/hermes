(function() {
    'use strict';

    function FateCtrl(hermesService) {
        var vm = this;

        vm.paper = null;
        vm.panZoom = null;
        vm.graphData = null;

        vm.getGraphingData = getGraphingData;
        vm.getRawFates = getRawFates;

        getRawFates();
        getGraphingData();


        //////////////////////

        function getRawFates() {
            hermesService.getFates().then(function (fates) {
                vm.fates = fates;
            });
        }

        function getGraphingData() {
            hermesService.getFatesSigma().then(function (data) {
                vm.graphData = data;
                return data;
            }).then(function(graphData){
                // create our canvas
                var container = document.getElementById('fatesView');
                var width = container.clientWidth;
                var height = container.clientHeight;
                vm.paper = new Raphael(document.getElementById('fatesView'), width, height);
                redrawGraph();
            });

            function redrawGraph() {
                vm.paper.clear();

                // we declare our settings here so they can be changed dynamically as needed
                var settings = {
                    'xScale': 600,
                    'xOffset': 100,
                    'yScale': 500,
                    'yOffset': 140,
                    'rootNodeStyle': {
                        'fill': "#000"
                    },
                    'childNodeStyle': {
                        'fill': "#fff",
                        'stroke': "#000",
                        'stroke-width': 4,
                    },
                    'endNodeStyle': {
                        'fill': "#666",
                        'stroke': '#000',
                        'stroke-width': 4,
                    }
                };

                // draw our edges
                for (var idx in vm.graphData.edges) {
                    var edge = vm.graphData.edges[idx];

                    drawEdge(vm.paper, settings, edge);
                }

                // draw our nodes
                for (var idx in vm.graphData.nodes) {
                    var node = vm.graphData.nodes[idx];
                    switch (node["type"]) {
                        case "rootNode":
                            drawRootNode(
                                vm.paper, settings, node
                            );
                            break;
                        case "childNode":
                            drawChildNode(
                                vm.paper, settings, node
                            );
                            break;
                        case "endNode":
                            drawEndNode(
                                vm.paper, settings, node
                            );
                            break;
                    }

                    addNodeLabel(vm.paper, settings, node);
                }

                vm.paper.setViewBox(0, 0, vm.paper.width, vm.paper.height, true);
                vm.panZoom = vm.paper.panzoom({ initialZoom: 1, initialPosition: { x: 0, y: 0} });
                vm.panZoom.enable();
            }

            /**
             * Draws the root node on our canvas
             * @param paper the Raphael instance
             * @param settings the settings to use
             * @param style the style to use for this node
             * @param node the node to draw
             */
            function drawRootNode(paper, settings, node) {

                var x = node['x'] * settings['xScale'] + settings['xOffset'];
                var y = node['y'] * settings['yScale'] + settings['yOffset'];

                var circle = paper.circle(x, y, 8);
                circle.attr({'fill': '#000'});
            }

            /**
             * Draws the child node on our canvas
             * @param paper the Raphael instance
             * @param settings the settings to use
             * @param style the style to use for this node
             * @param node the node to draw
             */
            function drawChildNode(paper, settings, node) {
                var x = node['x'] * settings['xScale'] + settings['xOffset'];
                var y = node['y'] * settings['yScale'] + settings['yOffset'];

                var circle = paper.circle(x, y, 8);
                circle.attr({'fill': '#000'});

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
            function drawEndNode(paper, settings, node) {
                var x = node['x'] * settings['xScale'] + settings['xOffset'];
                var y = node['y'] * settings['yScale'] + settings['yOffset'];

                var circle = paper.circle(x, y, 8);
                circle.attr({'fill': '#000'});

                var circle2 = paper.circle(x, y, 6);
                circle2.attr({ 'fill': '#fff'});

                var circle3 = paper.circle(x, y, 4);
                circle3.attr({'fill': '#000'});
            }

            /**
             * Add a node label for the given now
             * @param paper the Raphael instance
             * @param settings the settings to use
             * @param node the node to label
             */
            function addNodeLabel(paper, settings, node) {
                var x = node['x'] * settings['xScale'] + settings['xOffset'];
                var y = node['y'] * settings['yScale'] + settings['yOffset'] - 32;
                var label = paper.text(x, y, node["label"].replace(' ', '\n'));
                label.attr({
                    'font-size': 16,
                });
            }

            /**
             * Draw an edge between two nodes
             * @param paper the Raphael canvas
             * @param settings our settings
             * @param edge the edge we want to draw
             */
            function drawEdge(paper, settings, edge) {
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
                    + " C" + (x1 + indent) + "," + y1 + "," + x1 + "," + y2 + "," + (x1 + indent) + "," + y2
                    + " L" + x2 + "," + y2;
                paper.path(pathStr).attr({'stroke': '#000'});

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
                for (var idx in vm.graphData.nodes) {
                    if (vm.graphData.nodes[idx]["id"] == id) {
                        return vm.graphData.nodes[idx];
                    }
                }

                return null;
            }
        }
    }

    angular.module('hermesApp').controller('FateCtrl', FateCtrl);
    FateCtrl.$inject = ['HermesService'];

})();