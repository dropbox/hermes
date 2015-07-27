import json
import pytest
import requests

from datetime import datetime, timedelta

from .fixtures import tornado_server, tornado_app, sample_data1_server
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
            "limit": 10,
            "offset": 0,
            "totalEvents": 2
        },
        strip=["timestamp", "events"]
    )

    assert_success(
        client.get("/quests"),
        {
            "limit": 10,
            "offset": 0,
            "totalQuests": 0,
            "quests": []
        }
    )

    assert_success(
        client.get("/labors"),
        {
            "limit": 10,
            "offset": 0,
            "totalLabors": 0,
            "labors": []
        }
    )

    target_time = datetime.utcnow() + timedelta(days=7)

    assert_created(
        client.create(
            "/quests",
            creator="johnny",
            eventTypeId=1,
            targetTime=str(target_time),
            description="This is a quest almighty",
            hostnames=["example", "sample", "test"]
        ),
        "/api/v1/quests/1"
    )

    assert_success(
        client.get("/labors"),
        {
            "limit": 10,
            "offset": 0,
            "totalLabors": 3,
            "labors": [{"ackTime": None,
                        "ackUser": None,
                        "completionEventId": None,
                        "creationEventId": 3,
                        "targetTime": str(target_time),
                        "hostId": 1,
                        "id": 1,
                        "startingLaborId": None,
                        "questId": 1},
                       {"ackTime": None,
                        "ackUser": None,
                        "completionEventId": None,
                        "creationEventId": 4,
                        "targetTime": str(target_time),
                        "hostId": 2,
                        "id": 2,
                        "startingLaborId": None,
                        "questId": 1},
                       {"ackTime": None,
                        "ackUser": None,
                        "completionEventId": None,
                        "creationEventId": 5,
                        "targetTime": str(target_time),
                        "hostId": 3,
                        "id": 3,
                        "startingLaborId": None,
                        "questId": 1}],
        },
        strip=["creationTime", "completionTime"]
    )


def test_update(sample_data1_server):
    client = sample_data1_server

    # create a quest without a target_time
    assert_created(
        client.create(
            "/quests",
            creator="johnny",
            eventTypeId=1,
            description="This is a quest almighty",
            hostnames=["example", "sample", "test"]
        ),
        "/api/v1/quests/1"
    )

    # make sure 3 labors was created for this quest
    assert_success(
        client.get("/labors"),
        {
            "limit": 10,
            "offset": 0,
            "totalLabors": 3
        },
        strip=["creationTime", "labors"]
    )

    # create a new event that would create another labor
    assert_created(
        client.create(
            "/events",
            hostname="example",
            user="testman@example.com",
            eventTypeId=1,
            note="This is a test event"
        ),
        "/api/v1/events/6"
    )

    # make sure the labor is not attached to a quest
    assert_success(
        client.get("/labors/4"),
        {
            "ackTime": None,
            "ackUser": None,
            "completionEventId": None,
            "completionTime": None,
            "creationEventId": 6,
            "hostId": 1,
            "id": 4,
            "startingLaborId": None,
            "questId": None
        },
        strip=["creationTime"]
    )

    # attach the labor to a quest
    response = client.update(
        "/labors/4",
        ackUser="johnny@example.com",
        questId=1
    )

    # make sure the labor is attached to the quest
    assert_success(
        response,
        {
            "ackUser": "johnny@example.com",
            "completionEventId": None,
            "completionTime": None,
            "creationEventId": 6,
            "targetTime": None,
            "hostId": 1,
            "id": 4,
            "startingLaborId": None,
            "questId": 1
        },
        strip=["creationTime", "ackTime"]
    )

    assert response.json()['ackTime'] is not None