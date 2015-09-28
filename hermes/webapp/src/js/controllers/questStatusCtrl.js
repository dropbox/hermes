(function() {
    'use strict';

    function QuestStatusCtrl(hermesService, $q, $routeParams, $location) {
        var vm = this;

        vm.errorMessage = null;
        vm.filterByCreator = null;
        vm.queryInput = null;

        vm.questData = null;
        vm.selectedQuest = null;
        vm.selectedQuestDetails = null;
        vm.labors = null;
        vm.types = null;
        vm.limit = 10;
        vm.offset = 0;
        vm.totalQuests = 10;

        vm.colors = ['#0071ce', '#72b6ec', '#cce6fa', '#f4faff'];

        vm.runNewFilter = runNewFilter;
        vm.getOpenQuests = getOpenQuests;
        vm.newQuestSelection = newQuestSelection;
        vm.goToCreatePage = goToCreatePage;

        if ($routeParams.byQuery) {
            vm.queryInput = $routeParams.byQuery;
        }

        // if user passed a filter-by-creator query param, that takes precedence.
        // otherwise, the default is to use the authenticate user
        if ($routeParams.byCreator) {
            vm.filterByCreator = $routeParams.byCreator;
            getOpenQuests();
        } else {
            hermesService.getCurrentUser().then(function(user){
                if (user) {
                    vm.filterByCreator = user;
                }
                getOpenQuests();
            });
        }


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
            return ['10', '20', '50', '100'];
        }

        function pageSetting(page) {
            if (angular.isDefined(page)) {
                vm.offset = (page - 1) * vm.limit;
            } else {
                return "" + (vm.offset / vm.limit + 1);
            }
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
        vm.pageValues = pageValues;

        ////////////////////////////////

        function goToCreatePage() {
            $location.url("/v1/quest/new");
        }

        function runNewFilter() {
            $routeParams.questId = null;
            vm.offset = 0;
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

                // find the quest requested and make that the selection
                var index = 0;
                for (var idx in vm.questData) {
                    if (vm.questData[idx]['id'] == $routeParams.questId) {
                        index = idx;
                    }
                }

                vm.offset = index - (index % vm.limit);
                newQuestSelection(vm.questData[index]);
            });
        }

        function newQuestSelection(quest) {
            vm.selectedQuest = quest;
            vm.selectedQuestDetails = null;
            vm.hostOwners = null;
            vm.labors = null;
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
                $location.update_path('/v1/quests/' + quest.id, true);
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

            var sortedLabors = {};
            vm.types = {};
            for (var idx in laborsUnique) {
                var hostname = laborsUnique[idx]['host']['hostname'];
                var owner = ownerData[hostname];

                if (!sortedLabors[owner]) {
                    sortedLabors[owner] = {}
                }
                var ownerLabors = sortedLabors[owner];
                if (laborsUnique[idx]['completionEvent']) {
                    var completionEventType = laborsUnique[idx]['completionEvent']['eventType'];
                    var key = completionEventType['category'] + " " + completionEventType['state'];
                    vm.types[key] ? vm.types[key]++ : vm.types[key] = 1;
                    if (ownerLabors[key]) {
                        ownerLabors[key]['count']++;
                        ownerLabors[key]['hosts'].push(
                            laborsUnique[idx]['host']['hostname']
                        )
                    } else {
                        ownerLabors[key] = {
                            'count': 1,
                            'hosts': [laborsUnique[idx]['host']['hostname']]
                        }
                    }
                } else {
                    var creationEventType = laborsUnique[idx]['creationEvent']['eventType'];
                    var key = creationEventType['category'] + " " + creationEventType['state']
                    vm.types[key] ? vm.types[key]++ : vm.types[key] = 1;
                    if (ownerLabors[key]) {
                        ownerLabors[key]['count']++;
                        ownerLabors[key]['hosts'].push(
                            laborsUnique[idx]['host']['hostname']
                        )
                    } else {
                        ownerLabors[key] = {
                            'count': 1,
                            'hosts': [laborsUnique[idx]['host']['hostname']]
                        }
                    }
                }
            }

            vm.labors = sortedLabors;
        }
    }

    angular.module('hermesApp').controller('QuestStatusCtrl', QuestStatusCtrl);
    QuestStatusCtrl.$inject = ['HermesService', '$q', '$routeParams', '$location'];
})();
