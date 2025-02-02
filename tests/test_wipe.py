from typing import List
from typing import Tuple

import pytest

from spinta.testing.client import TestClient
from spinta.testing.data import listdata
from spinta.testing.utils import get_error_codes
from spinta.utils.schema import NA


def _excluding(
    name: str,
    value: str,
    data: List[Tuple[str, str]],
) -> List[Tuple[str, str]]:
    return [
        (_type, status)
        for _type, status in data
        if not (_type == name and status == value)
    ]


def test_wipe_all(app):
    app.authorize(['spinta_insert', 'spinta_getall', 'spinta_wipe'])

    # Create some data in different models
    resp = app.post('/', json={'_data': [
        {'_op': 'insert', '_type': 'report', 'status': 'ok'},
        {'_op': 'insert', '_type': 'backends/mongo/report', 'status': 'ok'},
        {'_op': 'insert', '_type': 'backends/postgres/report', 'status': 'ok'},
    ]})
    assert resp.status_code == 200, resp.json()

    # Get data from all models
    resp = app.get('/:all')
    data = sorted([(r['_type'], r.get('status')) for r in resp.json()['_data']])
    assert listdata(resp, '_type', 'status') == [
        ('_txn', NA),
        ('backends/mongo/report', 'ok'),
        ('backends/postgres/report', 'ok'),
        ('report', 'ok'),
    ]

    # Wipe all data
    resp = app.delete('/:wipe')
    assert resp.status_code == 200, resp.json()

    # Check what data again
    resp = app.get('/:all')
    assert resp.status_code == 200, resp.json()
    assert len(resp.json()['_data']) == 0


@pytest.mark.models(
    'backends/mongo/report',
    'backends/postgres/report',
)
def test_wipe_model(model, app):
    app.authorize(['spinta_insert', 'spinta_getall', 'spinta_wipe'])

    # Create some data in different models
    resp = app.post('/', json={'_data': [
        {'_op': 'insert', '_type': 'report', 'status': 'ok'},
        {'_op': 'insert', '_type': 'backends/mongo/report', 'status': 'ok'},
        {'_op': 'insert', '_type': 'backends/postgres/report', 'status': 'ok'},
    ]})
    assert resp.status_code == 200, resp.json()

    # Get data from all models
    resp = app.get('/:all')
    assert listdata(resp, '_type', 'status') == [
        ('_txn', NA),
        ('backends/mongo/report', 'ok'),
        ('backends/postgres/report', 'ok'),
        ('report', 'ok'),
    ]

    # Wipe model data
    resp = app.delete(f'/{model}/:wipe')
    assert resp.status_code == 200, resp.json()
    resp = app.delete(f'/_txn/:wipe')
    assert resp.status_code == 200, resp.json()

    # Check the data again
    resp = app.get('/:all')
    assert listdata(resp, '_type', 'status') == _excluding(model, 'ok', [
        ('backends/mongo/report', 'ok'),
        ('backends/postgres/report', 'ok'),
        ('report', 'ok'),
    ])


@pytest.mark.models(
    'backends/mongo/report',
    'backends/postgres/report',
)
def test_wipe_row(model: str, app: TestClient):
    app.authorize(['spinta_insert', 'spinta_getall', 'spinta_wipe'])

    # Create some data in different models
    resp = app.post('/', json={'_data': [
        {'_op': 'insert', '_type': 'report', 'status': 'ok'},
        {'_op': 'insert', '_type': 'backends/mongo/report', 'status': 'ok'},
        {'_op': 'insert', '_type': 'backends/mongo/report', 'status': 'nb'},
        {'_op': 'insert', '_type': 'backends/postgres/report', 'status': 'ok'},
        {'_op': 'insert', '_type': 'backends/postgres/report', 'status': 'nb'},
    ]})
    _id_idx = {
        'backends/mongo/report': 1,
        'backends/postgres/report': 3,
    }
    _id = listdata(resp, '_id')[_id_idx[model]]

    # Get data from all models
    resp = app.get('/:all')
    assert listdata(resp, '_type', 'status') == [
        ('_txn', NA),
        ('backends/mongo/report', 'nb'),
        ('backends/mongo/report', 'ok'),
        ('backends/postgres/report', 'nb'),
        ('backends/postgres/report', 'ok'),
        ('report', 'ok'),
    ]

    # Wipe model row data
    with pytest.raises(NotImplementedError):
        resp = app.delete(f'/{model}/{_id}/:wipe')
    assert resp.status_code == 200, resp.json()
    resp = app.delete(f'/_txn/:wipe')
    assert resp.status_code == 200, resp.json()

    # Check the data again.
    resp = app.get('/:all')
    assert listdata(resp, '_type', 'status') == [
        ('backends/mongo/report', 'nb'),
        ('backends/mongo/report', 'ok'),
        ('backends/postgres/report', 'nb'),
        ('backends/postgres/report', 'ok'),
        ('report', 'ok'),
    ]


