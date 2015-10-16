(function() {
    'use strict';

    function QuestStatusCtrl(hermesService, $q, $routeParams, $location, smoothScroll) {
        var vm = this;

        vm.errorMessage = null;
        vm.filterOwn = false;
        vm.filterByCreator = null;
        vm.queryInput = null;

        vm.domain = null;
        vm.user = null;
        vm.questData = null;
        vm.selectedQuest = null;
        vm.selectedQuestDetails = null;
        vm.selectedQuestUniqueLabors = 0;
        vm.selectedQuestInProgLabors = 0;
        vm.selectedQuestStartingLabors = 0;
        vm.selectedQuestCompletedLabors = 0;
        vm.labors = null;
        vm.selectedLabors = [];
        vm.types = null;
        vm.selectedEventType = null;
        vm.throwableTypes = null;
        vm.createEventsModal = false;
        vm.createInProgress = false;
        vm.limit = 10;
        vm.offset = 0;
        vm.totalQuests = 10;

        vm.colors = ['#688ab4', '#9cbfea', '#232f3e', '#7e8184'];

        vm.runNewFilter = runNewFilter;
        vm.getOpenQuests = getOpenQuests;
        vm.newQuestSelection = newQuestSelection;
        vm.goToCreatePage = goToCreatePage;
        vm.toggleSelect = toggleSelect;
        vm.filterOwnChanged = filterOwnChanged;
        vm.selectAll = selectAll;
        vm.deselectAll = deselectAll;
        vm.throwableEventTypesSelection = throwableEventTypesSelection;
        vm.createEvents = createEvents;

        vm.selectOptions = {
            updateOn: 'default change blur',
            getterSetter: true,
            allowInvalid: true
        };

        hermesService.getCurrentUser().then(function (user) {
            if (user) {
                vm.user = user;
            }

            if ($routeParams.byQuery) {
                vm.queryInput = $routeParams.byQuery;
            }

            // if user passed a filter-by-creator query param, that takes precedence.
            // otherwise, the default is to use the authenticate user
            if ($routeParams.byCreator) {
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
            vm.throwableTypes = types;
            vm.throwableEventTypesSelection(vm.throwableTypes[0])
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

        function goToCreatePage() {
            $location.url("/v1/quest/new");
        }

        function runNewFilter() {
            $routeParams.questId = null;
            vm.offset = 0;
            vm.questData = null;
            vm.selectedQuest= null;
            getOpenQuests();
        }

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
                    var quest = vm.questData[idx];
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

        function newQuestSelection(quest) {
            var detailsDiv = document.getElementById('quest-details');
            smoothScroll(detailsDiv, {duration: 700, easing: 'easeInOutQuad', offset: 100});
            vm.selectedQuest = quest;
            vm.selectedQuestDetails = null;
            vm.selectedQuestUniqueLabors = 0;
            vm.selectedQuestInProgLabors = 0;
            vm.selectedQuestStartingLabors = 0;
            vm.selectedQuestCompletedLabors = 0;
            vm.hostOwners = null;
            vm.labors = null;
            vm.selectedLabors = [];
            vm.types = null;

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

                $location.update_path('/v1/quests/' + quest.id, false);
                analyzeLabors(data[0], data[1]);
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
            vm.selectedQuestUniqueLabors = Object.keys(laborsUnique).length;
            vm.types = {};
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

                // if this labor is completed, we will file it by the complete event type
                if (laborsUnique[idx]['completionEvent']) {
                    vm.selectedQuestCompletedLabors++;
                    var completionEventType = laborsUnique[idx]['completionEvent']['eventType'];
                    var key = completionEventType['category'] + " " + completionEventType['state'];
                    // update the count of labors by type
                    vm.types[key] ? vm.types[key]++ : vm.types[key] = 1;

                    // sort into the bucket for this owner, if the labor is for the server owner
                    if (forOwner) {
                        if (sortedLabors[owner][key]) {
                            sortedLabors[owner][key]['count']++;
                            sortedLabors[owner][key]['hosts'].push(
                                laborsUnique[idx]['host']['hostname']
                            )
                        } else {
                            sortedLabors[owner][key] = {
                                'count': 1,
                                'hosts': [laborsUnique[idx]['host']['hostname']]
                            }
                        }
                    }

                    // sort into the bucket for the quest creator, if this labor is for the quest creator
                    if (forCreator) {
                        if (sortedLabors[creator][key]) {
                            sortedLabors[creator][key]['count']++;
                            sortedLabors[creator][key]['hosts'].push(
                                laborsUnique[idx]['host']['hostname']
                            )
                        } else {
                            sortedLabors[creator][key] = {
                                'count': 1,
                                'hosts': [laborsUnique[idx]['host']['hostname']]
                            }
                        }
                    }

                } else { // for incomplete labors, file by the creating event type
                    if (laborsUnique[idx]['startingLaborId']) {
                        vm.selectedQuestInProgLabors++;
                    } else {
                        vm.selectedQuestStartingLabors++;
                    }

                    var creationEventType = laborsUnique[idx]['creationEvent']['eventType'];
                    var key = creationEventType['category'] + " " + creationEventType['state'];

                    // update the count of labors by type
                    vm.types[key] ? vm.types[key]++ : vm.types[key] = 1;

                    // sort into the bucket for the server owner if the labor is for the owner
                    if (forOwner) {
                        if (sortedLabors[owner][key]) {
                            sortedLabors[owner][key]['count']++;
                            sortedLabors[owner][key]['hosts'].push(
                                laborsUnique[idx]['host']['hostname']
                            )
                        } else {
                            sortedLabors[owner][key] = {
                                'count': 1,
                                'hosts': [laborsUnique[idx]['host']['hostname']]
                            }
                        }
                    }

                    // sort into the bucket for the quest creator if the labor is designate for them
                    if (forCreator) {
                        if (sortedLabors[creator][key]) {
                            sortedLabors[creator][key]['count']++;
                            sortedLabors[creator][key]['hosts'].push(
                                laborsUnique[idx]['host']['hostname']
                            )
                        } else {
                            sortedLabors[creator][key] = {
                                'count': 1,
                                'hosts': [laborsUnique[idx]['host']['hostname']]
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
                        if (vm.selectedLabors.indexOf(vm.labors[idx][idy]["hosts"][idz]) == -1) {
                            vm.selectedLabors.push(vm.labors[idx][idy]["hosts"][idz]);
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
        function throwableEventTypesSelection(selection) {
            if (angular.isDefined(selection)) {
                vm.selectedEventType = selection;
            } else {
                return vm.selectedEventType;
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
                vm.user, vm.selectedLabors, vm.selectedEventType,
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
    QuestStatusCtrl.$inject = ['HermesService', '$q', '$routeParams', '$location', 'smoothScroll'];
})();
