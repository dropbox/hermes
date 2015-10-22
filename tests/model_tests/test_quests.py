import pytest
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes.models import EventType, Host, Quest, Labor, Event, Fate

from datetime import datetime, timedelta

from .fixtures import db_engine, session, sample_data1, sample_data2


def test_date_constraint(sample_data1):
    hosts = [
        sample_data1.query(Host).filter(
            Host.hostname == 'example.dropbox.com'
        ).one(),
        sample_data1.query(Host).filter(
            Host.hostname == 'test.dropbox.com'
        ).one(),
    ]

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 0

    creation_event_type = (
        sample_data1.query(EventType)
        .filter(EventType.id == 1).first()
    )

    target_time = datetime.now() - timedelta(days=2)

    with pytest.raises(exc.ValidationError):
        Quest.create(
            sample_data1, "testman", hosts, creation_event_type, target_time,
            description="Embark on the long road of maintenance"
        )


def test_creation(sample_data1):
    hosts = [
        sample_data1.query(Host).filter(
            Host.hostname == 'example.dropbox.com'
        ).one(),
        sample_data1.query(Host).filter(
            Host.hostname == 'test.dropbox.com'
        ).one(),
    ]

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 0

    creation_event_type = (
        sample_data1.query(EventType)
        .filter(EventType.id == 1).first()
    )

    target_time = datetime.now() + timedelta(days=2)

    Quest.create(
        sample_data1, "testman", hosts, creation_event_type, target_time,
        description="Embark on the long road of maintenance"
    )

    quests = sample_data1.query(Quest).all()

    assert len(quests) == 1
    assert quests[0].embark_time is not None
    assert quests[0].completion_time is None
    assert quests[0].description == "Embark on the long road of maintenance"
    assert quests[0].creator == "testman"
    assert quests[0].target_time == target_time
    assert len(quests[0].labors) == 2

    labors = Labor.get_open_unacknowledged(sample_data1)
    assert len(labors) == 2

    # now we want to test the closing of the quest by throwing events
    # that fulfill the labors

    found_hosts = sample_data1.query(Host).filter(
        Host.hostname.in_(["example.dropbox.com", "test.dropbox.com"])
    ).all()

    assert len(found_hosts) == 2

    completion_event_type = (
        sample_data1.query(EventType)
        .filter(EventType.id == 2).first()
    )

    Event.create(
        sample_data1, found_hosts[0], "testdude", completion_event_type
    )
    Event.create(
        sample_data1, found_hosts[1], "testdude", completion_event_type
    )

    labors = Labor.get_open_unacknowledged(sample_data1)
    assert len(labors) == 0

    quests = sample_data1.query(Quest).all()

    assert len(quests) == 1
    assert quests[0].embark_time is not None
    assert quests[0].completion_time is not None
    assert quests[0].description == "Embark on the long road of maintenance"
    assert quests[0].creator == "testman"
    assert len(quests[0].labors) == 2


