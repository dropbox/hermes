(function() {
    'use strict';

    function QuestStatusCtrl(hermesService) {
        var vm = this;

        vm.questData = null;
        vm.selectedQuest = null;
        vm.selectedQuestDetails = null;
        vm.laborAnalysis = {};

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

            hermesService.getQuestDetails(quest.id).then(function (questData) {
                vm.selectedQuestDetails = questData;
                analyzeLabors(questData);
            })
        }

        function analyzeLabors(quest) {
            vm.laborAnalysis = {};

            var labors = quest['labors'];
            for (var idx in labors) {
                if (labors[idx]['completionEvent']) {
                    var completionEventType = labors[idx]['completionEvent']['eventType'];
                    var key = completionEventType['category'] + " " + completionEventType['state'];
                    if (vm.laborAnalysis[key]) {
                        vm.laborAnalysis[key]['count']++;
                        vm.laborAnalysis[key]['hosts'].push(
                            labors[idx]['host']['hostname']
                        )
                    } else {
                        vm.laborAnalysis[key] = {
                            'count': 1,
                            'hosts': [labors[idx]['host']['hostname']]
                        }
                    }
                } else {
                    var creationEventType = labors[idx]['creationEvent']['eventType'];
                    var key = creationEventType['category'] + " " + creationEventType['state']
                    if (vm.laborAnalysis[key]) {
                        vm.laborAnalysis[key]['count']++;
                        vm.laborAnalysis[key]['hosts'].push(
                            labors[idx]['host']['hostname']
                        )
                    } else {
                        vm.laborAnalysis[key] = {
                            'count': 1,
                            'hosts': [labors[idx]['host']['hostname']]
                        }
                    }
                }
            }
        }
    }

    angular.module('hermesApp').controller('QuestStatusCtrl', QuestStatusCtrl);
    QuestStatusCtrl.$inject = ['HermesService'];
})();
