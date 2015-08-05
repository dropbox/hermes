"""
Module for declaring plugin base classes and helpers.
"""

import annex
import os
import logging

BUILTIN_PLUGIN_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "plugins")

log = logging.getLogger(__name__)

class BaseHermesHook(object):
    """ Base class for adding hooks into Hermes.

        This class must be overridden to add actions to perform before and
        after particular state transitions in Hermes.
    """

    def on_event(self, event):
        """Called when an event is created.

        Args:
            event: the event that was created
        """


def get_hooks(additional_dirs=None):
    """ Helper function to find and load all hooks. """
    log.debug("get_hooks()")
    if additional_dirs is None:
        additional_dirs = []
    hooks = annex.Annex(BaseHermesHook, [
        os.path.join(BUILTIN_PLUGIN_DIR, "hooks"),
        "/etc/hermes/plugins/hooks",
        [os.path.expanduser(os.path.join(plugin_dir, "hooks"))
         for plugin_dir in additional_dirs]
        ], instantiate=True)

    return hooks
