(function() {

    'use strict';

    function HermesService($http, $q) {
        var fates;
        var service = {
            getFates: getFates,
            getFatesSigma: getFatesSigma,
            getOpenQuests: getOpenQuests,
            getQuestDetails: getQuestDetails,
            getOwnerInformation: getOwnerInformation
        };

        return service;

        /////////////////////////

        /**
         * Get a list of all the open quests but not all the details --
         * just enough to give overview information.
         * @returns {*}
         */
        function getOpenQuests(options) {

            var url = "/api/v1/quests?filterClosed=true&progressInfo=true&expand=hosts&expand=labors&limit=all";

            if (options['filterByCreator']) {
                url += "&byCreator=" + options['filterByCreator'];
            }
            return $http.get(url)
                .then(getQuestsComplete)
                .catch(getQuestsFailed);

            function getQuestsComplete(response) {
                return response.data;
            }

            function getQuestsFailed(error) {
                console.error("API call to get open Quests failed. " + error.status + " " + error.statusText);
            }
        }

        /**
         * Grab all the details for a given quest (labors, events and eventtypes)
         * @param id the id of the quest we care about
         */
        function getQuestDetails(id) {
            return $http.get("/api/v1/quests/" + id + "/?progressInfo=true&limit=all&expand=labors&expand=hosts&expand=events&expand=eventtypes")
                .then(getQuestComplete)
                .catch(getQuestFailed);

            function getQuestComplete(response) {
                return response.data;
            }

            function getQuestFailed(error) {
                console.error("API call to get details of Quest " + id + " failed: "  + error.status + " " + error.statusText);
            }
        }

        function getOwnerInformation(hostnames) {
            return $http.post("/api/v1/extquery", {"hostnames": hostnames})
                .then(getOwnersComplete)
                .catch(getOwnersFailed);

            function getOwnersComplete(response) {
                return response.data.results;
            }

            function getOwnersFailed(error) {
                console.error("API to get owners failed: " + error.status + " " + error.statusText);
            }
        }

        function getFates() {
            return $http.get("/api/v1/fates?expand=eventtypes&limit=all")
                .then(getFatesComplete)
                .catch(getFatesFailed);

            function getFatesComplete(response) {
                //console.debug("Got Fates! " + response.data.fates);
                return response.data.fates;
            }

            function getFatesFailed(error) {
                console.error("API call to get Fates failed. "  + error.status + " " + error.statusText)
            }
        }

        /**
         * Get the fates but return them as a JSON that's consumable by SigmaJS
         */
        function getFatesSigma() {
            var graphData = {
                    nodes: [],
                    edges: []
                };

            var XINC = 0.5;
            var YINC = .2;
            var baseY = 0;  // used to track y coords when laying out graph

            return getFates().then(processFates).then(function() {
                var baseX = 0;

                // Go back through the nodes and assign them coordinates for
                // display
                for (var idx in graphData.nodes) {
                    if (graphData.nodes[idx]["id"][0] == "r") {
                        layoutGraph(baseX, graphData.nodes[idx]);
                    }
                }

            })
                .then(function() {
                return graphData;
            });


            function processFates(fates) {
                // first, let's graph out the nodes and the edges,
                // but we won't add positions until afterwards
                for (var x in fates) {
                    var rootId;
                    if (!fates[x]["follows_id"]) {
                        rootId = createRootNode(fates[x]["creationEventType"]);
                    } else {
                        rootId = "f" + fates[x]["follows_id"] + "c";
                    }
                    var childId = createChildNode(
                        fates[x]["completionEventType"],
                        fates[x]["id"]
                    );
                    createEdge(
                        fates[x]["id"], rootId, childId,
                        fates[x]["description"]
                    );
                }
            }


            /**
             * Create a node that will be the start of a chain
             */
            function createRootNode(creationEventType) {
                console.debug("Adding root node " + creationEventType["id"])
                var id = 'r' + creationEventType["id"];

                for (var node_id in graphData.nodes) {
                    if (graphData.nodes[node_id]["id"] == id) {
                        // we found an existing node with the same id
                        // so we must already have this defined. Exit
                        return id;
                    }
                }

                // not having found a matching node, we will create one
                var node = {
                    id: id,
                    size: 1,
                    type: 'rootNode',
                    label: creationEventType["category"] + ' ' + creationEventType["state"]
                };

                graphData.nodes.push(node);

                return id;
            }

            /**
             * Create a node that will be a child of the fate identified
             */
            function createChildNode(completionEventType, fateId) {
                var id = "f" + fateId + "c";

                var node = {
                    id: id,
                    size: 1,
                    type: 'childNode',
                    label: completionEventType["category"] + ' ' + completionEventType["state"]
                };

                graphData.nodes.push(node);

                return id;
            }

            /**
             * Create an edge between two nodes
             */
            function createEdge(fateId, nodeId1, nodeId2, desc) {
                var edge = {
                    id: "fe" + fateId,
                    source: nodeId1,
                    target: nodeId2,
                    type: 'fateFlow',
                    label: desc
                };

                graphData.edges.push(edge);
            }

            /**
             * Go back through the nodes and assign them coordinates for
             * display
             */
            function layoutGraph(baseX, node) {
                // update the x and y coords of this node
                node["x"] = baseX;
                node["y"] = baseY;

                // all children will be to the right
                baseX += XINC;

                // find all children and iterate
                var foundChildren = false;
                for (var idx in graphData.edges) {
                    if (graphData.edges[idx]["source"] == node["id"]) {
                        var childNode = findNode(graphData.edges[idx]["target"])
                        if (childNode) {
                            foundChildren = true;
                            layoutGraph(baseX, childNode);
                            baseY += YINC;
                        }
                    }
                }

                if (!foundChildren) {
                    node["type"] = "endNode";
                }
            }

            /**
             * Quick way to search and find the node with a given ID
             */
            function findNode(searchId) {
                for (var idx in graphData.nodes) {
                    if (graphData.nodes[idx]["id"] == searchId) {
                        return graphData.nodes[idx];
                    }
                }

                return null;
            }
        }
    }

    angular.module('hermesApp')
        .factory('HermesService',HermesService);

    HermesService.$inject = ["$http", "$q"];

})();