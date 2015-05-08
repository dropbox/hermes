import pytest
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes import models

from .fixtures import session


def test_creation(session):
    models.EventType.create(session, "foo", "bar", "This is a test")
    session.commit()

    event_types = session.query(models.EventType).all()

    assert len(event_types) == 1
    assert event_types[0].id == 1
    assert event_types[0].category == "foo"
    assert event_types[0].state == "bar"
    assert event_types[0].description == "This is a test"
