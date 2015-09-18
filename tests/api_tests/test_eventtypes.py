import json
import pytest
import requests

from .fixtures import tornado_server, tornado_app, sample_data1_server
from .util import (
    assert_error, assert_success, assert_created, assert_deleted, Client
)


def test_malformed(tornado_server):
    client = Client(tornado_server)
    assert_error(client.post("/eventtypes", data="Non-JSON"), 400)


def test_creation(tornado_server):
    client = Client(tornado_server)
    assert_success(client.get("/eventtypes"), {
        "eventTypes": [],
        "limit": 10,
        "offset": 0,
        "totalEventTypes": 0,
    })

    assert_created(
        client.create(
            "/eventtypes",
            category="foo",
            state="bar",
            description="This is a test"
        ), "/api/v1/eventtypes/1"
    )
    assert_error(
        client.create(
            "/eventtypes",
            category="foo",
            state="bar",
            description="Reject duplicate"
        ), 409
    )

    assert_success(
        client.get("/eventtypes"),
        {
            "eventTypes": [{
                          "id": 1,
                          "category": "foo",
                          "state": "bar",
                          "description": "This is a test",
                      }],
            "limit": 10,
            "offset": 0,
            "totalEventTypes": 1,
        }
    )

    assert_success(
        client.get("/eventtypes/1"),
        {
            "id": 1,
            "category": "foo",
            "state": "bar",
            "description": "This is a test",
            "events": [],
            "fates": [],
            "limit": 10,
            "offset": 0,
        }
    )

    assert_created(
        client.create(
            "/eventtypes",
            category="foo",
            state="baz",
            description="This is a second test"
        ), "/api/v1/eventtypes/2"
    )
    assert_success(
        client.get("/eventtypes", params={"category": "foo", "state": "baz"}),
        {
            "eventTypes": [{
                          "id": 2,
                          "category": "foo",
                          "state": "baz",
                          "description": "This is a second test",
                      }],
            "limit": 10,
            "offset": 0,
            "totalEventTypes": 1
        }
    )

def test_create_multiple(tornado_server):
    client = Client(tornado_server)
    assert_success(client.get("/eventtypes"), {
        "eventTypes": [],
        "limit": 10,
        "offset": 0,
        "totalEventTypes": 0,
    })

    client.create(
        "/eventtypes",
        eventTypes=[
            {
                "category": "foo",
                "state": "bar",
                "description": "This is a test"
            },
            {
                "category": "foo",
                "state": "baz",
                "description": "This is a 2nd test"
            }
        ]
    )

    assert_success(client.get("/eventtypes"), {
        "limit": 10,
        "offset": 0,
        "totalEventTypes": 2,
    }, strip="eventTypes")


def test_update(tornado_server):
    client = Client(tornado_server)
    assert_success(client.get("/eventtypes"), {
        "eventTypes": [],
        "limit": 10,
        "offset": 0,
        "totalEventTypes": 0,
    })

    assert_created(
        client.create(
            "/eventtypes",
            category="foo",
            state="bar",
            description="This is a test"
        ), "/api/v1/eventtypes/1"
    )

    assert_success(
        client.update("/eventtypes/1", description="new"),
        {
            "id": 1,
            "category": "foo",
            "state": "bar",
            "description": "new",
        }
    )

    assert_error(client.update("/eventtypes/1"), 400)

def test_filter_by_creating_types(sample_data1_server):
    client = sample_data1_server

    assert_success(
        client.get("/eventtypes?startingTypes=true"),{
        "limit": 10,
        "offset": 0,
        "totalEventTypes": 2
    }, strip=['eventTypes']
    )
