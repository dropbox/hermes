import pytest
from sqlalchemy.exc import IntegrityError

from hermes import exc
from hermes import models

from .fixtures import db_engine, session, sample_data1


def test_creation(session, sample_data1):
    event_types = session.query(models.EventType).all()
    assert len(event_types) == 4

    event_type1 = event_types[2]
    event_type2 = event_types[3]

    models.Fate.create(session, event_type1, event_type2, "New fate")
    session.commit()

    fates = session.query(models.Fate).all()

    # the total number of fates should be 2 now.  We care about the new one
    assert len(fates) == 2
    fate = fates[1]
    assert fate.id == 2
    assert fate.creation_event_type == event_type1
    assert fate.completion_event_type == event_type2
    assert fate.description == "New fate"


def test_duplicate(session, sample_data1):
    event_types = session.query(models.EventType).all()
    assert len(event_types) == 4

    event_type1 = event_types[0]
    event_type2 = event_types[1]

    with pytest.raises(IntegrityError):
        models.Fate.create(session, event_type1, event_type2, "Dup fate")