import base64
import json
import logging
import os
import pytest
import requests
import socket
import threading
import tornado
import tornado.httpserver
import tornado.ioloop
from tornado import netutil

import hermes
from hermes import models
from hermes.models import Model, Session, Host, EventType, Event, Fate, Labor, Quest
from hermes.settings import settings
from hermes.app import Application
from .util import load_json, Client


sa_log = logging.getLogger("sqlalchemy.engine.base.Engine")

# Uncomment to have all queries printed out
# sa_log.setLevel(logging.INFO)


class Server(object):
    """ Wrapper around Tornado server with test helpers. """

    def __init__(self, tornado_app):
        self.server = tornado.httpserver.HTTPServer(
            tornado_app
        )
        self.server.add_sockets(netutil.bind_sockets(
            None, "localhost", family=socket.AF_INET
        ))
        self.server.start()
        self.io_thread = threading.Thread(
            target=tornado.ioloop.IOLoop.instance().start
        )
        self.io_thread.start()

    @property
    def port(self):
        return self.server._sockets.values()[0].getsockname()[1]


@pytest.fixture()
def tornado_app(request, tmpdir):
    db_path = tmpdir.join("nsot.sqlite")
    db_engine = models.get_db_engine("sqlite:///%s" % db_path)

    Model.metadata.drop_all(db_engine)
    Model.metadata.create_all(db_engine)
    Session.configure(bind=db_engine)

    Fate._all_fates = None

    my_settings = {
        "db_engine": db_engine,
        "db_session": Session,
    }

    tornado_settings = {
        "debug": False,
    }

    return Application(my_settings=my_settings, **tornado_settings)


@pytest.fixture()
def tornado_server(request, tornado_app):

    server = Server(tornado_app)

    def fin():
        tornado.ioloop.IOLoop.instance().stop()
        server.io_thread.join()
    request.addfinalizer(fin)

    return server


@pytest.fixture
def session(request, tmpdir):
    db_path = tmpdir.join("nsot.sqlite")
    db_engine = models.get_db_engine("sqlite:///%s" % db_path)

    Model.metadata.drop_all(db_engine)
    Model.metadata.create_all(db_engine)
    Session.configure(bind=db_engine)
    session = Session()

    def fin():
        session.close()
    request.addfinalizer(fin)

    return session

@pytest.fixture
def sample_data1_server(tornado_server):
    client = Client(tornado_server)
    hosts_data = load_json("set1/hosts.json")
    client.create("/hosts/", hosts=hosts_data["hosts"])

    event_types_data = load_json("set1/eventtypes.json")
    client.create("/eventtypes/", eventTypes=event_types_data["eventTypes"])

    events = load_json("set1/event.json")
    client.post("/events/", json=events["event1"])
    client.post("/events/", json=events['event2'])

    fates = load_json("set1/fates.json")
    client.post("/fates/", json=fates["fate1"])
    client.post("/fates/", json=fates["fate2"])
    client.post("/fates/", json=fates["fate3"])

    return client
