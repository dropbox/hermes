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
            completionEventTypeId=7,
            precedes_ids=[],
            description="New fate"
        ),
        "/api/v1/fates/4"
    )

    assert_success(
        client.get("/fates/4"),
        {
            "id": 4,
            "creationEventTypeId": 6,
            "completionEventTypeId": 7,
            "follows_id": None,
            "precedes_ids": [],
            "description": "New fate"
        }
    )


def test_update(sample_data1_server):
    client = sample_data1_server
    assert_created(
        client.create(
            "/fates/",
            creationEventTypeId=6,
            completionEventTypeId=7,
            description="New fate"
        ),
        "/api/v1/fates/4"
    )

    assert_success(
        client.get("/fates/4"),
        {
            "id": 4,
            "creationEventTypeId": 6,
            "completionEventTypeId": 7,
            "follows_id": None,
            "precedes_ids": [],
            "description": "New fate"
        }
    )

    assert_success(
        client.update(
            "/fates/4",
            follows_id=1
        ),
        {
            "id": 4,
            "creationEventTypeId": 6,
            "completionEventTypeId": 7,
            "follows_id": 1,
            "precedes_ids": [],
            "description": "New fate"
        }
    )

    assert_success(
        client.update(
            "/fates/4",
            description="New desc"
        ),
        {
            "id": 4,
            "creationEventTypeId": 6,
            "completionEventTypeId": 7,
            "follows_id": 1,
            "precedes_ids": [],
            "description": "New desc"
        }
    )

    assert_success(
        client.update(
            "/fates/4",
            follows_id=None,
            description="Another desc"
        ),
        {
            "id": 4,
            "creationEventTypeId": 6,
            "completionEventTypeId": 7,
            "follows_id": None,
            "precedes_ids": [],
            "description": "Another desc"
        }
    )

    assert_success(
        client.get("/fates/4"),
        {
            "id": 4,
            "creationEventTypeId": 6,
            "completionEventTypeId": 7,
            "follows_id": None,
            "precedes_ids": [],
            "description": "Another desc"
        }
    )

