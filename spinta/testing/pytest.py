import os

import pytest
import sqlalchemy_utils as su
from responses import RequestsMock
from click.testing import CliRunner

from spinta import api
from spinta.testing.context import ContextForTests
from spinta.testing.client import TestClient
from spinta.config import RawConfig
from spinta.utils.imports import importstr


@pytest.fixture(scope='session')
def config():
    config = RawConfig()
    config.read({
        'env': 'test',
    })
    return config


@pytest.fixture(scope='session')
def postgresql(config):
    dsn = config.get('backends', 'default', 'dsn', required=True)
    if su.database_exists(dsn):
        yield dsn
    else:
        su.create_database(dsn)
        yield dsn
        su.drop_database(dsn)


@pytest.fixture(scope='session')
def mongo(config):
    yield
    dsn = config.get('backends', 'mongo', 'dsn', required=False)
    db = config.get('backends', 'mongo', 'db', required=False)
    if dsn and db:
        import pymongo
        client = pymongo.MongoClient(dsn)
        client.drop_database(db)


@pytest.fixture
def context(mocker, tmpdir, config, postgresql, mongo):
    mocker.patch.dict(os.environ, {
        'AUTHLIB_INSECURE_TRANSPORT': '1',
        'SPINTA_BACKENDS_FS_PATH': str(tmpdir),
    })

    Context = config.get('components', 'core', 'context', cast=importstr)
    Context = type('ContextForTests', (ContextForTests, Context), {})
    context = Context()

    context.set('config.raw', config)

    yield context

    config.restore()
    if context.loaded:
        context.wipe_all()


@pytest.fixture
def responses():
    with RequestsMock() as mock:
        yield mock


@pytest.fixture
def app(context, mocker):
    mocker.patch('spinta.api.context', context)
    return TestClient(context, api.app)


@pytest.fixture
def cli(context):
    runner = CliRunner()
    runner.env.update({
        'SPINTA_ENV': 'test',
    })
    return runner
