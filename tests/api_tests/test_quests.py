import json
import pytest
import requests
import logging

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

    # We start with 2 events in the test data
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

    # We start with 0 quests in the test data
    assert_success(
        client.get("/quests"),
        {
            "limit": 10,
            "offset": 0,
            "totalQuests": 0,
            "quests": []
        }
    )

    # We create a quest with a target time 7 days from today
    target_time = datetime.utcnow() + timedelta(days=7)
    assert_created(
        client.create(
            "/quests",
            creator="johnny@example.com",
            fateId=1,
            targetTime=str(target_time),
            description="This is a quest almighty",
            hostnames=["example", "sample", "test"]
        ),
        "/api/v1/quests/1"
    )

    assert_success(
        client.get("/quests"),
        {
            "limit": 10,
            "offset": 0,
            "totalQuests": 1
        },
        strip=["quests"]
    )

    assert_success(
        client.get("/quests/1"),
        {
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
            "limit": 10,
            "offset": 0,
            "totalEvents": 5
        },
        strip=["events"]
    )


def test_update(sample_data1_server):
    client = sample_data1_server

    target_time = datetime.utcnow() + timedelta(days=7)
    target_time2 = datetime.utcnow() + timedelta(days=12)

    # Create a quest
    assert_created(
        client.create(
            "/quests",
            creator="johnny@example.com",
            fateId=1,
            targetTime=str(target_time),
            description="This is a quest almighty",
            hostnames=["example", "sample", "test"]
        ),
        "/api/v1/quests/1"
    )

    # Update the creator of the quest
    assert_success(
        client.update(
            "/quests/1",
            creator="betsy@example.com"
        ),
        {
            "id": 1,
            "creator": "betsy@example.com",
            "targetTime": str(target_time),
            "description": "This is a quest almighty",
            "completionTime": None
        },
        strip=["embarkTime", "labors"]
    )

    # Verify the creator has changed
    assert_success(
        client.get("/quests/1"),
        {
            "id": 1,
            "creator": "betsy@example.com",
            "targetTime": str(target_time),
            "description": "This is a quest almighty",
            "completionTime": None
        },
        strip=["embarkTime", "labors"]
    )

    # Update the description
    assert_success(
        client.update(
            "/quests/1",
            description="New desc"
        ),
        {
            "id": 1,
            "creator": "betsy@example.com",
            "targetTime": str(target_time),
            "description": "New desc",
            "completionTime": None
        },
        strip=["embarkTime", "labors"]
    )

    # Verify the new description
    assert_success(
        client.get("/quests/1"),
        {
            "id": 1,
            "creator": "betsy@example.com",
            "targetTime": str(target_time),
            "description": "New desc",
            "completionTime": None
        },
        strip=["embarkTime", "labors"]
    )

    # Update both creator and description
    assert_success(
        client.update(
            "/quests/1",
            description="Newer desc",
            creator="tommy@example.com"
        ),
        {
            "id": 1,
            "creator": "tommy@example.com",
            "targetTime": str(target_time),
            "description": "Newer desc",
            "completionTime": None
        },
        strip=["embarkTime", "labors"]
    )

    # Verify both creator and description have updated
    assert_success(
        client.get("/quests/1"),
        {
            "id": 1,
            "creator": "tommy@example.com",
            "targetTime": str(target_time),
            "description": "Newer desc",
            "completionTime": None
        },
        strip=["embarkTime", "labors"]
    )

    # Update the target time
    assert_success(
        client.update(
            "/quests/1",
            targetTime=str(target_time2)
        ),
        {
            "id": 1,
            "creator": "tommy@example.com",
            "targetTime": str(target_time2),
            "description": "Newer desc",
            "completionTime": None
        },
        strip=["embarkTime", "labors"]
    )

    # Verify target time updated
    assert_success(
        client.get("/quests/1"),
        {
            "id": 1,
            "creator": "tommy@example.com",
            "targetTime": str(target_time2),
            "description": "Newer desc",
            "completionTime": None
        },
        strip=["embarkTime", "labors"]
    )


