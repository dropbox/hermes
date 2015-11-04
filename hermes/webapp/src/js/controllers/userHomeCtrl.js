(function() {
    'use strict';

    function UserHomeCtrl(hermesService, $q, $routeParams, $location, smoothScroll) {
        var vm = this;

        vm.errorMessage = null;

        vm.domain = null;
        vm.user = null;
        vm.questData = null;
        vm.totalQuests = null;
        vm.totalUserCreatedQuests = null;
        vm.totalLabors = null;
        vm.totalUserLabors = null;

        vm.questsUrl = null;
        vm.laborsUrl = null;

        vm.goToQuestsPage = goToQuestsPage;
        vm.goToLaborsPage = goToLaborsPage;

        hermesService.getCurrentUser().then(function (user) {
            if (user) {
                vm.user = user;
            }

            // find labors and quests for this user
            getOpenQuests();
            getOpenLabors();
        });

        hermesService.getServerConfig().then(function(config) {
           vm.domain = config['domain'];
        });

        function goToCreatePage() {
            $location.url("/v1/quest/new");
        }

        function goToQuestsPage() {
            $location.url(vm.questsUrl);
        }

        function goToLaborsPage() {
            $location.url(vm.laborsUrl);
        }

        /**
         * Get open quest information, but we only want basic overview information.
         */
        function getOpenQuests() {
            vm.errorMessage = null;

            var options = {};
            options['overviewOnly'] = true;

            hermesService.getOpenQuests(options).then(function (questData) {
                vm.questData = questData['quests'];
                vm.totalQuests = questData['totalQuests'];

                // see which quests are overdue and which are owned by this user
                vm.totalUserCreatedQuests = 0;
                for (var idx in vm.questData) {
                    evalDueDate(vm.questData[idx]);
                    if (vm.questData[idx]['creator'] == vm.user) {
                        vm.totalUserCreatedQuests++;
                    }
                }

                if (vm.totalUserCreatedQuests == 0) {
                    vm.questsUrl = "/v1/quests/?byCreator=";
                } else {
                    vm.questsUrl = "/v1/quests?byCreator=" + vm.user;
                }
            });
        }

        /**
         * Get labor information (overview only) for all open labors and labors
         * that apply to this user.
         */
        function getOpenLabors() {
            var options = {};
            options['overviewOnly'] = true;

            hermesService.getOpenLabors(options).then(function (laborData){
                vm.totalLabors = laborData['totalLabors'];
            });

            options['filterByOwner'] = vm.user;

            hermesService.getOpenLabors(options).then(function (laborData) {
                vm.totalUserLabors = laborData['totalLabors'];
                vm.laborsUrl = "/v1/labors?byOwner=" + vm.user;
            }).catch(function(error) {
                vm.totalUserLabors = 0;
                vm.laborsUrl = "/v1/labors?byOwner=";
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
    }

    angular.module('hermesApp').controller('UserHomeCtrl', UserHomeCtrl);
    UserHomeCtrl.$inject = ['HermesService', '$q', '$routeParams', '$location', 'smoothScroll'];
})();
