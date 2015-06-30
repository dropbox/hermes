import json
import pytest
import requests

from .fixtures import tornado_server, tornado_app, sample_data1_server

from datetime import datetime, timedelta

from .util import (
    assert_error, assert_success, assert_created, assert_deleted, Client
)


def test_malformed(sample_data1_server):
    client = sample_data1_server
    assert_error(client.post("/quests", data="Non-JSON"), 400)


def test_creation(sample_data1_server):
    client = sample_data1_server
    assert_success(
        client.get("/events"),
        {
            "events": [{"eventTypeId": 1,
                        "hostId": 1,
                        "href": "/api/v1/events/1",
                        "id": 1,
                        "note": "example needs a reboot",
                        "user": "system@example.com"},
                       {"eventTypeId": 2,
                        "hostId": 1,
                        "href": "/api/v1/events/2",
                        "id": 2,
                        "note": "example needs a rebooted",
                        "user": "system@example.com"}],
            "href": "/api/v1/events",
            "limit": 10,
            "offset": 0,
            "totalEvents": 2
        },
        strip=["timestamp"]
    )

    assert_success(
        client.get("/quests"),
        {
            "href": "/api/v1/quests",
            "limit": 10,
            "offset": 0,
            "totalQuests": 0,
            "quests": []
        }
    )

    target_time = datetime.utcnow() + timedelta(days=7)

    assert_created(
        client.create(
            "/quests",
            creator="johnny@example.com",
            eventTypeId=1,
            targetTime=str(target_time),
            description="This is a quest almighty",
            hostnames=["example", "sample", "test"]
        ),
        "/api/v1/quests/1"
    )

    assert_success(
        client.get("/quests"),
        {
            "href": "/api/v1/quests",
            "limit": 10,
            "offset": 0,
            "totalQuests": 1
        },
        strip=["quests"]
    )

    assert_success(
        client.get("/quests/1"),
        {
            "href": "/api/v1/quests/1",
            "id": 1,
            "creator": "johnny@example.com",
            "targetTime": str(target_time),
            "description": "This is a quest almighty",
            "completionTime": None
        },
        strip=["embarkTime", "labors"]
    )

    assert_success(
        client.get("/events"),
        {
            "href": "/api/v1/events",
            "limit": 10,
            "offset": 0,
            "totalEvents": 5
        },
        strip=["events"]
    )

    # see if we can create events based on quest id
    client.create(
        "/events",
        questId=1,
        user="testman@example.com",
        eventTypeId=2,
        note="These are test events for the quest"
    )

    assert_success(
        client.get("/events"),
        {
            "href": "/api/v1/events",
            "limit": 10,
            "offset": 0,
            "totalEvents": 8
        },
        strip=["events"]
    )

def test_update(sample_data1_server):
    client = sample_data1_server

    target_time = datetime.utcnow() + timedelta(days=7)

    assert_created(
        client.create(
            "/quests",
            creator="johnny@example.com",
            eventTypeId=1,
            targetTime=str(target_time),
            description="This is a quest almighty",
            hostnames=["example", "sample", "test"]
        ),
        "/api/v1/quests/1"
    )

    assert_success(
        client.update(
            "/quests/1",
            creator="betsy@example.com"
        ),
        {
            "href": "/api/v1/quests/1",
            "id": 1,
            "creator": "betsy@example.com",
            "targetTime": str(target_time),
            "description": "This is a quest almighty",
            "completionTime": None
        },
        strip=["embarkTime", "labors"]
    )

    assert_success(
        client.get("/quests/1"),
        {
            "href": "/api/v1/quests/1",
            "id": 1,
            "creator": "betsy@example.com",
            "targetTime": str(target_time),
            "description": "This is a quest almighty",
            "completionTime": None
        },
        strip=["embarkTime", "labors"]
    )

    assert_success(
        client.update(
            "/quests/1",
            description="New desc"
        ),
        {
            "href": "/api/v1/quests/1",
            "id": 1,
            "creator": "betsy@example.com",
            "targetTime": str(target_time),
            "description": "New desc",
            "completionTime": None
        },
        strip=["embarkTime", "labors"]
    )

    assert_success(
        client.get("/quests/1"),
        {
            "href": "/api/v1/quests/1",
            "id": 1,
            "creator": "betsy@example.com",
            "targetTime": str(target_time),
            "description": "New desc",
            "completionTime": None
        },
        strip=["embarkTime", "labors"]
    )

    assert_success(
        client.update(
            "/quests/1",
            description="Newer desc",
            creator="tommy@example.com"
        ),
        {
            "href": "/api/v1/quests/1",
            "id": 1,
            "creator": "tommy@example.com",
            "targetTime": str(target_time),
            "description": "Newer desc",
            "completionTime": None
        },
        strip=["embarkTime", "labors"]
    )

    assert_success(
        client.get("/quests/1"),
        {
            "href": "/api/v1/quests/1",
            "id": 1,
            "creator": "tommy@example.com",
            "targetTime": str(target_time),
            "description": "Newer desc",
            "completionTime": None
        },
        strip=["embarkTime", "labors"]
    )
