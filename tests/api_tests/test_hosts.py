import json
import pytest
import requests

from .fixtures import tornado_server, tornado_app
from .util import (
    assert_error, assert_success, assert_created, assert_deleted, Client
)


def test_malformed(tornado_server):
    client = Client(tornado_server)
    assert_error(client.post("/hosts", data="Non-JSON"), 400)


def test_creation(tornado_server):
    client = Client(tornado_server)
    assert_success(client.get("/hosts"), {
        "hosts": [],
        "limit": 10,
        "offset": 0,
        "totalHosts": 0,
    })

    assert_created(
        client.create("/hosts", hostname="example"), "/api/v1/hosts/example"
    )
    assert_error(client.create("/hosts", hostname="example"), 409)

    assert_success(
        client.get("/hosts"),
        {
            "hosts": [{
                          "id": 1,
                          "hostname": "example"
                      }],
            "limit": 10,
            "offset": 0,
            "totalHosts": 1,
        }
    )

    assert_success(
        client.get("/hosts/example"),
        {
            "id": 1,
            "hostname": "example",
            "events": [],
            "labors": [],
            "quests": [],
            "lastEvent": None,
            "limit": 10,
            "offset": 0,
        }
    )

    assert_created(client.create("/hosts", hostname="sample"), "/api/v1/hosts/sample")
    assert_success(
        client.get("/hosts", params={"hostname": "sample"}),
        {
            "hosts": [{
                          "id": 2,
                          "hostname": "sample"
                      }],
            "limit": 10,
            "offset": 0,
            "totalHosts": 1
        }
    )

def test_create_multiple(tornado_server):
    client = Client(tornado_server)
    assert_success(client.get("/hosts"), {
        "hosts": [],
        "limit": 10,
        "offset": 0,
        "totalHosts": 0,
    })

    client.create(
        "/hosts",
        hosts=[
            {"hostname":"example"},
            {"hostname":"sample"},
            {"hostname":"test"}
        ]
    )

    assert_success(client.get("/hosts"), {
        "limit": 10,
        "offset": 0,
        "totalHosts": 3,
    }, strip="hosts")


def test_update(tornado_server):
    client = Client(tornado_server)

    client.create("/hosts", hostname="testname")

    assert_success(
        client.update("/hosts/testname", hostname="newname"),
        {
            "id": 1,
            "hostname": "newname"
        }
    )

    # test failure of empty update calls
    assert_error(client.update("/hosts/newname"), 400)


def test_merging(tornado_server):
    """When renaming a server to an existing servername, just merge them"""
    client = Client(tornado_server)

    client.create("/hosts", hostname="testname")
    client.create("/hosts", hostname="newname")

    assert_success(
        client.update("/hosts/testname", hostname="newname"),
        {
            "id": 2,
            "hostname": "newname"
        }
    )