import pytest
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes.models import Host

from .fixtures import db_engine, session, sample_data1


def test_creation(session):
    Host.create(session, "abc-123")
    session.commit()

    hosts = session.query(Host).all()

    assert len(hosts) == 1
    assert hosts[0].id == 1
    assert hosts[0].hostname == "abc-123"

    host = Host.get_host(session, "abc-123")
    assert host.id == 1
    assert host.hostname == "abc-123"


def test_duplicate(session):
    Host.create(session, "abc-123")

    with pytest.raises(IntegrityError):
        Host.create(session, "abc-123")

    Host.create(session, "abc-456")


def test_required(session):
    Host.create(session, "abc-123")

    with pytest.raises(exc.ValidationError):
        Host.create(session, None)

def test_helpers(sample_data1):
    host = Host.get_host(sample_data1, "example.dropbox.com")
    assert host.id == 1
    assert host.hostname == "example.dropbox.com"

    events = host.get_latest_events().all()

    assert len(events) == 2
    assert events[0].note == "example.dropbox.com rebooted."