@pytest.mark.models(
    'backends/mongo/report',
    'backends/postgres/report',
)
def test_wipe_check_scope(model, app):
    app.authorize(['spinta_insert', 'spinta_getall', 'spinta_delete'])
    resp = app.delete(f'/{model}/:wipe')
    assert resp.status_code == 403


def test_wipe_check_ns_scope(app):
    app.authorize(['spinta_insert', 'spinta_getall', 'spinta_delete'])
    resp = app.delete(f'/:wipe')
    assert resp.status_code == 403


@pytest.mark.models(
    'backends/mongo/report',
    'backends/postgres/report',
)
def test_wipe_in_batch(model, app):
    app.authorize(['spinta_wipe'])
    resp = app.post(f'/', json={
        '_data': [
            {'_op': 'wipe', '_type': model}
        ]
    })
    assert resp.status_code == 400
    assert get_error_codes(resp.json()) == ['UnknownAction']


def test_wipe_all_access(app: TestClient):
    app.authorize(['spinta_insert', 'spinta_getall', 'spinta_delete'])

    # Create some data in different models.
    resp = app.post('/', json={'_data': [
        {'_op': 'insert', '_type': 'report', 'status': 'ok'},
        {'_op': 'insert', '_type': 'backends/mongo/report', 'status': 'ok'},
        {'_op': 'insert', '_type': 'backends/postgres/report', 'status': 'ok'},
    ]})
    assert resp.status_code == 200, resp.json()

    # Get data from all models.
    resp = app.get('/:all')
    assert listdata(resp, '_type', 'status') == [
        ('_txn', NA),
        ('backends/mongo/report', 'ok'),
        ('backends/postgres/report', 'ok'),
        ('report', 'ok'),
    ]

    # Wipe all data
    resp = app.delete('/:wipe')
    assert resp.status_code == 403  # Forbidden

    # Check the data again.
    resp = app.get('/:all')
    assert listdata(resp, '_type', 'status') == [
        ('_txn', NA),
        ('backends/mongo/report', 'ok'),
        ('backends/postgres/report', 'ok'),
        ('report', 'ok'),
    ]


@pytest.mark.models(
    'backends/mongo/report',
    'backends/postgres/report',
)
def test_wipe_model_access(model, app):
    app.authorize(['spinta_insert', 'spinta_getall', 'spinta_delete'])

    # Create some data in different models
    resp = app.post('/', json={'_data': [
        {'_op': 'insert', '_type': 'report', 'status': 'ok'},
        {'_op': 'insert', '_type': 'backends/mongo/report', 'status': 'ok'},
        {'_op': 'insert', '_type': 'backends/postgres/report', 'status': 'ok'},
    ]})
    assert resp.status_code == 200, resp.json()

    # Get data from all models
    resp = app.get('/:all')
    assert listdata(resp, '_type', 'status') == [
        ('_txn', NA),
        ('backends/mongo/report', 'ok'),
        ('backends/postgres/report', 'ok'),
        ('report', 'ok'),
    ]

    # Wipe model data
    resp = app.delete(f'/{model}/:wipe')
    assert resp.status_code == 403, resp.json()

    # Check what data again
    resp = app.get('/:all')
    assert listdata(resp, '_type', 'status') == [
        ('_txn', NA),
        ('backends/mongo/report', 'ok'),
        ('backends/postgres/report', 'ok'),
        ('report', 'ok'),
    ]


@pytest.mark.models(
    'backends/mongo/report',
    'backends/postgres/report',
)
def test_wipe_row_access(model, app):
    app.authorize(['spinta_insert', 'spinta_getall', 'spinta_delete'])

    # Create some data in different models
    resp = app.post('/', json={'_data': [
        {'_op': 'insert', '_type': 'report', 'status': 'ok'},
        {'_op': 'insert', '_type': 'backends/mongo/report', 'status': 'ok'},
        {'_op': 'insert', '_type': 'backends/postgres/report', 'status': 'ok'},
    ]})
    ids = dict(listdata(resp, '_type', '_id'))
    _id = ids[model]

    # Get data from all models
    resp = app.get('/:all')
    assert listdata(resp, '_type', 'status') == [
        ('_txn', NA),
        ('backends/mongo/report', 'ok'),
        ('backends/postgres/report', 'ok'),
        ('report', 'ok'),
    ]

    # Wipe model row data
    with pytest.raises(NotImplementedError):
        resp = app.delete(f'/{model}/{_id}/:wipe')
        assert resp.status_code == 403, resp.json()

    # Check what data again
    resp = app.get('/:all')
    assert listdata(resp, '_type', 'status') == [
        ('_txn', NA),
        ('backends/mongo/report', 'ok'),
        ('backends/postgres/report', 'ok'),
        ('report', 'ok'),
    ]
