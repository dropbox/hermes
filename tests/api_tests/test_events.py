import json
import pytest
import requests

from .fixtures import tornado_server, tornado_app, sample_data1_server, sample_data2_server
from .util import (
    assert_error, assert_success, assert_created, assert_deleted, Client
)


def test_malformed(sample_data1_server):
    client = sample_data1_server
    assert_error(client.post("/events", data="Non-JSON"), 400)

    assert_error(
        client.create(
            "/events",
            hostname="example",
            user="testman@example.com",
            note="This is a test event"
        ),
        400
    )

    assert_error(
        client.create(
            "/events",
            hostname="example",
            category="blah",
            user="testman@example.com",
            note="This is a test event"
        ),
        500
    )

    assert_error(
        client.create(
            "/events",
            hostname="example",
            state="blah",
            user="testman@example.com",
            note="This is a test event"
        ),
        500
    )


def test_creation(sample_data1_server):
    client = sample_data1_server
    assert_success(
        client.get("/eventtypes"),
        {
            "eventTypes": [{"category": "system-reboot",
                            "description": "This system requires a reboot.",
                            "restricted": False,
                            "id": 1,
                            "state": "required"},
                           {"category": "system-reboot",
                            "description": "This system rebooted.",
                            "restricted": False,
                            "id": 2,
                            "state": "completed"},
                           {"category": "system-maintenance",
                            "description": "This system requires maintenance.",
                            "restricted": False,
                            "id": 3,
                            "state": "required"},
                           {"category": "system-maintenance",
                            "description": "This system is ready for maintenance.",
                            "restricted": False,
                            "id": 4,
                            "state": "ready"},
                           {"category": "system-maintenance",
                            "description": "System maintenance completed.",
                            "restricted": False,
                            "id": 5,
                            "state": "completed"},
                           {"category": "system-shutdown",
                            "description": "System shutdown required.",
                            "restricted": False,
                            "id": 6,
                            "state": "required"},
                           {"category": "system-shutdown",
                            "description": "System shutdown completed.",
                            "restricted": False,
                            "id": 7,
                            "state": "completed"}],
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
                        "id": 1,
                        "note": "example needs a reboot",
                        "user": "system@example.com"},
                       {"eventTypeId": 2,
                        "hostId": 1,
                        "id": 2,
                        "note": "example needs a rebooted",
                        "user": "system@example.com"}],
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
            user="testman@example.com",
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
            "note": "This is a test event",
            "eventTypeId": 1,
            "user": "testman@example.com"
        },
        strip=["timestamp"]
    )

    assert_created(
        client.create(
            "/events",
            hostname="example",
            user="testman@example.com",
            category="system-reboot",
            state="completed",
            note="This is another test event"
        ),
        "/api/v1/events/4"
    )

    assert_success(
        client.get("/events/4"),
        {
            "id": 4,
            "hostId": 1,
            "note": "This is another test event",
            "eventTypeId": 2,
            "user": "testman@example.com"
        },
        strip=["timestamp"]
    )


def test_update(sample_data1_server):
    client = sample_data1_server
    assert_created(
        client.create(
            "/events",
            hostname="example",
            user="testman@example.com",
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
            "note": "This is a test event",
            "eventTypeId": 1,
            "user": "testman@example.com"
        },
        strip=["timestamp"]
    )

    assert_error(client.put("/events/3", json={"note": "New note"}), 405)


def test_multi_host_events(sample_data1_server):
    client = sample_data1_server
    result = client.create(
            "/events",
            hostnames=["example","sample","test"],
            user="testman@example.com",
            eventTypeId=1,
            note="This is a test event"
        )

    result_json = result.json()

    assert result_json['totalEvents'] == 3


def test__before_after_query(sample_data1_server):
    client = sample_data1_server
    event2 = client.get("/events/2").json()

    assert event2['timestamp'] is not None

    assert_created(
        client.create(
            "/events",
            hostname="example",
            user="testman@example.com",
            eventTypeId=1,
            note="This is a test event"
        ),
        "/api/v1/events/3"
    )

    new_event = client.get("/events/3").json()
    new_timestamp = new_event['timestamp']

    result = client.get("/events/?after={}".format(new_timestamp)).json()
    assert result['totalEvents'] == 1

    result = client.get("/events/?before={}".format(new_timestamp)).json()
    assert result['totalEvents'] == 2


def test_after_event_type_query(sample_data2_server):
    client = sample_data2_server
    assert_success(
        client.get("/events"),
        {
            "limit": 10,
            "offset": 0,
            "totalEvents": 15
        },
        strip=["timestamp", "events"]
    )
    assert_success(
        client.get("/events?hostname=example&afterEventType=3"),
        {
            "limit": 10,
            "offset": 0,
            "totalEvents": 3
        },
        strip=["timestamp", "events"]
    )


def test_after_event_id_query(sample_data2_server):
    """
    Test the afterEventId param to the events endpoint.
    """
    client = sample_data2_server
    assert_success(
        client.get("/events"),
        {
            "limit": 10,
            "offset": 0,
            "totalEvents": 15
        },
        strip=["timestamp", "events"]
    )
    # There are 8 events with hostname=example in the data set,
    # with ID values 1-8.  After event Id 2, there should be 7 total events.
    assert_success(
        client.get("/events?hostname=example&afterEventId=2"),
        {
            "limit": 10,
            "offset": 0,
            "totalEvents": 7
        },
        strip=["timestamp", "events"]
    )
    # After event Id 3 there should be 6 total events.
    assert_success(
        client.get("/events?hostname=example&afterEventId=3"),
        {
            "limit": 10,
            "offset": 0,
            "totalEvents": 6
        },
        strip=["timestamp", "events"]
    )