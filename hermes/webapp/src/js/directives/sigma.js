(function() {
    'use strict';
    angular.module('hermesApp')
        .directive('sigmajs', function() {
        //over-engineered random id, so that multiple instances can be put on a single page
        var divId = 'sigmjs-dir-container-'+Math.floor(Math.random() * 999999999999);
        return {
            restrict: 'E',
            template: '<div id="'+divId+'" style="width: 100%;height: 400px;"></div>',
            scope: {
                //@ reads the attribute value, = provides two-way binding, & works with functions
                graph: '=',
                width: '@',
                height: '@',
                relativeSizeNode: '='
            },
            link: function (scope, element, attrs) {
                // Let's first initialize sigma:
                var s = new sigma({
                    container: "container",
                    renderer: {
                        container: "container",
                        type: "canvas"
                    },
                    settings: {
                        defaultNodeColor: '#ec5148',
                        labelThreshold: 4
                    }
                });


                scope.$watch('graph', function(newVal,oldVal) {
                    s.graph.clear();
                    s.graph.read(scope.graph);
                    s.refresh();
                    if(scope.releativeSizeNode) {
                        //this feature needs the plugin to be added
                        sigma.plugins.relativeSize(s, 2);
                    }
                });

                scope.$watch('width', function(newVal,oldVal) {
                    console.log("graph width: "+scope.width);
                    element.children().css("width",scope.width);
                    s.refresh();
                    window.dispatchEvent(new Event('resize')); //hack so that it will be shown instantly
                });
                scope.$watch('height', function(newVal,oldVal) {
                    console.log("graph height: "+scope.height);
                    element.children().css("height",scope.height);
                    s.refresh();
                    window.dispatchEvent(new Event('resize'));//hack so that it will be shown instantly
                });

                element.on('$destroy', function() {
                    s.graph.clear();
                });
            }
        };
    });
})();