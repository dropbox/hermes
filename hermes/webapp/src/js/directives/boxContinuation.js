/**
 * Directive for watching a div and adding a "box-continuation" class when a
 * particular height is reached.  This is used when we have a max-height for a div
 * with a scroll and want to clue the user in to the fact that the box has additional
 * items in it.
 *
 * A "watch" attribute must be specified that let's us know what data
 * modifies the contents of the div (and therefore might alter the height).
 */
(function() {
    function boxContinuation () {
        return {
            restrict: 'A',
            scope: {
                'watch': '='
            },
            link: function ($scope, $ele, $attrs) {
                var triggerHeight = $attrs.triggerHeight || 200;

                $scope.$watch('watch',
                    classAlteration, true);

                function classAlteration() {
                    setTimeout(function() {
                        if ($ele[0].clientHeight >= triggerHeight) {
                            $ele[0].classList.add('box-continuation');
                        } else {
                            $ele[0].classList.remove('box-continuation');
                        }
                    }, 1);
                }
            }
        }
    }

    angular.module('hermesApp').directive('boxContinuation', boxContinuation);
})();