def test_quest_lifecycle(sample_data1_server, caplog):
    caplog.setLevel(logging.INFO)
    client = sample_data1_server

    # We start with 2 events in the test data
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

    # We start with 0 quests in the test data
    assert_success(
        client.get("/quests"),
        {
            "limit": 10,
            "offset": 0,
            "totalQuests": 0,
            "quests": []
        }
    )

    target_time = datetime.utcnow() + timedelta(days=7)

    # Create a quest with system-maintenance required
    assert_created(
        client.create(
            "/quests",
            creator="johnny",
            fateId=3,
            targetTime=str(target_time),
            description="This is a quest almighty",
            hostnames=["example", "sample", "test"]
        ),
        "/api/v1/quests/1"
    )

    # make sure we now have 5 events (we started with 2 and
    # we just created 3)
    assert_success(
        client.get("/events"),
        {
            "limit": 10,
            "offset": 0,
            "totalEvents": 5
        },
        strip=["events"]
    )

    # Make sure we created the appropriate labors for this quest
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
                        "fateId": 3,
                        "closingFateId": None,
                        "forOwner": True,
                        "forCreator": False,
                        "id": 1,
                        "startingLaborId": None,
                        "questId": 1},
                       {"ackTime": None,
                        "ackUser": None,
                        "completionEventId": None,
                        "creationEventId": 4,
                        "targetTime": str(target_time),
                        "hostId": 2,
                        "fateId": 3,
                        "closingFateId": None,
                        "forOwner": True,
                        "forCreator": False,
                        "id": 2,
                        "startingLaborId": None,
                        "questId": 1},
                       {"ackTime": None,
                        "ackUser": None,
                        "completionEventId": None,
                        "creationEventId": 5,
                        "targetTime": str(target_time),
                        "hostId": 3,
                        "fateId": 3,
                        "closingFateId": None,
                        "forOwner": True,
                        "forCreator": False,
                        "id": 3,
                        "startingLaborId": None,
                        "questId": 1}],
        },
        strip=["creationTime", "completionTime"]
    )

    # Ensure that the quest doesn't have a completion time yet
    # Also, test two meta features: progress info and
    # filtering to show only open labors
    assert_success(
        client.get("/quests/1?progressInfo=true"),
        {
            "creator": "johnny@example.com",
            "description": "This is a quest almighty",
            "id": 1,
            "totalLabors": 3,
            "unstartedLabors": 3,
            "inprogressLabors": 0,
            "completedLabors": 0,
            "percentComplete": 0.0,
        },
        strip=["embarkTime", "creationTime", "completionTime", "targetTime"]
    )

    # Throw events that should trigger intermediate labors
    client.create(
        "/events",
        questId=1,
        user="testman@example.com",
        eventTypeId=4,
        note="There are intermediate triggering events"
    )

    # make sure we now have 8 events (we started with 2 and
    # we created 3 at the start and 3 more just now)
    assert_success(
        client.get("/events"),
        {
            "limit": 10,
            "offset": 0,
            "totalEvents": 8
        },
        strip=["events"]
    )

    # Make sure we created the appropriate labors for this quest
    assert_success(
        client.get("/labors"),
        {
            "limit": 10,
            "offset": 0,
            "totalLabors": 6,
            "labors": [{"ackTime": None,
                        "ackUser": None,
                        "completionEventId": 6,
                        "creationEventId": 3,
                        "targetTime": str(target_time),
                        "hostId": 1,
                        "fateId": 3,
                        "closingFateId": 4,
                        "forOwner": True,
                        "forCreator": False,
                        "id": 1,
                        "startingLaborId": None,
                        "questId": 1},
                       {"ackTime": None,
                        "ackUser": None,
                        "completionEventId": 7,
                        "creationEventId": 4,
                        "targetTime": str(target_time),
                        "hostId": 2,
                        "fateId": 3,
                        "closingFateId": 4,
                        "forOwner": True,
                        "forCreator": False,
                        "id": 2,
                        "startingLaborId": None,
                        "questId": 1},
                       {"ackTime": None,
                        "ackUser": None,
                        "completionEventId": 8,
                        "creationEventId": 5,
                        "targetTime": str(target_time),
                        "hostId": 3,
                        "fateId": 3,
                        "closingFateId": 4,
                        "forOwner": True,
                        "forCreator": False,
                        "id": 3,
                        "startingLaborId": None,
                        "questId": 1},
                       {"ackTime": None,
                        "ackUser": None,
                        "completionEventId": None,
                        "creationEventId": 6,
                        "targetTime": str(target_time),
                        "hostId": 1,
                        "fateId": 4,
                        "closingFateId": None,
                        "id": 4,
                        "forOwner": False,
                        "forCreator": True,
                        "startingLaborId": 1,
                        "questId": 1},
                       {"ackTime": None,
                        "ackUser": None,
                        "completionEventId": None,
                        "creationEventId": 7,
                        "targetTime": str(target_time),
                        "hostId": 2,
                        "fateId": 4,
                        "closingFateId": None,
                        "forOwner": False,
                        "forCreator": True,
                        "id": 5,
                        "startingLaborId": 2,
                        "questId": 1},
                       {"ackTime": None,
                        "ackUser": None,
                        "completionEventId": None,
                        "creationEventId": 8,
                        "targetTime": str(target_time),
                        "hostId": 3,
                        "forOwner": False,
                        "forCreator": True,
                        "fateId": 4,
                        "closingFateId": None,
                        "id": 6,
                        "startingLaborId": 3,
                        "questId": 1}]
        },
        strip=["creationTime", "completionTime"]
    )

    # Ensure that the quest doesn't have a completion time yet
    # Also, test two meta features: progress info and
    # filtering to show only open labors
    assert_success(
        client.get("/quests/1?progressInfo=true&onlyOpenLabors=true&expand=labors&expand=eventtypes&expand=fates"),
        {
            "creator": "johnny@example.com",
            "description": "This is a quest almighty",
            "id": 1,
            "totalLabors": 3,
            "unstartedLabors": 0,
            "inprogressLabors": 3,
            "completedLabors": 0,
            "percentComplete": 50.0,
            "labors": [
                {
                    "ackTime": None,
                    "ackUser": None,
                    "completionEventId": None,
                    "creationEventId": 6,
                    "hostId": 1,
                    "forOwner": False,
                    "forCreator": True,
                    "id": 4,
                    "fateId": 4,
                    "closingFateId": None,
                    "fate": {
                        "creationEventType": {
                            "category": "system-maintenance",
                            "state": "ready",
                            "id": 4,
                            "description": "This system is ready for maintenance.",
                            "restricted": False,
                        },
                        "creationEventTypeId": 4,
                        "description": "A system that needs maintenance made ready before maintenance can occur.",
                        "followsId": 3,
                        "forOwner": False,
                        "forCreator": True,
                        "id": 4,
                        "precedesIds": [5],
                    },
                    "closingFate": None,
                    "startingLaborId": 1,
                    "questId": 1
                },
                {
                    "ackTime": None,
                    "ackUser": None,
                    "completionEventId": None,
                    "creationEventId": 7,
                    "hostId": 2,
                    "forOwner": False,
                    "forCreator": True,
                    "id": 5,
                    "fateId": 4,
                    "closingFateId": None,
                    "fate": {
                        "creationEventType": {
                            "category": "system-maintenance",
                            "state": "ready",
                            "id": 4,
                            "description": "This system is ready for maintenance.",
                            "restricted": False,
                        },
                        "creationEventTypeId": 4,
                        "description": "A system that needs maintenance made ready before maintenance can occur.",
                        "followsId": 3,
                        "forOwner": False,
                        "forCreator": True,
                        "id": 4,
                        "precedesIds": [5],
                    },
                    "closingFate": None,
                    "startingLaborId": 2,
                    "questId": 1
                },
                {
                    "ackTime": None,
                    "ackUser": None,
                    "completionEventId": None,
                    "creationEventId": 8,
                    "hostId": 3,
                    "forOwner": False,
                    "forCreator": True,
                    "id": 6,
                    "fateId": 4,
                    "closingFateId": None,
                    "fate": {
                        "creationEventType": {
                            "category": "system-maintenance",
                            "state": "ready",
                            "id": 4,
                            "description": "This system is ready for maintenance.",
                            "restricted": False,
                        },
                        "creationEventTypeId": 4,
                        "description": "A system that needs maintenance made ready before maintenance can occur.",
                        "followsId": 3,
                        "forOwner": False,
                        "forCreator": True,
                        "id": 4,
                        "precedesIds": [5],
                    },
                    "closingFate": None,
                    "startingLaborId": 3,
                    "questId": 1
                }
            ]
        },
        strip=["embarkTime", "creationTime", "completionTime", "targetTime"]
    )

    # Throw events that should trigger closing of the intermediate labors
    client.create(
        "/events",
        questId=1,
        user="testman@example.com",
        eventTypeId=5,
        note="There are intermediate triggering events"
    )

    # make sure we now have 11 events
    assert_success(
        client.get("/events"),
        {
            "limit": 10,
            "offset": 0,
            "totalEvents": 11
        },
        strip=["events"]
    )

    # Make sure we created the appropriate labors for this quest
    assert_success(
        client.get("/labors"),
        {
            "limit": 10,
            "offset": 0,
            "totalLabors": 6,
            "labors": [{"ackTime": None,
                        "ackUser": None,
                        "completionEventId": 6,
                        "creationEventId": 3,
                        "targetTime": str(target_time),
                        "hostId": 1,
                        "forOwner": True,
                        "forCreator": False,
                        "id": 1,
                        "fateId": 3,
                        "closingFateId": 4,
                        "startingLaborId": None,
                        "questId": 1},
                       {"ackTime": None,
                        "ackUser": None,
                        "completionEventId": 7,
                        "creationEventId": 4,
                        "targetTime": str(target_time),
                        "hostId": 2,
                        "forOwner": True,
                        "forCreator": False,
                        "id": 2,
                        "fateId": 3,
                        "closingFateId": 4,
                        "startingLaborId": None,
                        "questId": 1},
                       {"ackTime": None,
                        "ackUser": None,
                        "completionEventId": 8,
                        "creationEventId": 5,
                        "targetTime": str(target_time),
                        "hostId": 3,
                        "forOwner": True,
                        "forCreator": False,
                        "id": 3,
                        "fateId": 3,
                        "closingFateId": 4,
                        "startingLaborId": None,
                        "questId": 1},
                       {"ackTime": None,
                        "ackUser": None,
                        "completionEventId": 9,
                        "creationEventId": 6,
                        "targetTime": str(target_time),
                        "hostId": 1,
                        "forOwner": False,
                        "forCreator": True,
                        "id": 4,
                        "fateId": 4,
                        "closingFateId": 5,
                        "startingLaborId": 1,
                        "questId": 1},
                       {"ackTime": None,
                        "ackUser": None,
                        "completionEventId": 10,
                        "creationEventId": 7,
                        "targetTime": str(target_time),
                        "hostId": 2,
                        "forOwner": False,
                        "forCreator": True,
                        "fateId": 4,
                        "closingFateId": 5,
                        "id": 5,
                        "startingLaborId": 2,
                        "questId": 1},
                       {"ackTime": None,
                        "ackUser": None,
                        "completionEventId": 11,
                        "creationEventId": 8,
                        "targetTime": str(target_time),
                        "hostId": 3,
                        "forOwner": False,
                        "forCreator": True,
                        "fateId": 4,
                        "closingFateId": 5,
                        "id": 6,
                        "startingLaborId": 3,
                        "questId": 1}]
        },
        strip=["creationTime", "completionTime"]
    )

    # Ensure that the quest doesn't have a completion time yet
    quest_info = client.get("/quests/1").json()

    assert quest_info["completionTime"] is not None

    assert_success(
        client.get("/labors/?startingLaborId=3"),
        {
            "limit": 10,
            "offset": 0,
            "totalLabors": 2,
            "labors": [{"ackTime": None,
                        "ackUser": None,
                        "completionEventId": 8,
                        "creationEventId": 5,
                        "targetTime": str(target_time),
                        "hostId": 3,
                        "forOwner": True,
                        "forCreator": False,
                        "id": 3,
                        "fateId": 3,
                        "closingFateId": 4,
                        "startingLaborId": None,
                        "questId": 1},
                       {"ackTime": None,
                        "ackUser": None,
                        "completionEventId": 11,
                        "creationEventId": 8,
                        "targetTime": str(target_time),
                        "hostId": 3,
                        "forOwner": False,
                        "forCreator": True,
                        "id": 6,
                        "fateId": 4,
                        "closingFateId": 5,
                        "startingLaborId": 3,
                        "questId": 1}]
        },
        strip=["creationTime", "completionTime"]
    )

    assert_success(
        client.get("/quests/1?progressInfo=true&onlyOpenLabors=true&expand=labors"),
        {
            "creator": "johnny@example.com",
            "description": "This is a quest almighty",
            "id": 1,
            "totalLabors": 3,
            "unstartedLabors": 0,
            "inprogressLabors": 0,
            "completedLabors": 3,
            "percentComplete": 100.0,
            "labors": [
            ]
        },
        strip=["embarkTime", "creationTime", "completionTime", "targetTime"]
    )