def test_creation_without_target(sample_data1):
    hosts = [
        sample_data1.query(Host).filter(
            Host.hostname == 'example.dropbox.com'
        ).one(),
        sample_data1.query(Host).filter(
            Host.hostname == 'test.dropbox.com'
        ).one(),
    ]

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 0

    creation_event_type = (
        sample_data1.query(EventType)
        .filter(EventType.id == 1).first()
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
    assert quests[0].target_time is None
    assert len(quests[0].labors) == 2

    labors = Labor.get_open_unacknowledged(sample_data1)
    assert len(labors) == 2


def test_mass_creation(sample_data1):
    hosts = [
        sample_data1.query(Host).filter(
            Host.hostname == 'example.dropbox.com'
        ).one(),
        sample_data1.query(Host).filter(
            Host.hostname == 'test.dropbox.com'
        ).one(),
    ]

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 0

    creation_event_type1 = (
        sample_data1.query(EventType)
        .filter(EventType.id == 1).first()
    )

    target_time1 = datetime.now() + timedelta(days=7)
    target_time2 = datetime.now() + timedelta(days=10)
    target_time3 = datetime.now() + timedelta(days=14)

    Quest.create(
        sample_data1, "testman", hosts, creation_event_type1, target_time1,
        description="Embark on the long road of maintenance"
    )
    Quest.create(
        sample_data1, "testman", hosts, creation_event_type1, target_time2,
        description="Embark on the longer road of maintenance"
    )
    Quest.create(
        sample_data1, "testman", hosts, creation_event_type1, target_time3,
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
    assert len(quests[0].labors) == 2
    assert len(quests[1].labors) == 2
    assert len(quests[2].labors) == 2

    labors = Labor.get_open_unacknowledged(sample_data1)
    assert len(labors) == 6

    # now we want to test the closing of the quest by throwing events
    # that fulfill the labors

    found_hosts = sample_data1.query(Host).filter(
        Host.hostname.in_(["example.dropbox.com", "test.dropbox.com"])
    ).all()

    assert len(found_hosts) == 2

    completion_event_type1 = (
        sample_data1.query(EventType)
        .filter(EventType.id == 2).first()
    )

    Event.create(
        sample_data1, found_hosts[0], "testdude", completion_event_type1
    )
    Event.create(
        sample_data1, found_hosts[1], "testdude", completion_event_type1
    )

    labors = Labor.get_open_unacknowledged(sample_data1)
    assert len(labors) == 0

    quests = sample_data1.query(Quest).all()

    assert len(quests) == 3
    assert quests[0].embark_time is not None
    assert quests[0].completion_time is not None
    assert quests[1].embark_time is not None
    assert quests[1].completion_time is not None
    assert quests[2].embark_time is not None
    assert quests[2].completion_time is not None
    assert quests[0].description == "Embark on the long road of maintenance"
    assert quests[0].creator == "testman"
    assert len(quests[0].labors) == 2


def test_quest_preservation(sample_data1):
    """When a quest has labors that chain together, make sure they stay
    attached to the quest.
    """
    hosts = [
        sample_data1.query(Host).filter(
            Host.hostname == 'example.dropbox.com'
        ).one(),
        sample_data1.query(Host).filter(
            Host.hostname == 'test.dropbox.com'
        ).one(),
    ]

    labors = sample_data1.query(Labor).all()
    assert len(labors) == 0

    creation_event_type = (
        sample_data1.query(EventType)
        .filter(EventType.id == 3).first()
    )

    target_time = datetime.now() + timedelta(days=2)

    Quest.create(
        sample_data1, "testman", hosts, creation_event_type, target_time,
        description="Embark on the long road of maintenance"
    )

    quests = sample_data1.query(Quest).all()

    assert len(quests) == 1
    assert quests[0].embark_time is not None
    assert quests[0].completion_time is None
    assert quests[0].description == "Embark on the long road of maintenance"
    assert quests[0].creator == "testman"
    assert len(quests[0].labors) == 2

    labors = Labor.get_open_unacknowledged(sample_data1)
    assert len(labors) == 2

    # now we want to throw events that create the subsequent labors
    found_hosts = sample_data1.query(Host).filter(
        Host.hostname.in_(["example.dropbox.com", "test.dropbox.com"])
    ).all()
    assert len(found_hosts) == 2

    completion_event_type1 = sample_data1.query(EventType).get(4)

    Event.create(
        sample_data1, found_hosts[0], "testdude", completion_event_type1
    )
    Event.create(
        sample_data1, found_hosts[1], "testdude", completion_event_type1
    )

    assert len(quests[0].labors) == 4
    assert len(quests[0].get_open_labors().all()) == 2


def test_complex_chaining1(sample_data2):
    """This test works on testing some complex chainging fates:

    ET: sys-audit, sys-needed, sys-ready, sys-complete, reboot-needed, reboot-complete, puppet-restart

    Fates:
    sys-audit => sys-needed
    sys-needed => sys-ready
    sys-ready => sys-complete
    sys-needed => reboot-complete
    reboot-needed => reboot-complete
    reboot-complete => puppet-restart

    Quests:
    Alpha: servers need sys-audit; on sys-needed event, add only 1 labor for sys-needed and add to quest
    """
    event_types = sample_data2.query(EventType).all()
    assert len(event_types) == 7

    fates = sample_data2.query(Fate).all()
    assert len(fates) == 8

    hosts = [
        sample_data2.query(Host).filter(
            Host.hostname == 'example.dropbox.com'
        ).one(),
        sample_data2.query(Host).filter(
            Host.hostname == 'test.dropbox.com'
        ).one(),
    ]

    target_time = datetime.now() + timedelta(days=2)

    quest = Quest.create(
        sample_data2, "testman", hosts,
        EventType.get_event_type(sample_data2, "system-maintenance", "audit"),
        target_time,
        description="Servers need audit"
    )

    assert quest
    assert len(quest.get_open_labors().all()) == 2

    # now we fire the system-maintenance needed event
    found_hosts = sample_data2.query(Host).filter(
        Host.hostname.in_(["example.dropbox.com", "test.dropbox.com"])
    ).all()
    assert len(found_hosts) == 2
    event1 = Event.create(
        sample_data2, found_hosts[0], "system",
        EventType.get_event_type(sample_data2, "system-maintenance", "needed")
    )
    event2 = Event.create(
        sample_data2, found_hosts[1], "system",
        EventType.get_event_type(sample_data2, "system-maintenance", "needed")
    )

    assert len(quest.labors) == 4
    assert len(quest.get_open_labors().all()) == 2
    assert quest.completion_time is None

    labor1 = quest.get_open_labors().all()[0]
    labor2 = quest.get_open_labors().all()[1]

    assert labor1.host == hosts[0]
    assert labor2.host == hosts[1]
    # True b/c of Fate #2
    assert labor1.for_owner is True
    # True b/c of Fate #4
    assert labor1.for_creator is True
    # True b/c of Fate #2
    assert labor2.for_owner is True
    # True b/c of Fate #4
    assert labor2.for_creator is True
    assert labor1.creation_event == event1
    assert labor2.creation_event == event2


def test_complex_chaining2(sample_data2):
    """This test works on testing some complex chaining of fates:

    ET: sys-audit, sys-needed, sys-ready, sys-complete, reboot-needed,
        reboot-complete, puppet-restart

    Fates:
    system-maintenance-audit => system-maintenance-needed
        => system-maintenance-ready => system-maintenance-completed

    system-maintenance-audit => system-maintenance-needed
        => system-reboot-completed

    system-reboot-needed => system-reboot-completed => puppet-restart

    Quests:
    Bravo: servers need sys-needed
    Charlie: servers need reboot-needed

    We test that one event will complete bravo quest while progressing charlie quest
    """
    event_types = sample_data2.query(EventType).all()
    assert len(event_types) == 7

    fates = sample_data2.query(Fate).all()
    assert len(fates) == 8

    hosts = [sample_data2.query(Host).get(1)]

    target_time1 = datetime.now() + timedelta(days=2)
    target_time2 = datetime.now() + timedelta(days=7)

    print "\nbravo quest"
    bravo_quest = Quest.create(
        sample_data2, "testman", hosts,
        EventType.get_event_type(sample_data2, "system-maintenance", "audit"),
        target_time1,
        description="System maintenance is needed"
    )

    print "\ncharlie quest"
    charlie_quest = Quest.create(
        sample_data2, "testman", hosts,
        EventType.get_event_type(sample_data2, "system-reboot", "needed"),
        target_time2,
        description="Systems need a reboot"
    )
    assert bravo_quest
    assert charlie_quest
    assert len(bravo_quest.labors) == 1
    assert len(charlie_quest.labors) == 1
    assert bravo_quest.completion_time is None
    assert charlie_quest.completion_time is None

    assert len(hosts[0].events) == 2

    # Now we want to progress the bravo quest by throwing the sys-maint needed event
    print "\nevent 1"
    event1 = Event.create(
        sample_data2, hosts[0], "system",
        EventType.get_event_type(sample_data2, "system-maintenance", "needed")
    )
    assert len(bravo_quest.get_open_labors().all()) == 1
    assert bravo_quest.get_open_labors().all()[0].creation_event == event1
    assert bravo_quest.get_open_labors().all()[0].starting_labor_id == hosts[0].events[0].id
    assert len(bravo_quest.labors) == 2

    # Now we progress the charlie quest and complete the bravo quest with
    # the system-reboot-completed event
    print "\nevent 2"
    event2 = Event.create(
        sample_data2, hosts[0], "system",
        EventType.get_event_type(sample_data2, "system-reboot", "completed")
    )
    assert bravo_quest.completion_time is not None
    assert len(bravo_quest.labors) == 2
    assert charlie_quest.get_open_labors().all()[0].creation_event == event2
    assert charlie_quest.get_open_labors().all()[0].starting_labor_id == hosts[0].events[1].id
    assert charlie_quest.completion_time is None
    assert len(charlie_quest.labors) == 2

    # since the previous event progressed the workflow, this one below
    # shouldn't create a labor since system-reboot-completed labors are
    # intermediates
    print "\nevent 3"
    event3 = Event.create(
        sample_data2, hosts[0], "system",
        EventType.get_event_type(sample_data2, "system-reboot", "completed")
    )

    # we will have a 5th event here due to event3
    assert len(hosts[0].events) == 5

    assert len(charlie_quest.labors) == 2
    assert len(charlie_quest.get_open_labors().all()) == 1

    assert charlie_quest.get_open_labors().all()[0].creation_event == event2
    assert charlie_quest.get_open_labors().all()[0].quest == charlie_quest

    assert len(sample_data2.query(Labor).all()) == 4


def test_complex_chaining3(sample_data2):
    """This test works on testing some complex chaining of fates:

    ET: sys-audit, sys-needed, sys-ready, sys-complete, reboot-needed,
        reboot-complete, puppet-restart

    Fates:
    system-maintenance-audit => system-maintenance-needed
        => system-maintenance-ready => system-maintenance-completed

    system-maintenance-audit => system-maintenance-needed
        => system-reboot-completed

    system-reboot-needed => system-reboot-completed => puppet-restart

    Quests:
    Bravo: servers need sys-needed
    Charlie: servers need reboot-needed
    """
    event_types = sample_data2.query(EventType).all()
    assert len(event_types) == 7

    fates = sample_data2.query(Fate).all()
    assert len(fates) == 8

    hosts = [sample_data2.query(Host).get(1)]

    target_time1 = datetime.now() + timedelta(days=2)
    target_time2 = datetime.now() + timedelta(days=7)

    print "\nbravo quest"
    bravo_quest = Quest.create(
        sample_data2, "testman", hosts,
        EventType.get_event_type(sample_data2, "system-maintenance", "audit"),
        target_time1,
        description="System maintenance is needed"
    )

    print "\ncharlie quest"
    charlie_quest = Quest.create(
        sample_data2, "testman", hosts,
        EventType.get_event_type(sample_data2, "system-reboot", "needed"),
        target_time2,
        description="Systems need a reboot"
    )
    assert bravo_quest
    assert charlie_quest
    assert len(bravo_quest.labors) == 1
    assert bravo_quest.get_open_labors().all()[0].for_owner is True
    assert bravo_quest.get_open_labors().all()[0].for_creator is False
    assert len(charlie_quest.labors) == 1
    assert bravo_quest.completion_time is None
    assert charlie_quest.completion_time is None

    assert len(hosts[0].events) == 2

    # Now we want to progress the bravo quest by throwing the sys-maint needed event
    print "\nevent 1"
    event1 = Event.create(
        sample_data2, hosts[0], "system",
        EventType.get_event_type(sample_data2, "system-maintenance", "needed")
    )
    assert bravo_quest.get_open_labors().all()[0].creation_event == event1
    assert bravo_quest.get_open_labors().all()[0].starting_labor_id == hosts[0].events[0].id
    # True b/c of Fate #2
    assert bravo_quest.get_open_labors().all()[0].for_owner is True
    # True b/c of Fate #4
    assert bravo_quest.get_open_labors().all()[0].for_creator is True
    assert len(bravo_quest.labors) == 2

    # Now we progress the bravo quest again by throwing sys-maint-ready
    print "\nevent 1b"
    event1b = Event.create(
        sample_data2, hosts[0], "system",
        EventType.get_event_type(sample_data2, "system-maintenance", "ready")
    )
    assert bravo_quest.get_open_labors().all()[0].creation_event == event1b
    assert bravo_quest.get_open_labors().all()[0].starting_labor_id == hosts[0].events[0].id
    assert bravo_quest.get_open_labors().all()[0].for_owner is True
    assert bravo_quest.get_open_labors().all()[0].for_creator is False
    assert len(bravo_quest.labors) == 3

    # Now we progress the charlie quest with the system-reboot-completed event
    # but bravo quest stays put
    print "\nevent 2"
    event2 = Event.create(
        sample_data2, hosts[0], "system",
        EventType.get_event_type(sample_data2, "system-reboot", "completed")
    )
    assert bravo_quest.completion_time is None
    assert len(bravo_quest.labors) == 3
    assert charlie_quest.get_open_labors().all()[0].creation_event == event2
    assert charlie_quest.get_open_labors().all()[0].starting_labor_id == hosts[0].events[1].id
    assert charlie_quest.completion_time is None
    assert len(charlie_quest.labors) == 2

    # since the previous event progressed the workflow, this one below
    # shouldn't create a labor since system-reboot-completed labors are
    # intermediates
    print "\nevent 3"
    event3 = Event.create(
        sample_data2, hosts[0], "system",
        EventType.get_event_type(sample_data2, "system-reboot", "completed")
    )

    # we will have a 6th event here due to event3
    assert len(hosts[0].events) == 6

    assert len(charlie_quest.labors) == 2
    assert len(charlie_quest.get_open_labors().all()) == 1

    assert charlie_quest.get_open_labors().all()[0].creation_event == event2
    assert charlie_quest.get_open_labors().all()[0].quest == charlie_quest

    assert len(sample_data2.query(Labor).all()) == 5




