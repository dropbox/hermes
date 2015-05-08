import pytest

from hermes import models

@pytest.fixture
def session(request, tmpdir):
    db_path = tmpdir.join("hermes.sqlite")
    db_engine = models.get_db_engine("sqlite:///%s" % db_path)

    models.Model.metadata.drop_all(db_engine)
    models.Model.metadata.create_all(db_engine)
    models.Session.configure(bind=db_engine)
    session = models.Session()

    def fin():
        session.close()
    request.addfinalizer(fin)

    return session