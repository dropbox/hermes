"""
Project-wide utilities.
"""

import logging
import requests

from .settings import settings


log = logging.getLogger(__name__)


def slack_message(message):
    """Post a message to Slack if a webhook as been defined.

    Args:
        message: the content of the Slack post
    """
    if not settings.slack_webhook:
        return

    if settings.slack_proxyhost:
        proxies = {
            "http": "http://{}".format(settings.slack_proxyhost),
            "https": "http://{}".format(settings.slack_proxyhost)
        }
    else:
        proxies = None

    json = {
        "text": message,
        "username": "Hermes Log",
        "icon_emoji": ":hermes:",
    }
    try:
        log.info("{} {}".format(settings.slack_webhook, json))
        response = requests.post(
            settings.slack_webhook, json=json, proxies=proxies
        )
    except Exception as exc:
        log.warn("Error writing to Slack: {}".format(exc.message))