(function() {
    'use strict';

    function QuestEditCtrl(hermesService, $q, $routeParams, $location) {
        var vm = this;

        vm.user = null;         // holds the current user; we should only let current owners update quests
        vm.today = new Date();  // used to restrict how far back the due date can be set
        vm.quest = null;        // holds the retrieve quest details

        // new values that the user can edit
        vm.newCreator = null;
        vm.description = null;
        vm.targetDate = null;

        vm.editingCreator = false;  // controls if we show the creator editing field
        vm.editingDate = false;     // controls if we show the date picker
        vm.editingDesc = false;     // controls if we show the desc edit field

        // various messaging fields
        vm.successMessage = null;
        vm.errorMessage = null;

        hermesService.getCurrentUser().then(function(user){
            if (user) {
                vm.user = user;
            } else {
                vm.errorMessages.push("Cannot create a new quest if not authenticated.");
            }
        });

        refreshQuestInfo();

        vm.calDateClasser = calDateClasser;
        vm.focus = focus;
        vm.saveCreator = saveCreator;
        vm.saveTargetTime = saveTargetTime;
        vm.saveDescription = saveDescription;
        vm.refreshQuestInfo = refreshQuestInfo;

        ////////////////////////////////

        function refreshQuestInfo() {
            hermesService.getQuestDetails($routeParams.questId).then(function(quest) {
                vm.quest = quest;
                vm.description = quest.description;
                vm.targetDate = new Date();
                //vm.targetDate.setDate(new Date(targetDate).getDate());
                vm.targetDate.setTime(Math.round(vm.targetDate.getTime() / 900000) * 900000);
            });
        }

        /**
         * Adds our classes to the date picker
         * @param date the date in question
         * @param mode the mode
         */
        function calDateClasser(date, mode) {
            return "date-picker";
        }

        /**
         * Helper to set focus and select the text
         * @param id  the item that gets focus
         */
        function focus(id) {
            setTimeout(function() {
                document.getElementById(id).focus();
                document.getElementById(id).select();
            }, 10);
        }

        /**
         * Change the creator for a quest
         */
        function saveCreator() {
            hermesService.updateQuest(vm.quest.id, {"creator": vm.newCreator})
                .then(function(response) {
                    vm.successMessage = "Updated creator to " + vm.newCreator;
                    vm.newCreator = null;
                    vm.editingCreator = false;
                    vm.refreshQuestInfo();
                })
                .catch(function(error) {
                    vm.errorMessage = "Error updating creator: " + error.statusText;
                })
        }

        /**
         * Change the target time for a quest
         */
        function saveTargetTime() {
            hermesService.updateQuest(vm.quest.id, {"targetTime": vm.targetDate})
                .then(function(response) {
                    vm.successMessage = "Updated target time to " + vm.targetDate;
                    vm.editingDate = false;
                    vm.refreshQuestInfo();
                })
                .catch(function(error) {
                    vm.errorMessage = "Error updating target time: " + error.statusText;
                })
        }

        /**
         * Change the description for a quest
         */
        function saveDescription() {
            hermesService.updateQuest(vm.quest.id, {"description": vm.description})
                .then(function(response) {
                    vm.successMessage = "Updated description!";
                    vm.editingDesc = false;
                    vm.refreshQuestInfo();
                })
                .catch(function(error) {
                    vm.errorMessage = "Error updating description: " + error.statusText;
                })
        }

    }

    angular.module('hermesApp').controller('QuestEditCtrl', QuestEditCtrl);
    QuestEditCtrl.$inject = ['HermesService', '$q', '$routeParams', '$location'];
})();
