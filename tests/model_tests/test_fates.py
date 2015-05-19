import pytest
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes import models

from .fixtures import db_engine, session, sample_data1


def test_creation(sample_data1):
    event_types = sample_data1.query(models.EventType).all()
    assert len(event_types) == 7

    event_type6 = event_types[5]
    event_type7 = event_types[6]

    models.Fate.create(
        sample_data1, event_type6, event_type7, description="New fate"
    )
    sample_data1.commit()

    fates = sample_data1.query(models.Fate).all()

    # the total number of fates should be 4 now.  We care about the new one
    assert len(fates) == 4
    fate = fates[3]
    assert fate.id == 4
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
    event_types = sample_data1.query(models.EventType).all()
    assert len(event_types) == 7

    event_type1 = event_types[0]
    event_type2 = event_types[1]

    with pytest.raises(IntegrityError):
        models.Fate.create(
            sample_data1, event_type1, event_type2, description="Dup fate"
        )