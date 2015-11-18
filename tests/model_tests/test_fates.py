import pytest
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes.models import Fate, EventType

from .fixtures import db_engine, session, sample_data1


def test_creation(sample_data1):
    event_types = sample_data1.query(EventType).all()
    fates = sample_data1.query(Fate).all()
    assert len(event_types) == 7
    assert len(fates) == 6

    event_type6 = event_types[5]
    event_type7 = event_types[6]

    Fate.create(
        sample_data1, event_type6, description="New fate"
    )
    Fate.create(
        sample_data1, event_type7, follows_id=7, description="New fate"
    )
    sample_data1.commit()

    fates = sample_data1.query(Fate).all()

    # the total number of fates should be 8 now.  We care about the new one
    assert len(fates) == 8
    fate = fates[6]
    assert fate.id == 7
    assert fate.creation_event_type == event_type6
    assert fate.description == "New fate"
    assert fate.for_creator is False
    assert fate.for_owner is True

    assert len(event_type6.auto_creates) == 1
    assert event_type6.auto_creates[0] == fate

    assert len(event_type7.auto_creates) == 1
    assert event_type7.auto_creates[0] == fates[7]


def test_creation2(sample_data1):
    event_types = sample_data1.query(EventType).all()
    fates = sample_data1.query(Fate).all()
    assert len(event_types) == 7
    assert len(fates) == 6

    event_type6 = event_types[5]
    event_type7 = event_types[6]

    Fate.create(
        sample_data1, event_type6, for_creator=True,
        for_owner=False, description="New fate"
    )
    Fate.create(
        sample_data1, event_type7, follows_id=7, description="New fate"
    )
    sample_data1.commit()

    fates = sample_data1.query(Fate).all()

    # the total number of fates should be 8 now.  We care about the new one
    assert len(fates) == 8
    fate = fates[6]
    assert fate.id == 7
    assert fate.creation_event_type == event_type6
    assert fate.description == "New fate"
    assert fate.for_creator is True
    assert fate.for_owner is False

    assert len(event_type6.auto_creates) == 1
    assert event_type6.auto_creates[0] == fate

    assert len(event_type7.auto_creates) == 1
    assert event_type7.auto_creates[0] == fates[7]


def test_designation_constraint(sample_data1):
    """Fates must be set to for_owner or for_creator or both"""

    event_type1 = sample_data1.query(EventType).get(1)

    with pytest.raises(exc.ValidationError):
        Fate.create(
            sample_data1, event_type1, description="Wrong fate",
            for_creator=False, for_owner=False, follows_id=2
        )


def test_follows_id_valid(sample_data1):
    event_type1 = sample_data1.query(EventType).get(1)

    # There is no Fate 20
    with pytest.raises(exc.ValidationError):
        Fate.create(
            sample_data1, event_type1, description="Coolio",
            follows_id=20
        )