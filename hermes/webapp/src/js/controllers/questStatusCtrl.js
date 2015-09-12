(function() {
    'use strict';

    function QuestStatusCtrl(hermesService) {
        var vm = this;

        vm.questData = null;
        vm.selectedQuest = null;

        vm.getOpenQuests = getOpenQuests;
        vm.newQuestSelection = newQuestSelection;

        getOpenQuests();

        ////////////////////////////////

        function getOpenQuests() {
            hermesService.getOpenQuests().then(function (questData) {
                vm.questData = questData;
                vm.selectedQuest = questData[0];
            });
        }

        function newQuestSelection(quest) {
            console.log(quest);
            vm.selectedQuest = quest;
        }
    }

    angular.module('hermesApp').controller('QuestStatusCtrl', QuestStatusCtrl);
    QuestStatusCtrl.$inject = ['HermesService'];
})();