def test_filter_by_creator(sample_data1_server):
    client = sample_data1_server
    # We start with 0 quests in the test data
    assert_success(
        client.get("/quests"),
        {
            "limit": 10,
            "offset": 0,
            "totalQuests": 0,
            "quests": []
        }
    )

    # Have johnny create a quest
    assert_created(
        client.create(
            "/quests",
            creator="johnny@example.com",
            fateId=1,
            description="This is a quest almighty",
            hostnames=["example", "sample", "test"]
        ),
        "/api/v1/quests/1"
    )

    # Have bonny create a quest
    assert_created(
        client.create(
            "/quests",
            creator="bonny@example.com",
            fateId=1,
            description="This is a quest not so almighty",
            hostnames=["example", "sample", "test"]
        ),
        "/api/v1/quests/2"
    )

    assert_success(
        client.get("/quests"),
        {
            "limit": 10,
            "offset": 0,
            "totalQuests": 2
        },
        strip=["quests"]
    )

    quest_1 = client.get("/quests?byCreator=johnny@example.com").json()
    quest_2 = client.get("/quests?byCreator=bonny@example.com").json()

    assert len(quest_1['quests']) == 1
    assert quest_1['quests'][0]['id'] == 1
    assert len(quest_2['quests']) == 1
    assert quest_2['quests'][0]['id'] == 2

    assert_success(
        client.get("/quests?byCreator=noone@example.com"),
        {
            "limit": 10,
            "offset": 0,
            "totalQuests": 0
        },
        strip=["quests"]
    )


