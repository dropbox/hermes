(function() {

    'use strict';

    function HermesService($http, $q) {
        var fates = null;
        var fatesGraph = null;
        var serverConfig = null;
        var currentUser = null;
        var service = {
            getFates: getFates,
            getFatesGraph: getFatesGraph,
            getOpenLabors: getOpenLabors,
            getOpenQuests: getOpenQuests,
            getQuestDetails: getQuestDetails,
            getOwnerInformation: getOwnerInformation,
            getHostTags: getHostTags,
            getCurrentUser: getCurrentUser,
            getAllEventTypes: getAllEventTypes,
            getStartingEventTypes: getStartingEventTypes,
            getUserThrowableEventTypes: getUserThrowableEventTypes,
            getCreatorThrowableEventsTypes: getCreatorThrowableEventTypes,
            getQuestCreatorThrowableEventTypes: getQuestCreatorThrowableEventTypes,
            runQuery: runQuery,
            createQuest: createQuest,
            createQuestEmail: createQuestEmail,
            updateQuest: updateQuest,
            createEvents: createEvents,
            getServerConfig: getServerConfig
        };

        getServerConfig().then(function(config) {
            if (config['fullstoryId']) {
                window['_fs_debug'] = false;
                window['_fs_host'] = 'www.fullstory.com';
                window['_fs_org'] = config['fullstoryId'];
                (function(m,n,e,t,l,o,g,y){
                  g=m[e]=function(a,b){g.q?g.q.push([a,b]):g._api(a,b);};g.q=[];
                  o=n.createElement(t);o.async=1;o.src='https://'+_fs_host+'/s/fs.js';
                  y=n.getElementsByTagName(t)[0];y.parentNode.insertBefore(o,y);
                  g.identify=function(i,v){g(l,{uid:i});if(v)g(l,v)};g.setUserVars=function(v){FS(l,v)};
                  g.identifyAccount=function(i,v){o='account';v=v||{};v.acctId=i;FS(o,v)};
                  g.clearUserCookie=function(d,i){d=n.domain;while(1){n.cookie='fs_uid=;domain='+d+
                  ';path=/;expires='+new Date(0);i=d.indexOf('.');if(i<0)break;d=d.slice(i+1)}}
                })(window,document,'FS','script','user');
            }
        });

        return service;

        /////////////////////////

        /**
         * Try to create a quest given the information
         * @param user the user who is the owner/creator of the quest
         * @param hosts the list of hosts to which this quest applies
         * @param fateId the ID for the Fate to use to start the quest
         * @param targetDateTime the date and time the quest should complete
         * @param description the human readable description for this quest
         */
        function createQuest(user, hosts, fateId, targetDateTime, description) {
            return $http.post("/api/v1/quests", {
                'creator': user,
                'hostnames': hosts,
                'fateId': fateId,
                'targetTime': targetDateTime,
                'description': description
            }).then(createQuestCompleted)
                .catch(createQuestFailed);

            function createQuestCompleted(response) {
                return response;
            }

            function createQuestFailed(error) {
                console.error("API for creating a quest failed! " + error.status + " " + error.statusText);
                throw error;
            }
        }

        /**
         * Try to send an email to server or labor owners for a given quest
         * @param questId ID for the quest to email about
         * @param message message to send to server or labor owners
         * @param subject subject of message to send
         * @param sender email address to send from
         * @param serverOwners boolean to send or not send to server owners
         * @param laborOwners boolean to send or not send to labor owners
         * @returns {*}
         */
        function createQuestEmail(questId, message, subject, sender, serverOwners, laborOwners) {
            return $http.post("/api/v1/quests/" + questId + "/mail", {
                'serverOwners': serverOwners,
                'laborOwners': laborOwners,
                'from': sender,
                'subject': subject,
                'message': message
            }).then(createQuestEmailCompleted)
                .catch(createQuestEmailFailed);

            function createQuestEmailCompleted(response) {
                console.log("hermes service: message sent")
                return response;
            }

            function createQuestEmailFailed(error) {
                console.error("API for creating a quest email failed! " + error.status + " " + error.statusText);
                throw error;
            }
        }

        /**
         * Update a given quest with new values
         * @param questId the id of the quest to update
         * @param fields hash of fields to update.  Should only contain "owner", "description", and/or "targetTime"
         */
        function updateQuest(questId, fields) {
            var json = {};
            if ("creator" in fields) {
                json["creator"] = fields["creator"];
            }
            if ("description" in fields) {
                json["description"] = fields["description"];
            }
            if ("targetTime" in fields) {
                json["targetTime"] = fields["targetTime"];
            }

            return $http.put("/api/v1/quests/" + questId, json)
                .then(updateQuestCompleted)
                .catch(updateQuestFailed);

            function updateQuestCompleted(response) {
                return response;
            }

            function updateQuestFailed(error) {
                console.error("API for updating a quest failed! " + error.status + " " + error.statusText);
                throw error;
            }
        }

        /**
         * Try to create events for the given hsots
         * @param user the authenticated user creating these events
         * @param hosts the list of hosts we want to create these events for
         * @param eventType the eventtype of the event to create
         * @param note the note to put with the event
         */
        function createEvents(user, hosts, eventType, note) {
            return $http.post("/api/v1/events", {
                'user': user,
                'hostnames': hosts,
                'eventTypeId': eventType.id,
                'note': note
            }).then(createQuestCompleted)
                .catch(createQuestFailed);

            function createQuestCompleted(response) {
                return response;
            }

            function createQuestFailed(error) {
                console.error("API for creating a quest failed! " + error.status + " " + error.statusText);
                throw error;
            }
        }


        /**
         * Get the current authenticated user
         */
        function getCurrentUser() {
            if (currentUser != null) {
                return currentUser;
            } else {
                currentUser = $http.get("/api/v1/currentUser")
                .then(getCurrentUserComplete)
                .catch(getCurrentUserFailed);

                return currentUser;
            }

            function getCurrentUserComplete(response) {
                if (response.data['user']) {
                    serverConfig.then(function(config) {
                        if (config['fullstoryId']) {
                            FS.identify(response.data['user'], {});
                        }
                    });

                    return response.data['user'];
                } else {
                    return null;
                }
            }

            function getCurrentUserFailed(error) {
                console.error("API call to get open current user. " + error.status + " " + error.statusText);
            }
        }

        /**
         * Get a list of all open labors, along with quest details
         */
        function getOpenLabors(options) {

            var url;
            if (options['overviewOnly']) {
                url = "/api/v1/labors/?open=true";
            } else {
                url = "/api/v1/labors/?open=true&expand=hosts&limit=all&expand=quests&expand=events&expand=eventtypes&expand=fates";
            }

            if (options['filterByOwner']) {
                url += "&userQuery=" + encodeURIComponent(options['filterByOwner']);
            }

            if (options['filterByQuery']) {
                url += "&hostQuery=" + encodeURIComponent(options['filterByQuery']);
            }

            if (options['filterByCategory']) {
                url += "&category=" + encodeURIComponent(options['filterByCategory']);
            }

            if (options['filterByState']) {
                url += "&state=" + encodeURIComponent(options['filterByState']);
            }

            if (options['filterByHostname']) {
                url += "&hostname=" + encodeURIComponent(options['filterByHostname']);
            }

            return $http.get(url)
                .then(getLaborsComplete)
                .catch(getLaborsFailed);

            function getLaborsComplete(response) {
                return response.data;
            }

            function getLaborsFailed(error) {
                console.error("API call to get open labors failed. " + error.status + " " + error.statusText);
                throw error;
            }
        }

        /**
         * Get a list of all the open quests but not all the details --
         * just enough to give overview information.
         * @returns {*}
         */
        function getOpenQuests(options) {

            var url;
            if (options['overviewOnly']) {
                url = "/api/v1/quests?filterClosed=true&limit=all"
            } else {
                url = "/api/v1/quests?filterClosed=true&progressInfo=true&expand=hosts&expand=labors&limit=all";
            }

            if (options['filterByCreator']) {
                url += "&byCreator=" + encodeURIComponent(options['filterByCreator']);
            }

            if (options['filterByQuery']) {
                url += "&hostQuery=" + encodeURIComponent(options['filterByQuery']);
            }

            return $http.get(url)
                .then(getQuestsComplete)
                .catch(getQuestsFailed);

            function getQuestsComplete(response) {
                return response.data;
            }

            function getQuestsFailed(error) {
                console.error("API call to get open Quests failed. " + error.status + " " + error.statusText);
                throw error;
            }
        }

        /**
         * Grab all the details for a given quest (labors, events and eventtypes)
         * @param id the id of the quest we care about
         */
        function getQuestDetails(id) {
            return $http.get("/api/v1/quests/" + id + "/?progressInfo=true&limit=all&expand=labors&expand=hosts&expand=events&expand=eventtypes&expand=fates")
                .then(getQuestComplete)
                .catch(getQuestFailed);

            function getQuestComplete(response) {
                return response.data;
            }

            function getQuestFailed(error) {
                console.error("API call to get details of Quest " + id + " failed: "  + error.status + " " + error.statusText);
            }
        }

        /**
         * Get the owner information for the hosts we care about
         * @param hostnames the hostnames of the hosts we care about
         * @returns {*}
         */
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

        /**
         * Get tags for each of the hosts
         * @param hostnames the hostnames of the hosts we care about
         * @returns {*}
         */
        function getHostTags(hostnames) {
            return $http.post("/api/v1/extquery", {"hostnames": hostnames, "operation": "tags"})
                .then(getTagsComplete)
                .catch(getTagsFailed);

            function getTagsComplete(response) {
                return response.data.results;
            }

            function getTagsFailed(error) {
                console.error("API to get host tags failed: " + error.status + " " + error.statusText);
            }
        }

        /**
         * Get all fates, for references
         * @returns {*}
         */
        function getFates() {
            if (fates) {
                var promise = $q.defer();
                promise.resolve(fates);
                return promise.promise;
            }
            return $http.get("/api/v1/fates?expand=eventtypes&limit=all")
                .then(getFatesComplete)
                .catch(getFatesFailed);

            function getFatesComplete(response) {
                fates = response.data.fates;
                return fates;
            }

            function getFatesFailed(error) {
                console.error("API call to get Fates failed. "  + error.status + " " + error.statusText)
            }
        }

        /**
         * Get the fates and return them in a graph format
         */
        function getFatesGraph() {
            if (fatesGraph) {
                var promise = $q.defer();
                promise.resolve(fatesGraph);
                return promise.promise;
            }
            var graphData = {
                    nodes: [],
                    edges: []
                };

            var XINC = 0.5;
            var YINC = .2;

            return getFates().then(processFates).then(function() {
                var baseX = 0;
                var baseY = 0; // used to track y coords when laying out graph

                // Go back through the nodes and assign them coordinates for
                // display
                for (var idx in graphData.nodes) {
                    if (graphData.nodes[idx]["type"] == "rootNode") {
                        baseY = layoutGraph(baseX, baseY, graphData.nodes[idx]);
                        baseY += YINC;
                    }
                }
            }).then(function() {
                fatesGraph = graphData;
                return graphData;
            });

            /**
             * Process the fates into a nice node-link map
             * @param fates fates to process
             */
            function processFates(fates) {
                // first, let's graph out the nodes and the edges,
                // but we won't add positions until afterwards
                for (var x in fates) {
                    if (!fates[x]["followsId"]) {
                        parseFate(fates, fates[x])
                    }
                }

                function parseFate(fates, fate) {
                    var rootId;
                    if (!fate["followsId"]) {
                        rootId = createNode(fate['id'], 'rootNode', fate['description']);
                    } else {
                        rootId = createNode(fate['id'], 'childNode', fate['description']);
                    }

                    var children = [];
                    for (var x in fates) {
                        if (fate['precedesIds'].indexOf(fates[x]['id']) != -1) {
                            var childId = parseFate(fates, fates[x]);
                            children.push(childId);
                            createEdge(rootId, childId, fates[x]['creationEventType']);
                        }
                    }

                    return rootId;
                }
            }

            /**
             * Create a node for the node-edge fates graph
             */
            function createNode(fateId, nodeType, fateDesc) {
                var id = 'f' + fateId;

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
                    type: nodeType,
                    label: fateDesc,
                };

                graphData.nodes.push(node);

                return id;
            }

            /**
             * Create an edge between two nodes
             */
            function createEdge(nodeId1, nodeId2, completionEventType) {
                var edge = {
                    id: "edge" + nodeId1 + nodeId2,
                    source: nodeId1,
                    target: nodeId2,
                    type: 'fateFlow',
                    label: completionEventType['category'] + " " + completionEventType['state']
                };

                graphData.edges.push(edge);
            }

            /**
             * Go back through the nodes and assign them coordinates for
             * display
             */
            function layoutGraph(baseX, baseY, node) {
                // update the x and y coords of this node
                node["x"] = baseX;
                node["y"] = baseY;

                // all children will be to the right
                baseX += XINC;

                // find all children and iterate
                var foundChildren = false;
                var firstChild = true;
                for (var idx in graphData.edges) {
                    if (graphData.edges[idx]["source"] == node["id"]) {
                        var childNode = findNode(graphData.edges[idx]["target"])
                        if (childNode) {
                            foundChildren = true;
                            if (!firstChild) {
                                baseY += YINC;
                            } else {
                                firstChild = false;
                            }
                            baseY = layoutGraph(baseX, baseY, childNode);
                        }
                    }
                }

                if (!foundChildren) {
                    node["type"] = "endNode";
                }

                return baseY;
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

        /**
         * Get a list of event types that can start non-intermediate labors
         * @returns {*}
         */
        function getStartingEventTypes() {
            return $http.get("/api/v1/eventtypes?startingTypes=true&limit=all")
                .then(getStartingEventTypesComplete)
                .catch(getStartingEventTypesFailed);

            function getStartingEventTypesComplete(response) {
                return response.data.eventTypes;
            }

            function getStartingEventTypesFailed(error) {
                console.error("API call to get starting EventTypes failed. "
                    + error.status + " " + error.statusText);
                throw error;
            }
        }


        /**
         * Get all event-types that users are allowed to throw.  Basically,
         * this is any event-type of state "ready."
         * @returns {*}
         */
        function getUserThrowableEventTypes() {
            return $http.get("/api/v1/eventtypes?limit=all&state=acknowledge")
                .then(getCompleted)
                .catch(getFailed);

            function getCompleted(response) {
                return response.data.eventTypes;
            }

            function getFailed(error) {
                console.error("API call to get user throwable event-types failed. "
                    + error.status + " " + error.statusText);
                throw error;
            }
        }

        /**
         * Get all event-types that quest creators are allowed to throw.  Basically,
         * this is any event-type of state "completed."
         * @returns {*}
         */
        function getCreatorThrowableEventTypes() {
            return $http.get("/api/v1/eventtypes?limit=all&state=completed")
                .then(getCompleted)
                .catch(getFailed);

            function getCompleted(response) {
                return response.data.eventTypes;
            }

            function getFailed(error) {
                console.error("API call to get creator throwable event-types failed. "
                    + error.status + " " + error.statusText);
                throw error;
            }
        }

        function getAllEventTypes() {
            return $http.get("/api/v1/eventtypes?limit=all")
                .then(getCompleted)
                .catch(getFailed);

            function getCompleted(response) {
                return response.data.eventTypes;
            }

            function getFailed(error) {
                console.error("API call to get all event-types failed. "
                    + error.status + " " + error.statusText);
                throw error;
            }
        }

        /**
         * Get all event-types that quest creators are allowed to throw.  Basically,
         * this is any event-type of state "completed."
         * @returns {*}
         */
        function getQuestCreatorThrowableEventTypes() {
            return $http.get("/api/v1/eventtypes?limit=all&state=completed")
                .then(getCompleted)
                .catch(getFailed);

            function getCompleted(response) {
                return response.data.eventTypes;
            }

            function getFailed(error) {
                console.error("API call to get creator throwable event-types failed. "
                    + error.status + " " + error.statusText);
                throw error;
            }
        }

        /**
         * Run a given query against the extquery passthrough service
         * @param queryString the string to run
         * @returns {*}
         */
        function runQuery(queryString) {
            return $http.get("/api/v1/extquery?query=" + encodeURIComponent(queryString))
                .then(runQueryComplete)
                .catch(runQueryFailed);

            function runQueryComplete(response) {
                return response.data.results.sort();
            }

            function runQueryFailed(error) {
                console.error("API call to get run query failed. "  + error.status + " " + error.statusText);
                throw error;
            }
        }

        /**
         * Get the server's config.
         * @returns a config promise
         */
        function getServerConfig() {
            if (serverConfig == null) {
                serverConfig = $http.get("/api/v1/serverConfig")
                    .then(function(response) {
                    return response.data
                });
            }
            return serverConfig;
        }
    }

    angular.module('hermesApp')
        .factory('HermesService',HermesService);

    HermesService.$inject = ["$http", "$q"];

})();