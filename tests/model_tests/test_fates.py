import pytest
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes import models

from .fixtures import db_engine, session, sample_data1


def test_creation(sample_data1):
    event_types = sample_data1.query(models.EventType).all()
    assert len(event_types) == 6

    event_type4 = event_types[4]
    event_type5 = event_types[5]

    models.Fate.create(sample_data1, event_type4, event_type5, "New fate")
    sample_data1.commit()

    fates = sample_data1.query(models.Fate).all()

    # the total number of fates should be 3 now.  We care about the new one
    assert len(fates) == 3
    fate = fates[2]
    assert fate.id == 3
    assert fate.creation_event_type == event_type4
    assert fate.completion_event_type == event_type5
    assert fate.description == "New fate"


def test_duplicate(sample_data1):
    event_types = sample_data1.query(models.EventType).all()
    assert len(event_types) == 6

    event_type1 = event_types[0]
    event_type2 = event_types[1]

    with pytest.raises(IntegrityError):
        models.Fate.create(sample_data1, event_type1, event_type2, "Dup fate")