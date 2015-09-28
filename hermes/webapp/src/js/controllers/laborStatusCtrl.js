(function() {
    'use strict';

    function LaborStatusCtrl(hermesService, $q, $routeParams, $location) {
        var vm = this;

        vm.errorMessage = null;
        vm.hostOwnerInput = null;
        vm.queryInput = null;
        vm.filterEventType = null;
        vm.selectedEventType = null;

        vm.laborData = null;
        vm.selected = [];
        vm.hostTags = null;
        vm.hostOwners = null;
        vm.throwableTypes = null;
        vm.allTypes = null;
        vm.createInProgress = false;
        vm.limit = 10;
        vm.offset = 0;
        vm.totalQuests = 10;
        vm.createErrorMessage = null;
        vm.createSuccessMessage = null;
        vm.createEventsModal = false;

        vm.colors = ['#0071ce', '#72b6ec', '#cce6fa', '#f4faff'];

        vm.runFilter = runFilter;
        vm.getOpenLabors = getOpenLabors;
        vm.toggleSelect = toggleSelect;
        vm.selectAll = selectAll;
        vm.deselectAll = deselectAll;
        vm.throwableEventTypesSelection = throwableEventTypesSelection;
        vm.filterEventTypesSelection = filterEventTypesSelection;
        vm.createEvents = createEvents;


        vm.selectOptions = {
            updateOn: 'default change blur',
            getterSetter: true,
            allowInvalid: true
        };


        if ($routeParams.byQuery) {
            vm.queryInput = $routeParams.byQuery;
        }

        // if user passed a filter-by-owner query param, that takes precedence.
        // otherwise, the default is to use the authenticate user
        if ($routeParams.byOwner) {
            vm.hostOwnerInput = $routeParams.byOwner;
            getOpenLabors("owner");
        } else {
            hermesService.getCurrentUser().then(function(user){
                if (user) {
                    vm.hostOwnerInput = user;
                }
                getOpenLabors();
            });
        }

        hermesService.getCurrentUser().then(function(user){
            if (user) {
                vm.user = user;
            } else {
                vm.errorMessage = "Cannot create a new quest if not authenticated.";
            }
        });

        hermesService.getAllEventTypes().then(function(types) {
            var allTypes = [null];
            vm.allTypes = allTypes.concat(types);
            vm.filterEventType = vm.allTypes[0];
        });

        hermesService.getUserThrowableEventTypes().then(function(types) {
            vm.throwableTypes = types;
            vm.selectedEventType = vm.throwableTypes[0];
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
            var maxPage = Math.floor((vm.totalLabors - 1) / vm.limit);
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

        function filterEventTypesSelection(selection) {
            if (angular.isDefined(selection)) {
                vm.filterEventType = selection;
            } else {
                return vm.filterEventType;
            }
        }

        function runFilter() {
            $routeParams.laborId = null;
            vm.offset = 0;
            getOpenLabors();
        }

        function getOpenLabors() {
            vm.errorMessage = null;
            vm.selected = [];
            vm.laborData = null;

            var options = {};

            if (vm.hostOwnerInput) {
                options['filterByOwner'] = vm.hostOwnerInput;
                $location.search('byOwner', vm.hostOwnerInput, false);
            }

            if (vm.queryInput) {
                options['filterByQuery'] = vm.queryInput;
                $location.search('byQuery', vm.queryInput, false);
            }

            if (vm.filterEventType) {
                options['filterByCategory'] = vm.filterEventType.category;
                options['filterByState'] = vm.filterEventType.state;
            }

            hermesService.getOpenLabors(options).then(function (data) {
                if (!data
                    || !data['labors']
                    || data['labors'].length == 0) {
                    vm.errorMessage = "No labors found matching criteria.  Please refine.";
                    return;
                }

                vm.laborData = data['labors'];
                vm.limit = data['limit'] || vm.limit;
                vm.offset = data['offset'] || vm.offset;
                vm.totalLabors = data['totalLabors'] || vm.totalLabors;

                // find the quest requested and make that the selection
                var index = 0;
                for (var idx in vm.laborData) {
                    if (vm.laborData[idx]['id'] == $routeParams.laborId) {
                        index = idx;
                    }
                }

                vm.offset = index - (index % vm.limit);

                getHostTags();
            }).catch(function(error) {
                vm.errorMessage = "Could not load open labors!  Please try again later.";
            });
        }

        /**
         * Get tags associated with the hosts of the machines in vm.laborData
         */
        function getHostTags() {
            var hostnames = []
            for (var idx in vm.laborData) {
                var labor = vm.laborData[idx];
                hostnames.push(labor['host']['hostname'])
            }

            hermesService.getHostTags(hostnames).then(function(data) {
                vm.hostTags = data;
            }).catch(function(error){
                vm.errorMessage = "Could not load host tags: " + error.statusText;
            });

            hermesService.getOwnerInformation(hostnames).then(function(data) {
                vm.hostOwners = data;
            }).catch(function(error) {
                vm.errorMessage = "Could not load host owners: " + error.statusText;
            })

        }

        /**
         * Toggle a labor selection
         * @param id id of the labor to select
         */
        function toggleSelect(id) {
            var idx = vm.selected.indexOf(id);
            if (idx != -1) {
                vm.selected.splice(idx, 1)
            } else {
                vm.selected.push(id);
            }
        }

        /**
         * Select all the labors on this screen and add them to the list
         * of selected labors
         */
        function selectAll() {
            for (var idx = parseInt(vm.offset);
                 idx < (parseInt(vm.offset) + parseInt(vm.limit));
                 idx++) {

                if (idx >= vm.laborData.length) {
                    break;
                }

                if (vm.selected.indexOf(vm.laborData[idx].id) == -1) {
                    vm.selected.push(vm.laborData[idx].id);
                }
            }
        }

         /**
         * Deselect all the labors on this screen and remove them to the list
         * of selected labors
         */
        function deselectAll() {
            for (var idx = parseInt(vm.offset);
                 idx < (parseInt(vm.offset) +  parseInt(vm.limit)); idx++) {

                if (idx >= vm.laborData.length) {
                    break;
                }

                var idy = vm.selected.indexOf(vm.laborData[idx].id);
                if (idy != -1) {
                    vm.selected.splice(idy, 1);
                }
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

            var hostnames = [];
            for (var idx in vm.laborData) {
                var labor_id = vm.laborData[idx].id;

                if (vm.selected.indexOf(labor_id) != -1) {
                    hostnames.push(vm.laborData[idx].host.hostname);
                }
            }

            vm.result = hermesService.createEvents(vm.user, hostnames, vm.selectedEventType, "Created via Web UI.")
                .then(function(response) {
                    vm.createInProgress = false;
                    vm.selected = [];
                    vm.createSuccessMessage = "Successfully created events.";
                    getOpenLabors();
                })
                .catch(function(error) {
                    vm.createInProgress = false;
                    vm.createErrorMessage ="Event creation failed!  " + error.statusText;
                });

        }
    }

    angular.module('hermesApp').controller('LaborStatusCtrl', LaborStatusCtrl);
    LaborStatusCtrl.$inject = ['HermesService', '$q', '$routeParams', '$location'];
})();
