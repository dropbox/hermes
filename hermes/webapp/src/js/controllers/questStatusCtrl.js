(function() {
    'use strict';

    function QuestStatusCtrl(hermesService, $q) {
        var vm = this;

        vm.questData = null;
        vm.selectedQuest = null;
        vm.selectedQuestDetails = null;
        vm.labors = null;

        vm.getOpenQuests = getOpenQuests;
        vm.newQuestSelection = newQuestSelection;

        getOpenQuests();

        ////////////////////////////////

        function getOpenQuests() {
            hermesService.getOpenQuests().then(function (questData) {
                vm.questData = questData;
                newQuestSelection(questData[0]);
            });
        }

        function newQuestSelection(quest) {
            vm.selectedQuest = quest;
            vm.selectedQuestDetails = null;
            vm.hostOwners = null;
            vm.labors = null;

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
                analyzeLabors(data[0], data[1]);
            });
        }

        /**
         * Build the breakdown of the open labors, grouping by owner and then state
         * @param quest
         */
        function analyzeLabors(ownerData, questData) {
            var sortedLabors = {};
            var labors = questData['labors'];
            for (var idx in labors) {
                var hostname = labors[idx]['host']['hostname'];
                var owner = ownerData[hostname];

                if (!sortedLabors[owner]) {
                    sortedLabors[owner] = {}
                }
                var ownerLabors = sortedLabors[owner];
                if (labors[idx]['completionEvent']) {
                    var completionEventType = labors[idx]['completionEvent']['eventType'];
                    var key = completionEventType['category'] + " " + completionEventType['state'];
                    if (ownerLabors[key]) {
                        ownerLabors[key]['count']++;
                        ownerLabors[key]['hosts'].push(
                            labors[idx]['host']['hostname']
                        )
                    } else {
                        ownerLabors[key] = {
                            'count': 1,
                            'hosts': [labors[idx]['host']['hostname']]
                        }
                    }
                } else {
                    var creationEventType = labors[idx]['creationEvent']['eventType'];
                    var key = creationEventType['category'] + " " + creationEventType['state']
                    if (ownerLabors[key]) {
                        ownerLabors[key]['count']++;
                        ownerLabors[key]['hosts'].push(
                            labors[idx]['host']['hostname']
                        )
                    } else {
                        ownerLabors[key] = {
                            'count': 1,
                            'hosts': [labors[idx]['host']['hostname']]
                        }
                    }
                }
            }

            vm.labors = sortedLabors;
        }
    }

    angular.module('hermesApp').controller('QuestStatusCtrl', QuestStatusCtrl);
    QuestStatusCtrl.$inject = ['HermesService', '$q'];
})();
