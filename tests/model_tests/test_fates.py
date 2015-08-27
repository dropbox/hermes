import pytest
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes.models import Fate, EventType

from .fixtures import db_engine, session, sample_data1


def test_creation(sample_data1):
    event_types = sample_data1.query(EventType).all()
    assert len(event_types) == 7

    event_type6 = event_types[5]
    event_type7 = event_types[6]

    Fate.create(
        sample_data1, event_type6, event_type7, description="New fate"
    )
    sample_data1.commit()

    fates = sample_data1.query(Fate).all()

    # the total number of fates should be 5 now.  We care about the new one
    assert len(fates) == 5
    fate = fates[4]
    assert fate.id == 5
    assert fate.creation_event_type == event_type6
    assert fate.completion_event_type == event_type7
    assert fate.description == "New fate"

    assert len(event_type6.auto_creates) == 1
    assert event_type6.auto_creates[0] == fate
    assert len(event_type6.auto_completes) == 0

    assert len(event_type7.auto_creates) == 0
    assert len(event_type7.auto_completes) == 1
    assert event_type7.auto_completes[0] == fate


def test_duplicate(sample_data1):
    event_type4 = sample_data1.query(EventType).get(4)
    event_type5 = sample_data1.query(EventType).get(5)

    with pytest.raises(IntegrityError):
        Fate.create(
            sample_data1, event_type4, event_type5, description="Dup fate",
            follows_id=2
        )


def test_uniqueness_by_follows_id(sample_data1):
    """We should be able to create a fate with the same event_types if the
    follows_id is unique"""

    event_type4 = sample_data1.query(EventType).get(4)
    event_type5 = sample_data1.query(EventType).get(5)

    fate = Fate.create(
        sample_data1, event_type4, event_type5, description="Unique fate",
        follows_id=None
    )


def test_follows_id_constraint(sample_data1):
    """When specifying that a Fate follows another Fate, make sure the
    completing EventType for the preceding Fate matches the creation EventType
    forthe following Fate.
    """

    event_type1 = sample_data1.query(EventType).get(1)
    event_type5 = sample_data1.query(EventType).get(5)

    with pytest.raises(exc.ValidationError):
        Fate.create(
            sample_data1, event_type1, event_type5, description="Wrong fate",
            follows_id=2
        )

def test_follows_id_valid(sample_data1):
    event_type1 = sample_data1.query(EventType).get(1)
    event_type5 = sample_data1.query(EventType).get(5)

    # There is no Fate 20
    with pytest.raises(exc.ValidationError):
        Fate.create(
            sample_data1, event_type1, event_type5, description="Coolio",
            follows_id=20
        )