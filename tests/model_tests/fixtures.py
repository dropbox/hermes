import pytest

from hermes import models

@pytest.fixture
def db_engine(tmpdir):
    db_path = tmpdir.join("hermes.sqlite")
    db_engine = models.get_db_engine("sqlite:///%s" % db_path)

    return db_engine

@pytest.fixture
def session(db_engine, request, tmpdir):
    models.Model.metadata.drop_all(db_engine)
    models.Model.metadata.create_all(db_engine)
    models.Session.configure(bind=db_engine)
    session = models.Session()

    models.Fate._all_fates = None

    def fin():
        session.close()
    request.addfinalizer(fin)

    return session

@pytest.fixture
def sample_data1(session):
    sql_file = open('tests/sample_data/sample_data1.sql')
    sql = sql_file.read()
    for statement in sql.split(";"):
        session.execute(statement)

    return session

@pytest.fixture
def sample_data2(session):
    sql_file = open('tests/sample_data/sample_data2.sql')
    sql = sql_file.read()
    for statement in sql.split(";"):
        session.execute(statement)

    return session