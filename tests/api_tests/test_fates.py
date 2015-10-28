import json
import pytest
import requests

from .fixtures import tornado_server, tornado_app, sample_data1_server
from .util import (
    assert_error, assert_success, assert_created, assert_deleted, Client
)


def test_malformed(sample_data1_server):
    client = sample_data1_server
    assert_error(client.post("/fates", data="Non-JSON"), 400)


def test_bad_creation(sample_data1_server):
    """Fate's must be either set to forOwner, forCreator, or both"""
    client = sample_data1_server
    assert_error(
        client.post(
            "/fates",
            data={
                "creationEventTypeId": 6,
                "forOwner": False,
                "forCreator": False,
                "precedesIds": [],
                "description":"New fate"
            }
        ),
        400
    )


def test_creation(sample_data1_server):
    client = sample_data1_server
    assert_success(
        client.get("/eventtypes"),
        {
            "limit": 10,
            "offset": 0,
            "totalEventTypes": 7,
        },
        strip="eventTypes"
    )

    assert_created(
        client.create(
            "/fates/",
            creationEventTypeId=6,
            description="New fate"
        ),
        "/api/v1/fates/6"
    )

    assert_created(
        client.create(
            "/fates/",
            creationEventTypeId=7,
            followsId=6,
            description="New fate2"
        ),
        "/api/v1/fates/7"
    )

    assert_success(
        client.get("/fates/6"),
        {
            "id": 6,
            "creationEventTypeId": 6,
            "followsId": None,
            "forOwner": True,
            "forCreator": False,
            "precedesIds": [7],
            "description": "New fate"
        }
    )

    assert_success(
        client.get("/fates/7"),
        {
            "id": 7,
            "creationEventTypeId": 7,
            "followsId": 6,
            "forOwner": True,
            "forCreator": False,
            "precedesIds": [],
            "description": "New fate2"
        }
    )


def test_update(sample_data1_server):
    client = sample_data1_server
    assert_created(
        client.create(
            "/fates/",
            creationEventTypeId=6,
            description="New fate"
        ),
        "/api/v1/fates/6"
    )

    assert_success(
        client.get("/fates/6"),
        {
            "id": 6,
            "creationEventTypeId": 6,
            "followsId": None,
            "forOwner": True,
            "forCreator": False,
            "precedesIds": [],
            "description": "New fate"
        }
    )

    assert_success(
        client.update(
            "/fates/6",
            followsId=1
        ),
        {
            "id": 6,
            "creationEventTypeId": 6,
            "followsId": 1,
            "forOwner": True,
            "forCreator": False,
            "precedesIds": [],
            "description": "New fate"
        }
    )

    assert_success(
        client.update(
            "/fates/6",
            description="New desc"
        ),
        {
            "id": 6,
            "creationEventTypeId": 6,
            "followsId": 1,
            "forOwner": True,
            "forCreator": False,
            "precedesIds": [],
            "description": "New desc"
        }
    )

    assert_success(
        client.update(
            "/fates/6",
            followsId=None,
            description="Another desc"
        ),
        {
            "id": 6,
            "creationEventTypeId": 6,
            "followsId": None,
            "forOwner": True,
            "forCreator": False,
            "precedesIds": [],
            "description": "Another desc"
        }
    )

    assert_success(
        client.get("/fates/6"),
        {
            "id": 6,
            "creationEventTypeId": 6,
            "followsId": None,
            "forOwner": True,
            "forCreator": False,
            "precedesIds": [],
            "description": "Another desc"
        }
    )

