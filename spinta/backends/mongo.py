import contextlib
import copy

import pymongo
from bson.objectid import ObjectId

from spinta.backends import Backend
from spinta.commands import load, prepare, migrate, check, push, get, getall, wipe, wait
from spinta.components import Context, Manifest, Model
from spinta.config import Config


class Mongo(Backend):
    # Instance of this class will be created when application starts. First if
    # will be loaded from configuration using `load` command, then it will be
    # prepared from manifest declarations using `prepare` command.
    #
    # Backend also must have a `transaction` method which must return read or
    # write transaction object containing an active `connection` to database.
    metadata = {
        'name': 'mongo',
        'properties': {
            'dsn': {'type': 'string', 'required': True},
            'db': {'type': 'string', 'required': True},
        },
    }

    @contextlib.contextmanager
    def transaction(self, write=False):
        with self.engine.begin() as connection:
            if write:
                # TODO: get a real transaction id
                transaction_id = 1
                yield WriteTransaction(connection, transaction_id)
            else:
                yield ReadTransaction(connection)


class ReadTransaction:

    def __init__(self, connection):
        self.connection = connection


class WriteTransaction(ReadTransaction):

    def __init__(self, connection, id):
        super().__init__(connection)
        self.id = id
        self.errors = 0


@load.register()
def load(context: Context, backend: Mongo, config: Config):
    # Load Mongo client using configuration.
    backend.dsn = config.get('backends', backend.name, 'dsn', required=True)
    backend.db = config.get('backends', backend.name, 'db', required=True)

    backend.client = pymongo.MongoClient(backend.dsn)
    backend.db = backend.client[backend.db]


@wait.register()
def wait(context: Context, backend: Mongo, config: Config, *, fail: bool = False):
    return True


@prepare.register()
def prepare(context: Context, backend: Mongo, manifest: Manifest):
    # Mongo does not need any table or database preparations
    pass


@migrate.register()
def migrate(context: Context, backend: Mongo):
    # Migrate schema changes.
    pass


@check.register()
def check(context: Context, model: Model, backend: Mongo, data: dict):
    # Check data before insert/update.
    transaction = context.get('transaction')


@push.register()
def push(context: Context, model: Model, backend: Mongo, data: dict):
    # Push data to Mongo backend, this can be an insert, update or delete. If
    # `id` is not given, it is an insert if `id` is given, it is an update.
    #
    # Deletes are not yet implemented, but for deletes `data` must equal to
    # `{'id': 1, _delete: True}`.
    #
    # Also this must return inserted/updated/deleted id.
    #
    # Also this command must write information to changelog after change is
    # done.
    transaction = context.get('transaction')
    model_collection = backend.db[model.get_type_value()]

    # Make a copy of data, because `pymongo` changes the reference `data`
    # object on `insert_one()` call.
    #
    # We want to have our data intact from whatever specific mongo metadata
    # MongoDB may add to our object.
    raw_data = copy.deepcopy(data)

    if 'id' in data:
        result = model_collection.update_one(
            {'_id': raw_data['id']},
            {'$set': raw_data}
        )
        assert result.matched_count == 1 and result.modified_count == 1
        data_id = data['id']
    else:
        data_id = model_collection.insert_one(raw_data).inserted_id
    return data_id


@get.register()
def get(context: Context, model: Model, backend: Mongo, id: ObjectId):
    transaction = context.get('transaction')
    model_collection = backend.db[model.get_type_value()]
    result = model_collection.find_one({"_id": id})

    # Mongo returns ID under, key `_id`, but to conform to the interface
    # we must change `_id` to `id`
    #
    # TODO: this must be fixed/implemented in the spinta/types/store.py::get()
    # just like it's done on spinta/types/store.py::push()
    result['id'] = result.pop('_id')
    return result


@getall.register()
def getall(context: Context, model: Model, backend: Mongo):
    transaction = context.get('transaction')
    # Yield all available entries.
    model_collection = backend.db[model.get_type_value()]
    return model_collection.find({})


@wipe.register()
def wipe(context: Context, model: Model, backend: Mongo):
    transaction = context.get('transaction')
    # Delete all data for a given model
    model_collection = backend.db[model.get_type_value()]
    return model_collection.delete_many({})
