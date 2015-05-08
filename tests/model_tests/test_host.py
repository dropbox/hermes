import pytest
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes import models

from .fixtures import session


def test_creation(session):
    models.Host.create(session, "abc-123")
    session.commit()

    hosts = session.query(models.Host).all()

    assert len(hosts) == 1
    assert hosts[0].id == 1
    assert hosts[0].hostname == "abc-123"


def test_duplicate(session):
    models.Host.create(session, "abc-123")

    with pytest.raises(IntegrityError):
        models.Host.create(session, "abc-123")

    models.Host.create(session, "abc-456")


def test_required(session):
    models.Host.create(session, "abc-123")

    with pytest.raises(exc.ValidationError):
        models.Host.create(session, None)
