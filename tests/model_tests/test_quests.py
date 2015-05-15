import pytest
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes.models import EventType, Host, Quest, Achievement, Event

from .fixtures import db_engine, session, sample_data1


def test_creation(sample_data1):
    hosts = ['example.dropbox.com', 'test.dropbox.com']

    achievements = sample_data1.query(Achievement).all()
    assert len(achievements) == 0

    creation_event_type = (
        sample_data1.query(EventType)
        .filter(EventType.id == 3).first()
    )

    Quest.create(
        sample_data1, "testman", hosts, creation_event_type,
        description="Embark on the long road of maintenance"
    )

    quests = sample_data1.query(Quest).all()

    assert len(quests) == 1
    assert quests[0].embark_time is not None
    assert quests[0].completion_time is None
    assert quests[0].description == "Embark on the long road of maintenance"
    assert quests[0].creator == "testman"
    assert len(quests[0].achievements) == 2

    achievements = Achievement.get_open_unacknowledged(sample_data1)
    assert len(achievements) == 2

    # now we want to test the closing of the quest by throwing events
    # that fulfill the achievements

    found_hosts = sample_data1.query(Host).filter(Host.hostname.in_(hosts)).all()

    assert len(found_hosts) == 2

    completion_event_type = (
        sample_data1.query(EventType)
        .filter(EventType.id == 4).first()
    )

    Event.create(
        sample_data1, found_hosts[0], "testdude", completion_event_type
    )
    Event.create(
        sample_data1, found_hosts[1], "testdude", completion_event_type
    )

    achievements = Achievement.get_open_unacknowledged(sample_data1)
    assert len(achievements) == 0

    quests = sample_data1.query(Quest).all()

    assert len(quests) == 1
    assert quests[0].embark_time is not None
    assert quests[0].completion_time is not None
    assert quests[0].description == "Embark on the long road of maintenance"
    assert quests[0].creator == "testman"
    assert len(quests[0].achievements) == 2


def test_mass_creation(sample_data1):
    hosts = ['example.dropbox.com', 'test.dropbox.com']

    achievements = sample_data1.query(Achievement).all()
    assert len(achievements) == 0

    creation_event_type1 = (
        sample_data1.query(EventType)
        .filter(EventType.id == 1).first()
    )
    creation_event_type2 = (
        sample_data1.query(EventType)
        .filter(EventType.id == 3).first()
    )

    Quest.create(
        sample_data1, "testman", hosts, creation_event_type1,
        description="Embark on the long road of maintenance"
    )
    Quest.create(
        sample_data1, "testman", hosts, creation_event_type1,
        description="Embark on the longer road of maintenance"
    )
    Quest.create(
        sample_data1, "testman", hosts, creation_event_type2,
        description="WHEN WILL IT END!!"
    )

    quests = sample_data1.query(Quest).all()

    assert len(quests) == 3
    assert quests[0].embark_time is not None
    assert quests[0].completion_time is None
    assert quests[0].description == "Embark on the long road of maintenance"
    assert quests[0].creator == "testman"
    assert quests[1].embark_time is not None
    assert quests[1].completion_time is None
    assert quests[2].embark_time is not None
    assert quests[2].completion_time is None
    assert len(quests[0].achievements) == 2
    assert len(quests[1].achievements) == 2
    assert len(quests[2].achievements) == 2

    achievements = Achievement.get_open_unacknowledged(sample_data1)
    assert len(achievements) == 6

    # now we want to test the closing of the quest by throwing events
    # that fulfill the achievements

    found_hosts = sample_data1.query(Host).filter(Host.hostname.in_(hosts)).all()

    assert len(found_hosts) == 2

    completion_event_type1 = (
        sample_data1.query(EventType)
        .filter(EventType.id == 2).first()
    )
    completion_event_type2 = (
        sample_data1.query(EventType)
        .filter(EventType.id == 4).first()
    )

    Event.create(
        sample_data1, found_hosts[0], "testdude", completion_event_type1
    )
    Event.create(
        sample_data1, found_hosts[1], "testdude", completion_event_type1
    )

    achievements = Achievement.get_open_unacknowledged(sample_data1)
    assert len(achievements) == 2

    quests = sample_data1.query(Quest).all()

    assert len(quests) == 3
    assert quests[0].embark_time is not None
    assert quests[0].completion_time is not None
    assert quests[1].embark_time is not None
    assert quests[1].completion_time is not None
    assert quests[2].embark_time is not None
    assert quests[2].completion_time is None
    assert quests[0].description == "Embark on the long road of maintenance"
    assert quests[0].creator == "testman"
    assert len(quests[0].achievements) == 2