def test_filter_by_hostnames(sample_data1_server):
    client = sample_data1_server
    # We start with 0 quests in the test data
    assert_success(
        client.get("/quests"),
        {
            "limit": 10,
            "offset": 0,
            "totalQuests": 0,
            "quests": []
        }
    )

    # Have johnny create a quest
    assert_created(
        client.create(
            "/quests",
            creator="johnny@example.com",
            fateId=1,
            description="This is a quest almighty",
            hostnames=["sample"]
        ),
        "/api/v1/quests/1"
    )

    # Have bonny create a quest
    assert_created(
        client.create(
            "/quests",
            creator="bonny@example.com",
            fateId=1,
            description="This is a quest not so almighty",
            hostnames=["example", "sample", "test"]
        ),
        "/api/v1/quests/2"
    )

    assert_success(
        client.get("/quests"),
        {
            "limit": 10,
            "offset": 0,
            "totalQuests": 2
        },
        strip=["quests"]
    )

    quest_1 = client.get("/quests?hostnames=example,test").json()
    quest_2 = client.get("/quests?hostnames=sample").json()

    assert len(quest_1['quests']) == 1
    assert quest_1['quests'][0]['id'] == 2
    assert len(quest_2['quests']) == 2
    assert quest_2['quests'][0]['id'] == 1
    assert quest_2['quests'][1]['id'] == 2

    assert_success(
        client.get("/quests?hostnames=not-a-server"),
        {
            "limit": 10,
            "offset": 0,
            "totalQuests": 0
        },
        strip=["quests"]
    )





