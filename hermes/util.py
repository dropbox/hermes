"""
Project-wide utilities.
"""

import logging
import requests
import smtplib

from email.mime.text import MIMEText

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
        log.debug("{} {}".format(settings.slack_webhook, json))
        response = requests.post(
            settings.slack_webhook, json=json, proxies=proxies
        )
    except Exception as exc:
        log.warn("Error writing to Slack: {}".format(exc.message))


def email_message(recipients, subject, message):
    """Email a message to a user.

    Args:
        subject: the subject of the email we wish to send
        message: the content of the email we wish to send
        recipients: the email address to whom we wish to send the email
    """
    if not settings.email_notifications:
        return

    if isinstance(recipients, basestring):
        recipients = recipients.split(",")
    if isinstance(settings.email_always_copy, basestring):
        extra_recipients = settings.email_always_copy.split(",")
    else:
        extra_recipients = [settings.email_always_copy]

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = settings.email_sender_address
    msg["To"] = ", ".join(recipients)
    if extra_recipients:
        msg["Cc"] = ", ".join(extra_recipients)

    try:
        smtp = smtplib.SMTP("localhost")
        smtp.sendmail(
            settings.email_sender_address,
            recipients + extra_recipients,
            msg.as_string()
        )
        smtp.quit()
    except Exception as exc:
        log.warn("Error sending email: {}".format(exc.message))
