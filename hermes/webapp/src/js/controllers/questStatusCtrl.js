(function() {
    'use strict';

    function QuestStatusCtrl(hermesService, $q, $routeParams, $location, smoothScroll, $cookies) {
        var vm = this;

        vm.errorMessage = null; // here we store any error message to show the user
        vm.filterOwn = false;   // if true, user wants to filter quests by ones they created
        vm.filterByCreator = null;  // if set, user wants to filter quests by the creator specified
        vm.queryInput = null;   // if set, user wants to find quests related to machines returned by this query

        vm.domain = null;   // the domain name that hosts this instance of Hermes; ex: example.org
        vm.user = null;     // the currently authenticated user
        vm.questData = null;    // holds the raw quest overview data being displayed
        vm.selectedQuest = null;    // the quest selected for detailed view
        vm.selectedQuestDetails = null;     // the detailed data of the selected quest

        /*
            # of unique labors where a unique labor is designated as a starting labor.
            In other words, if labor B was created as a result of labor A being closed,
            then be count both of those as just 1 unique labor
         */
        vm.selectedQuestUniqueLabors = 0;

        /*
            An "in progress" labor is an open labor that was created after a previous
            labor was closed.
         */
        vm.selectedQuestInProgLabors = 0;

        /*
            Starting labors are those that were originally created when the quest was
            created.  They have no parent labor.
         */
        vm.selectedQuestStartingLabors = 0;

        /*
            Completed labors are closed labors that have no child labors.  So, if
            closing labor A created labor B and then labor B is now closed, this
            accounts for 1 completed labor (see above note on unique labors)
         */
        vm.selectedQuestCompletedLabors = 0;

        /*
          holds data on labors for the selected quest, sorted into buckets
          based on who is responsible for acting
         */
        vm.labors = null;

        vm.selectedLabors = [];     // the labors selected by clicking in the web ui

        vm.hostTags = null;     // host the server tags for hosts with labors in the selected quest
        vm.showHostTags = false;    // if true, the UI will display the server tags for the hosts in the selected quest
        vm.countByTypes = null;     // in the selected quest, the count of labors by event type; will be used for drawing status image
        vm.creatorThrowableTypes = null;    // holds the event types that a quest creator is allowed to throw; FIXME -- this sucks and should be based on labors
        vm.userThrowableTypes = null;   // hold the event types that a server owner is allowed to throw: FIXME -- this sucks and should be based on labors
        vm.selectedType = null; // the event type the user has picked from the UI to throw
        vm.throwableTypes = null;   // based on the user and his relationship to the selected quest, this is a pointer to one of the above throwable event type lists
        vm.createEventsModal = false;   // if true, show the "throw events" confirmation model
        vm.createInProgress = false;    // if true, event creation is in progress so block are further requests

        vm.limit = 10;  // the default # of quests to show on each page
        vm.offset = 0;  // the default offset for the quest list page
        vm.totalQuests = 10;    // the number of total quests found when filtered by the given parameters
        vm.messageSubject = null;   // the subject of the email message to send from the message block in the UI
        vm.messageEmail = null; // the body of the email message to send from the message block in the UI
        vm.showMessageBlock = false;    // if true, show the email message creation block

        /* pointers to our functions that we want to expose */
        vm.runNewFilter = runNewFilter;
        vm.getOpenQuests = getOpenQuests;
        vm.newQuestSelection = newQuestSelection;
        vm.goToCreatePage = goToCreatePage;
        vm.toggleSelect = toggleSelect;
        vm.filterOwnChanged = filterOwnChanged;
        vm.selectAll = selectAll;
        vm.deselectAll = deselectAll;
        vm.throwableTypesSelection = throwableTypesSelection;
        vm.createEvents = createEvents;
        vm.createQuestEmail = createQuestEmail;

        vm.selectOptions = {
            updateOn: 'default change blur',
            getterSetter: true,
            allowInvalid: true
        };

        // we track the "items per page" limit with cookies so grab any value we might have for this
        vm.limit = $cookies.get("pageLimit") ? $cookies.get("pageLimit") : 50;

        hermesService.getCurrentUser().then(function (user) {
            if (user) {
                vm.user = user;
            }

            if ($routeParams.byQuery) {
                vm.queryInput = $routeParams.byQuery;
            }

            // if user passed a filter-by-creator query param, that takes precedence.
            // otherwise, the default is to use the authenticate user
            if ($routeParams.byCreator || $routeParams.byCreator == "") {
                vm.filterByCreator = $routeParams.byCreator;
                vm.filterOwn = false;
            } else if (vm.user && !$routeParams.questId) {
                vm.filterByCreator = vm.user;
                vm.filterOwn = true;
            } else {
                vm.filterByCreator = "";
                vm.filterOwn = false;
            }

            getOpenQuests();
        });

        hermesService.getServerConfig().then(function(config) {
           vm.domain = config['domain'];
        });

        hermesService.getCreatorThrowableEventsTypes().then(function(types) {
            vm.creatorThrowableTypes = types;
        });

        hermesService.getUserThrowableEventTypes().then(function(types) {
            vm.userThrowableTypes = types;
        });


        //////// FIXME: Move to some kind of control service ///////
        vm.limitOptions = {
            updateOn: 'default change blur',
            getterSetter: true,
            allowInvalid: true
        };

        function limitSetting(limit) {
            if (angular.isDefined(limit)) {
                vm.limit = limit;
                vm.offset = 0;
                $cookies.put('pageLimit', limit);
            } else {
                return "" + vm.limit;
            }
        }

        function limitValues() {
            return ['10', '20', '50', '100', 'ALL'];
        }

        function pageSetting(page) {
            if (angular.isDefined(page)) {
                vm.offset = (page - 1) * vm.limit;
            } else {
                return "" + (vm.offset / vm.limit + 1);
            }
        }

        function pageFirst() {
            pageSetting(1);
        }

        function pagePrev() {
            var currentPage = parseInt(pageSetting());

            if (currentPage > 1) {
                pageSetting(currentPage - 1);
            }
        }

        function pageNext() {
            var currentPage = parseInt(pageSetting());
            var maxPage = Math.floor((vm.totalQuests - 1) / vm.limit) + 1;
            if (currentPage < maxPage) {
                pageSetting(currentPage + 1);
            }
        }

        function pageLast() {
            var maxPage = Math.floor((vm.totalQuests - 1) / vm.limit) + 1;
            pageSetting(maxPage);
        }

        function pageValues() {
            var maxPage = Math.floor((vm.totalQuests - 1) / vm.limit);
            var options = [];
            for (var i = 0; i <= maxPage; i++) {
                options.push("" + (i + 1));
            }

            return options;
        }

        vm.limitSetting = limitSetting;
        vm.limitValues = limitValues;
        vm.pageSetting = pageSetting;
        vm.pageFirst = pageFirst;
        vm.pagePrev = pagePrev;
        vm.pageNext = pageNext;
        vm.pageLast = pageLast;
        vm.pageValues = pageValues;

        ////////////////////////////////

        /**
         * Called when the user clicks the "show only my quests" checkbox.
         */
        function filterOwnChanged() {
            if (vm.filterOwn) {
                if (vm.user) {
                    vm.filterByCreator = vm.user;
                } else {
                    vm.filterOwn = false;
                    vm.errorMessage = "Your username is unknown.";
                }
            }
        }

        /**
         * Called when the user clicks "Create Quest" button
         */
        function goToCreatePage() {
            $location.url("/v1/quest/new");
        }

        /**
         * Called when user changes filtering settings and hits "GO" button
         */
        function runNewFilter() {
            $routeParams.questId = null;
            vm.offset = 0;
            vm.questData = null;
            vm.selectedQuest= null;
            getOpenQuests();
        }

        /**
         * Creates an email and sends it to all server owners participating in the selected quest
         */
        function createQuestEmail() {
            hermesService.createQuestEmail(
                vm.selectedQuestDetails['id'], vm.messageEmail,
                vm.messageSubject, vm.user, true, false
            )
                .then(function (response){
                    vm.createSuccessMessage = "Successfully sent email.";
                    vm.messageSubject = null;
                    vm.messageEmail = null;
                    vm.showMessageBlock = false;
                }).catch(function (error){
                    vm.createErrorMessage = "Email failed to send"
                })
        }

        /**
         * Get all the open quests, filtered by any settings the user has entered
         */
        function getOpenQuests() {
            vm.errorMessage = null;

            var options = {};
            if (vm.filterByCreator) {
                options['filterByCreator'] = vm.filterByCreator;
                $location.search('byCreator', vm.filterByCreator, false);
            } else {
                $location.search('byCreator', null, false);
            }

            if (vm.queryInput) {
                options['filterByQuery'] = vm.queryInput;
                $location.search('byQuery', vm.queryInput, false);
            } else {
                $location.search('byQuery', null, false);
            }

            hermesService.getOpenQuests(options).then(function (questData) {
                if (!questData
                    || !questData['quests']
                    || questData['quests'].length == 0) {
                    vm.errorMessage = "No Quests found matching criteria.  Please refine.";
                    return;
                }

                vm.questData = questData['quests'];
                vm.limit = questData['limit'] || vm.limit;
                vm.offset = questData['offset'] || vm.offset;
                vm.totalQuests = questData['totalQuests'] || vm.totalQuests;

                // see which quests are overdue
                for (var idx in vm.questData) {
                    evalDueDate(vm.questData[idx]);
                }

                // find the quest requested and make that the selection
                var index = -1;
                for (var idx in vm.questData) {
                    if (vm.questData[idx]['id'] == $routeParams.questId) {
                        index = idx;
                    }
                }

                if ($routeParams.questId && index == -1) {
                    vm.errorMessage = "Quest " + $routeParams.questId +
                            " not found.  Perhaps the quest is completed," +
                            " invalid, or has been filtered out."
                } else {
                    // if index is -1, then they likely didn't specify an id
                    if (index == -1) index = 0;
                    vm.offset = index - (index % vm.limit);
                    newQuestSelection(vm.questData[index]);
                }
            });
        }

        /**
         * Determine if the quest is overdue and add a property to indicate
         * @param quest the quest to analyze
         */
        function evalDueDate(quest) {
            if (quest.targetTime) {
                var dateRegex = /(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/;
                var dateArray = dateRegex.exec(quest.targetTime);
                var targetDate = new Date(
                    (+dateArray[1]),
                    (+dateArray[2]) - 1, // Careful, month starts at 0!
                    (+dateArray[3]),
                    (+dateArray[4]),
                    (+dateArray[5]),
                    (+dateArray[6])
                );

                if (targetDate - new Date() <= 0) quest.overDue = true;
                else quest.overDue = false;
            } else {
                quest.overDue = false;
            }
        }

        /**
         * Called when the user clicks on a quest in the left hand list.  This
         * quest now becomes the selected quest and additional details are loaded
         * for that quest including open labors, host owners, and host tags.
         * @param quest
         */
        function newQuestSelection(quest) {
            vm.errorMessage = null;
            vm.selectedQuest = quest;
            vm.selectedQuestDetails = null;
            vm.selectedQuestUniqueLabors = 0;
            vm.selectedQuestInProgLabors = 0;
            vm.selectedQuestStartingLabors = 0;
            vm.selectedQuestCompletedLabors = 0;
            vm.hostOwners = null;
            vm.hostTags = null;
            vm.labors = null;
            vm.selectedLabors = [];
            vm.countByTypes = null;

            // change the modal type and throwable events type
            if (vm.selectedQuest['creator'] == vm.user) {
                vm.throwableTypes = vm.creatorThrowableTypes;
            } else {
                vm.throwableTypes = vm.userThrowableTypes;
            }
            if (!vm.selectedType || vm.throwableTypes.indexOf(vm.selectedType) == -1) {
                vm.selectedType = vm.throwableTypes[0]
            }

            // Scroll back to the top of the page
            var detailsDiv = document.getElementById('quest-details');
            smoothScroll(detailsDiv, {duration: 700, easing: 'easeInOutQuad', offset: 100});

            // make an array of all the hostnames, and have the hermes service
            // give us back a hostname to owner mapping
            // NOTE: this will have duplicate entries for hostname because we
            // are using a list that has both open and closed labors.  But
            // the external querier should clean that up for us
            var hostnames = [];
            for (var idx in quest['labors']) {
                var hostname = quest['labors'][idx]['host']['hostname'];
                hostnames.push(hostname);
            }

            var get1 = hermesService.getOwnerInformation(hostnames);
            var get2 = hermesService.getQuestDetails(quest.id);

            $q.all([
                get1, get2
            ]).then(function(data) {
                vm.hostOwners = data[0];
                vm.selectedQuestDetails = data[1];
                evalDueDate(vm.selectedQuestDetails);

                $location.update_path('/v1/quests/' + quest.id, false);
                analyzeLabors(data[0], data[1]);
            });

            // get the host tags just in case the user wants to display them
            hermesService.getHostTags(hostnames).then(function(data) {
                vm.hostTags = data;
            }).catch(function(error){
                vm.errorMessage = "Could not load host tags: " + error.statusText;
            });
        }

        /**
         * Build the breakdown of the open labors, grouping by owner and then state
         * @param quest
         */
        function analyzeLabors(ownerData, questData) {
            if (!ownerData || !questData) {
                vm.errorMessage = "Failed to load data.  Please try again.";
                return;
            }

            vm.selectedQuestUniqueLabors = questData['totalLabors'];
            vm.selectedQuestStartingLabors = questData['unstartedLabors'];
            vm.selectedQuestInProgLabors = questData['inprogressLabors'];
            vm.selectedQuestCompletedLabors = questData['completedLabors'];

            // keep the latest labor with an given id or starting_labor_id
            // FIXME: This should all be done by the backend but isn't supported yet
            var laborsUnique  = {};
            var labors = questData['labors'];
            for (var idx in labors) {
                var id = labors[idx]['startingLaborId'] ? labors[idx]['startingLaborId'] : labors[idx]['id'];
                if (laborsUnique[id]) {
                    var timestamp = new Date(labors[idx]['creationTime'].replace(' ', 'T'));
                    var existing_timestamp = new Date(laborsUnique[id]['creationTime'].replace(' ', 'T'));
                    if (timestamp > existing_timestamp) {
                        laborsUnique[id] = labors[idx];
                    }
                } else {
                    laborsUnique[id] = labors[idx];
                }
            }

            // sort the unique labors into a buckets based on the owner and labor type
            var sortedLabors = {};
            vm.countByTypes = {};
            for (var idx in laborsUnique) {
                var hostname = laborsUnique[idx]['host']['hostname'];
                var owner = ownerData[hostname];
                var creator = questData['creator'];
                var forOwner = laborsUnique[idx]['forOwner'];
                var forCreator = laborsUnique[idx]['forCreator'];


                if (forOwner && !sortedLabors[owner]) {
                    sortedLabors[owner] = {};
                }

                if (forCreator && !sortedLabors[creator]) {
                    sortedLabors[creator] = {};
                }

                // if this labor is completed, we will file it by the completed event type
                if (laborsUnique[idx]['completionEvent']) {
                    var key = laborsUnique[idx]['completionEvent']['eventType']['description'];
                    // update the count of labors by type
                    vm.countByTypes[key] ? vm.countByTypes[key]++ : vm.countByTypes[key] = 1;

                    // sort into the bucket for this owner, if the labor is for the server owner
                    if (forOwner) {
                        if (sortedLabors[owner][key]) {
                            sortedLabors[owner][key]['count']++;
                            sortedLabors[owner][key]['hosts'].push(
                                {
                                    'hostname': laborsUnique[idx]['host']['hostname'],
                                    'laborId': laborsUnique[idx]['id']
                                }
                            )
                        } else {
                            sortedLabors[owner][key] = {
                                'count': 1,
                                'hosts': [
                                    {
                                        'hostname': laborsUnique[idx]['host']['hostname'],
                                        'laborId': laborsUnique[idx]['id']
                                    }
                                ]
                            }
                        }
                    }

                    // sort into the bucket for the quest creator, if this labor is for the quest creator
                    if (forCreator) {
                        if (sortedLabors[creator][key]) {
                            sortedLabors[creator][key]['count']++;
                            sortedLabors[creator][key]['hosts'].push(
                                {
                                    'hostname': laborsUnique[idx]['host']['hostname'],
                                    'laborId': laborsUnique[idx]['id']
                                }
                            )
                        } else {
                            sortedLabors[creator][key] = {
                                'count': 1,
                                'hosts': [
                                    {
                                        'hostname': laborsUnique[idx]['host']['hostname'],
                                        'laborId': laborsUnique[idx]['id']
                                    }
                                ]
                            }
                        }
                    }

                } else { // for incomplete labors, file by the creating event type
                    //var creationEventType = laborsUnique[idx]['creationEvent']['eventType'];
                    //var key = creationEventType['category'] + " " + creationEventType['state'];
                    var key = laborsUnique[idx]['fate']['description'];

                    // update the count of labors by type
                    vm.countByTypes[key] ? vm.countByTypes[key]++ : vm.countByTypes[key] = 1;

                    // sort into the bucket for the server owner if the labor is for the owner
                    if (forOwner) {
                        if (sortedLabors[owner][key]) {
                            sortedLabors[owner][key]['count']++;
                            sortedLabors[owner][key]['hosts'].push(
                                {
                                    'hostname': laborsUnique[idx]['host']['hostname'],
                                    'laborId': laborsUnique[idx]['id']
                                }
                            )
                        } else {
                            sortedLabors[owner][key] = {
                                'count': 1,
                                'hosts': [
                                   {
                                        'hostname': laborsUnique[idx]['host']['hostname'],
                                        'laborId': laborsUnique[idx]['id']
                                    }
                                ]
                            }
                        }
                    }

                    // sort into the bucket for the quest creator if the labor is designate for them
                    if (forCreator) {
                        if (sortedLabors[creator][key]) {
                            sortedLabors[creator][key]['count']++;
                            sortedLabors[creator][key]['hosts'].push(
                                {
                                    'hostname': laborsUnique[idx]['host']['hostname'],
                                    'laborId': laborsUnique[idx]['id']
                                }
                            )
                        } else {
                            sortedLabors[creator][key] = {
                                'count': 1,
                                'hosts': [
                                    {
                                        'hostname': laborsUnique[idx]['host']['hostname'],
                                        'laborId': laborsUnique[idx]['id']
                                    }
                                ]
                            }
                        }
                    }
                }
            }

            vm.labors = sortedLabors;
        }

        /**
         * Toggle a labor selection
         * @param hostname hostname of the labor to select
         */
        function toggleSelect(hostname) {
            var idx = vm.selectedLabors.indexOf(hostname);
            if (idx != -1) {
                vm.selectedLabors.splice(idx, 1)
            } else {
                vm.selectedLabors.push(hostname);
            }
        }

        /**
         * Select all the labors on this screen and add them to the list
         * of selected labors
         */
        function selectAll() {
            for (var idx in vm.labors) {
                for (var idy in vm.labors[idx]) {
                    for (var idz in vm.labors[idx][idy]["hosts"]) {
                        if (vm.selectedLabors.indexOf(vm.labors[idx][idy]["hosts"][idz]["hostname"]) == -1) {
                            vm.selectedLabors.push(vm.labors[idx][idy]["hosts"][idz]["hostname"]);
                        }
                    }
                }
            }
        }

         /**
         * Deselect all the labors on this screen and remove them to the list
         * of selected labors
         */
        function deselectAll() {
            vm.selectedLabors = [];
        }

        /**
         * The getter/setter for event types
         */
        function throwableTypesSelection(selection) {
            if (angular.isDefined(selection)) {
                vm.selectedType = selection;
            } else {
                return vm.selectedType;
            }
        }

        /**
         * Create events for the selected hosts
         */
        function createEvents() {
            if (vm.createInProgress) return;
            vm.createEventsModal = false;
            vm.createInProgress = true;
            vm.createErrorMessage = null;
            vm.createSuccessMessage = null;

            if (!vm.selectedLabors) {
                return;
            }

            vm.result = hermesService.createEvents(
                vm.user, vm.selectedLabors, vm.selectedType,
                "Created by " + vm.user + " via Web UI."
            )
                .then(function(response) {
                    vm.createInProgress = false;
                    vm.selected = [];
                    vm.createSuccessMessage = "Successfully created events.";
                    newQuestSelection(vm.selectedQuest);
                })
                .catch(function(error) {
                    vm.createInProgress = false;
                    vm.createErrorMessage ="Event creation failed!  " + error.statusText;
                });

        }
    }

    angular.module('hermesApp').controller('QuestStatusCtrl', QuestStatusCtrl);
    QuestStatusCtrl.$inject = [
        'HermesService',
        '$q',
        '$routeParams',
        '$location',
        'smoothScroll',
        '$cookies'
    ];
})();
