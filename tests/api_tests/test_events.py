import json
import pytest
import requests

from .fixtures import tornado_server, tornado_app, sample_data1_server
from .util import (
    assert_error, assert_success, assert_created, assert_deleted, Client
)


def test_malformed(sample_data1_server):
    client = sample_data1_server
    assert_error(client.post("/events", data="Non-JSON"), 400)


def test_creation(sample_data1_server):
    client = sample_data1_server
    assert_success(
        client.get("/eventtypes"),
        {
            "eventTypes": [{"category": "system-reboot",
                            "description": "This system requires a reboot.",
                            "href": "/api/v1/eventtypes/1",
                            "id": 1,
                            "state": "required"},
                           {"category": "system-reboot",
                            "description": "This system rebooted.",
                            "href": "/api/v1/eventtypes/2",
                            "id": 2,
                            "state": "completed"},
                           {"category": "system-maintenance",
                            "description": "This system requires maintenance.",
                            "href": "/api/v1/eventtypes/3",
                            "id": 3,
                            "state": "required"},
                           {"category": "system-maintenance",
                            "description": "This system is ready for maintenance.",
                            "href": "/api/v1/eventtypes/4",
                            "id": 4,
                            "state": "ready"},
                           {"category": "system-maintenance",
                            "description": "System maintenance completed.",
                            "href": "/api/v1/eventtypes/5",
                            "id": 5,
                            "state": "completed"},
                           {"category": "system-shutdown",
                            "description": "System shutdown required.",
                            "href": "/api/v1/eventtypes/6",
                            "id": 6,
                            "state": "required"},
                           {"category": "system-shutdown",
                            "description": "System shutdown completed.",
                            "href": "/api/v1/eventtypes/7",
                            "id": 7,
                            "state": "completed"}],
            "href": "/api/v1/eventtypes",
            "limit": 10,
            "offset": 0,
            "totalEventTypes": 7,
        }
    )

    assert_success(
        client.get("/events"),
        {
            "events": [{"eventTypeId": 1,
                        "hostId": 1,
                        "href": "/api/v1/events/1",
                        "id": 1,
                        "note": "example needs a reboot",
                        "user": "system"},
                       {"eventTypeId": 2,
                        "hostId": 1,
                        "href": "/api/v1/events/2",
                        "id": 2,
                        "note": "example needs a rebooted",
                        "user": "system"}],
            "href": "/api/v1/events",
            "limit": 10,
            "offset": 0,
            "totalEvents": 2
        },
        strip=["timestamp"]
    )

    assert_created(
        client.create(
            "/events",
            hostname="example",
            user="testman",
            eventTypeId=1,
            note="This is a test event"
        ),
        "/api/v1/events/3"
    )

    assert_success(
        client.get("/events/3"),
        {
            "id": 3,
            "hostId": 1,
            "href": "/api/v1/events/3",
            "note": "This is a test event",
            "eventTypeId": 1,
            "user": "testman"
        },
        strip=["timestamp"]
    )


def test_update(sample_data1_server):
    client = sample_data1_server
    assert_created(
        client.create(
            "/events",
            hostname="example",
            user="testman",
            eventTypeId=1,
            note="This is a test event"
        ),
        "/api/v1/events/3"
    )

    assert_success(
        client.get("/events/3"),
        {
            "id": 3,
            "hostId": 1,
            "href": "/api/v1/events/3",
            "note": "This is a test event",
            "eventTypeId": 1,
            "user": "testman"
        },
        strip=["timestamp"]
    )

    assert_error(client.put("/events/3", json={"note": "New note"}), 405)