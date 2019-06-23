import uuid
import datetime

import pytest

from spinta.utils.itertools import consume
from spinta.utils.refs import get_ref_id


def test_app(app):
    resp = app.get('/', headers={'accept': 'text/html'})
    assert resp.status_code == 200

    resp.context.pop('request')
    assert resp.context == {
        'location': [
            ('root', '/'),
        ],
        'items': [
            ('capital', '/capital'),
            ('continent', '/continent'),
            ('country', '/country'),
            ('deeply', '/deeply'),
            ('nested', '/nested'),
            ('org', '/org'),
            ('photo', '/photo'),
            # FIXME: /report should be /reports, because that is specified in
            #        'endpoint' option of report model.
            ('report', '/report'),
            ('rinkimai', '/rinkimai'),
            ('tenure', '/tenure'),
        ],
        'datasets': [],
        'header': [],
        'data': [],
        'row': [],
        'formats': [],
    }


def test_directory(app):
    resp = app.get('/rinkimai', headers={'accept': 'text/html'})
    assert resp.status_code == 200

    resp.context.pop('request')
    assert resp.context == {
        'location': [
            ('root', '/'),
            ('rinkimai', None),
        ],
        'items': [
            ('apygarda', '/rinkimai/apygarda'),
            ('apylinke', '/rinkimai/apylinke'),
            ('kandidatas', '/rinkimai/kandidatas'),
            ('turas', '/rinkimai/turas'),
        ],
        'datasets': [
            {'name': 'json/data', 'link': '/rinkimai/:dataset/json/:resource/data', 'canonical': False},
            {'name': 'xlsx/data', 'link': '/rinkimai/:dataset/xlsx/:resource/data', 'canonical': False},
        ],
        'header': [],
        'data': [],
        'row': [],
        'formats': [],
    }


def test_model(context, app):
    row, = context.push([
        {
            'type': 'country',
            'title': 'Earth',
            'code': 'er',
        },
    ])

    app.authorize(['spinta_country_getall'])
    resp = app.get('/country', headers={'accept': 'text/html'})
    assert resp.status_code == 200

    resp.context.pop('request')
    assert resp.context == {
        'location': [
            ('root', '/'),
            ('country', None),
            (':changes', '/country/:changes'),
        ],
        'items': [],
        'datasets': [
            {'canonical': False, 'link': '/country/:dataset/csv/:resource/countries', 'name': 'csv/countries'},
            {'canonical': False, 'link': '/country/:dataset/denorm/:resource/orgs', 'name': 'denorm/orgs'},
            {'canonical': False, 'link': '/country/:dataset/dependencies/:resource/continents', 'name': 'dependencies/continents'},
            {'canonical': False, 'link': '/country/:dataset/sql/:resource/db', 'name': 'sql/db'},
        ],
        'header': ['id', 'title', 'code', 'revision'],
        'data': [
            [
                {'color': None, 'link': '/country/%s' % row['id'], 'value': row['id'][:8]},
                {'color': None, 'link': None, 'value': 'Earth'},
                {'color': None, 'link': None, 'value': 'er'},
                # FIXME: revision should not be None
                {'color': '#C1C1C1', 'link': None, 'value': ''},
            ],
        ],
        'row': [],
        'formats': [
            ('CSV', '/country/:format/csv'),
            ('JSON', '/country/:format/json'),
            ('JSONL', '/country/:format/jsonl'),
            ('ASCII', '/country/:format/ascii'),
        ],
    }


def test_model_get(context, app):
    row, = context.push([
        {
            'type': 'country',
            'title': 'Earth',
            'code': 'er',
        },
    ])

    app.authorize(['spinta_country_getone'])
    resp = app.get('/country/%s' % row['id'], headers={'accept': 'text/html'})
    assert resp.status_code == 200

    resp.context.pop('request')
    assert resp.context == {
        'location': [
            ('root', '/'),
            ('country', '/country'),
            (row['id'][:8], None),
            (':changes', '/country/%s/:changes' % row['id']),
        ],
        'items': [],
        'datasets': [
            {'canonical': False, 'link': '/country/:dataset/csv/:resource/countries', 'name': 'csv/countries'},
            {'canonical': False, 'link': '/country/:dataset/denorm/:resource/orgs', 'name': 'denorm/orgs'},
            {'canonical': False, 'link': '/country/:dataset/dependencies/:resource/continents', 'name': 'dependencies/continents'},
            {'canonical': False, 'link': '/country/:dataset/sql/:resource/db', 'name': 'sql/db'},
        ],
        'header': [],
        'data': [],
        'row': [
            ('id', {'color': None, 'link': '/country/%s' % row['id'], 'value': row['id']}),
            ('title', {'color': None, 'link': None, 'value': 'Earth'}),
            ('code', {'color': None, 'link': None, 'value': 'er'}),
            ('type', {'color': None, 'link': None, 'value': 'country'}),
            # FIXME: revision should not be None
            ('revision', {'color': '#C1C1C1', 'link': None, 'value': ''}),
        ],
        'formats': [
            ('CSV', '/country/%s/:format/csv' % row['id']),
            ('JSON', '/country/%s/:format/json' % row['id']),
            ('JSONL', '/country/%s/:format/jsonl' % row['id']),
            ('ASCII', '/country/%s/:format/ascii' % row['id']),
        ],
    }


def test_dataset(context, app, mocker):
    mocker.patch('spinta.backends.postgresql.dataset.get_new_id', return_value='REVISION')

    context.push([
        {
            'type': 'rinkimai/:dataset/json/:resource/data',
            'id': get_ref_id('Rinkimai 1'),
            'pavadinimas': 'Rinkimai 1',
        },
    ])

    app.authorize(['spinta_rinkimai_dataset_json_resource_data_getall'])
    resp = app.get('/rinkimai/:dataset/json/:resource/data', headers={'accept': 'text/html'})
    assert resp.status_code == 200

    resp.context.pop('request')
    assert resp.context == {
        'location': [
            ('root', '/'),
            ('rinkimai', '/rinkimai'),
            (':dataset/json/:resource/data', None),
            (':changes', '/rinkimai/:dataset/json/:resource/data/:changes'),
        ],
        'items': [
            ('apygarda', '/rinkimai/apygarda'),
            ('apylinke', '/rinkimai/apylinke'),
            ('kandidatas', '/rinkimai/kandidatas'),
            ('turas', '/rinkimai/turas'),
        ],
        'datasets': [
            {'canonical': False, 'link': '/rinkimai/:dataset/json/:resource/data', 'name': 'json/data'},
            {'canonical': False, 'link': '/rinkimai/:dataset/xlsx/:resource/data', 'name': 'xlsx/data'},
        ],
        'header': ['id', 'pavadinimas', 'revision'],
        'data': [
            [
                {'color': None, 'link': '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data', 'value': 'df6b9e04'},
                {'color': None, 'link': None, 'value': 'Rinkimai 1'},
                {'color': None, 'link': None, 'value': 'REVISION'},
            ],
        ],
        'row': [],
        'formats': [
            ('CSV', '/rinkimai/:dataset/json/:resource/data/:format/csv'),
            ('JSON', '/rinkimai/:dataset/json/:resource/data/:format/json'),
            ('JSONL', '/rinkimai/:dataset/json/:resource/data/:format/jsonl'),
            ('ASCII', '/rinkimai/:dataset/json/:resource/data/:format/ascii'),
        ],
    }


def test_dataset_with_show(context, app, mocker):
    mocker.patch('spinta.backends.postgresql.dataset.get_new_id', return_value='REVISION')

    context.push([
        {
            'type': 'rinkimai/:dataset/json/:resource/data',
            'id': get_ref_id('Rinkimai 1'),
            'pavadinimas': 'Rinkimai 1',
        },
    ])

    app.authorize(['spinta_rinkimai_dataset_json_resource_data_search'])
    resp = app.get('/rinkimai/:dataset/json/:show/pavadinimas', headers={'accept': 'text/html'})
    assert resp.status_code == 200

    resp.context.pop('request')
    assert resp.context['header'] == ['pavadinimas']
    assert [tuple(y['value'] for y in x) for x in resp.context['data']] == [
        ('Rinkimai 1',),
    ]


def test_dataset_url_wihtout_resource(context, app, mocker):
    context.push([
        {
            'type': 'rinkimai/:dataset/json',
            'id': get_ref_id('Rinkimai 1'),
            'pavadinimas': 'Rinkimai 1',
        },
    ])

    app.authorize(['spinta_rinkimai_dataset_json_resource_data_getall'])
    resp = app.get('/rinkimai/:dataset/json', headers={'accept': 'text/html'})
    assert resp.status_code == 200


def test_nested_dataset(context, app, mocker):
    mocker.patch('spinta.backends.postgresql.dataset.get_new_id', return_value='REVISION')

    context.push([
        {
            'type': 'deeply/nested/model/name/:dataset/nested/dataset/name/:resource/resource',
            'id': get_ref_id('42'),
            'name': 'Nested One',
        },
    ])

    app.authorize(['spinta_deeply_nested_model_name_dataset_nest989f7f4d_getall'])
    resp = app.get('deeply/nested/model/name/:dataset/nested/dataset/name/:resource/resource', headers={'accept': 'text/html'})
    assert resp.status_code == 200

    resp.context.pop('request')
    assert resp.context == {
        'location': [
            ('root', '/'),
            ('deeply', '/deeply'),
            ('nested', '/deeply/nested'),
            ('model', '/deeply/nested/model'),
            ('name', '/deeply/nested/model/name'),
            (':dataset/nested/dataset/name/:resource/resource', None),
            (':changes', '/deeply/nested/model/name/:dataset/nested/dataset/name/:resource/resource/:changes'),
        ],
        'items': [],
        'datasets': [
            {
                'canonical': False,
                'link': '/deeply/nested/model/name/:dataset/nested/dataset/name/:resource/resource',
                'name': 'nested/dataset/name/resource',
            },
        ],
        'header': ['id', 'name', 'revision'],
        'data': [
            [
                {'color': None, 'link': '/deeply/nested/model/name/e2ff1ff0f7d663344abe821582b0908925e5b366/:dataset/nested/dataset/name/:resource/resource', 'value': 'e2ff1ff0'},
                {'color': None, 'link': None, 'value': 'Nested One'},
                {'color': None, 'link': None, 'value': 'REVISION'},
            ],
        ],
        'row': [],
        'formats': [
            ('CSV', '/deeply/nested/model/name/:dataset/nested/dataset/name/:resource/resource/:format/csv'),
            ('JSON', '/deeply/nested/model/name/:dataset/nested/dataset/name/:resource/resource/:format/json'),
            ('JSONL', '/deeply/nested/model/name/:dataset/nested/dataset/name/:resource/resource/:format/jsonl'),
            ('ASCII', '/deeply/nested/model/name/:dataset/nested/dataset/name/:resource/resource/:format/ascii'),
        ],
    }


def test_dataset_key(context, app, mocker):
    mocker.patch('spinta.backends.postgresql.dataset.get_new_id', return_value='REVISION')

    context.push([
        {
            'type': 'rinkimai/:dataset/json/:resource/data',
            'id': get_ref_id('Rinkimai 1'),
            'pavadinimas': 'Rinkimai 1',
        },
    ])

    app.authorize(['spinta_rinkimai_dataset_json_resource_data_getone'])
    resp = app.get('/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data', headers={'accept': 'text/html'})
    assert resp.status_code == 200

    resp.context.pop('request')
    assert resp.context == {
        'location': [
            ('root', '/'),
            ('rinkimai', '/rinkimai'),
            (':dataset/json/:resource/data', '/rinkimai/:dataset/json/:resource/data'),
            ('df6b9e04', None),
            (':changes', '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data/:changes'),
        ],
        'formats': [
            ('CSV', '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data/:format/csv'),
            ('JSON', '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data/:format/json'),
            ('JSONL', '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data/:format/jsonl'),
            ('ASCII', '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data/:format/ascii'),
        ],
        'datasets': [
            {'canonical': False, 'link': '/rinkimai/:dataset/json/:resource/data', 'name': 'json/data'},
            {'canonical': False, 'link': '/rinkimai/:dataset/xlsx/:resource/data', 'name': 'xlsx/data'},
        ],
        'items': [
            ('apygarda', '/rinkimai/apygarda'),
            ('apylinke', '/rinkimai/apylinke'),
            ('kandidatas', '/rinkimai/kandidatas'),
            ('turas', '/rinkimai/turas'),
        ],
        'header': [],
        'data': [],
        'row': [
            ('id', {
                'color': None,
                'link': '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data',
                'value': 'df6b9e04ac9e2467690bcad6d9fd673af6e1919b',
            }),
            ('pavadinimas', {'color': None, 'link': None, 'value': 'Rinkimai 1'}),
            ('type', {'color': None, 'link': None, 'value': 'rinkimai/:dataset/json/:resource/data'}),
            ('revision', {'color': None, 'link': None, 'value': 'REVISION'}),
        ],
    }


def test_changes_single_object(context, app, mocker):
    mocker.patch('spinta.backends.postgresql.dataset.utcnow', return_value=datetime.datetime(2019, 3, 6, 16, 15, 0, 816308))
    mocker.patch('spinta.backends.postgresql.dataset.get_new_id', return_value='REVISION')

    context.push([
        {
            'type': 'rinkimai/:dataset/json/:resource/data',
            'id': get_ref_id('Rinkimai 1'),
            'pavadinimas': 'Rinkimai 1',
        },
    ])
    context.push([
        {
            'type': 'rinkimai/:dataset/json/:resource/data',
            'id': get_ref_id('Rinkimai 1'),
            'pavadinimas': 'Rinkimai 2',
        },
    ])

    app.authorize(['spinta_rinkimai_dataset_json_resource_data_changes'])
    resp = app.get('/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data/:changes', headers={'accept': 'text/html'})
    assert resp.status_code == 200

    resp.context.pop('request')
    assert resp.context == {
        'location': [
            ('root', '/'),
            ('rinkimai', '/rinkimai'),
            (':dataset/json/:resource/data', '/rinkimai/:dataset/json/:resource/data'),
            ('df6b9e04', '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data'),
            (':changes', None),
        ],
        'formats': [
            ('CSV', '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data/:changes/:format/csv'),
            ('JSON', '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data/:changes/:format/json'),
            ('JSONL', '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data/:changes/:format/jsonl'),
            ('ASCII', '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data/:changes/:format/ascii'),
        ],
        'datasets': [
            {'canonical': False, 'link': '/rinkimai/:dataset/json/:resource/data', 'name': 'json/data'},
            {'canonical': False, 'link': '/rinkimai/:dataset/xlsx/:resource/data', 'name': 'xlsx/data'},
        ],
        'items': [
            ('apygarda', '/rinkimai/apygarda'),
            ('apylinke', '/rinkimai/apylinke'),
            ('kandidatas', '/rinkimai/kandidatas'),
            ('turas', '/rinkimai/turas'),
        ],
        'header': [
            'change_id',
            'transaction_id',
            'datetime',
            'action',
            'id',
            'pavadinimas',
        ],
        'data': [
            [
                {'color': None, 'link': None, 'value': resp.context['data'][0][0]['value']},
                {'color': None, 'link': None, 'value': resp.context['data'][0][1]['value']},
                {'color': None, 'link': None, 'value': '2019-03-06T16:15:00.816308'},
                {'color': None, 'link': None, 'value': 'patch'},
                {'color': None, 'link': '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data', 'value': 'df6b9e04'},
                {'color': '#B2E2AD', 'link': None, 'value': 'Rinkimai 2'},
            ],
            [
                {'color': None, 'link': None, 'value': resp.context['data'][1][0]['value']},
                {'color': None, 'link': None, 'value': resp.context['data'][1][1]['value']},
                {'color': None, 'link': None, 'value': '2019-03-06T16:15:00.816308'},
                {'color': None, 'link': None, 'value': 'insert'},
                {'color': None, 'link': '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data', 'value': 'df6b9e04'},
                {'color': '#B2E2AD', 'link': None, 'value': 'Rinkimai 1'},
            ],
        ],
        'row': [],
    }


def test_changes_object_list(context, app, mocker):
    mocker.patch('spinta.backends.postgresql.dataset.utcnow', return_value=datetime.datetime(2019, 3, 6, 16, 15, 0, 816308))
    mocker.patch('spinta.backends.postgresql.dataset.get_new_id', return_value='REVISION')

    context.push([
        {
            'type': 'rinkimai/:dataset/json/:resource/data',
            'id': get_ref_id('Rinkimai 1'),
            'pavadinimas': 'Rinkimai 1',
        },
    ])
    context.push([
        {
            'type': 'rinkimai/:dataset/json/:resource/data',
            'id': get_ref_id('Rinkimai 1'),
            'pavadinimas': 'Rinkimai 2',
        },
    ])

    app.authorize(['spinta_rinkimai_dataset_json_resource_data_changes'])
    resp = app.get('/rinkimai/:dataset/json/:resource/data/:changes', headers={'accept': 'text/html'})
    assert resp.status_code == 200

    resp.context.pop('request')
    assert resp.context == {
        'location': [
            ('root', '/'),
            ('rinkimai', '/rinkimai'),
            (':dataset/json/:resource/data', '/rinkimai/:dataset/json/:resource/data'),
            (':changes', None),
        ],
        'formats': [
            ('CSV', '/rinkimai/:dataset/json/:resource/data/:changes/:format/csv'),
            ('JSON', '/rinkimai/:dataset/json/:resource/data/:changes/:format/json'),
            ('JSONL', '/rinkimai/:dataset/json/:resource/data/:changes/:format/jsonl'),
            ('ASCII', '/rinkimai/:dataset/json/:resource/data/:changes/:format/ascii'),
        ],
        'datasets': [
            {'canonical': False, 'link': '/rinkimai/:dataset/json/:resource/data', 'name': 'json/data'},
            {'canonical': False, 'link': '/rinkimai/:dataset/xlsx/:resource/data', 'name': 'xlsx/data'},
        ],
        'items': [
            ('apygarda', '/rinkimai/apygarda'),
            ('apylinke', '/rinkimai/apylinke'),
            ('kandidatas', '/rinkimai/kandidatas'),
            ('turas', '/rinkimai/turas'),
        ],
        'header': [
            'change_id',
            'transaction_id',
            'datetime',
            'action',
            'id',
            'pavadinimas',
        ],
        'data': [
            [
                {'color': None, 'link': None, 'value': resp.context['data'][0][0]['value']},
                {'color': None, 'link': None, 'value': resp.context['data'][0][1]['value']},
                {'color': None, 'link': None, 'value': '2019-03-06T16:15:00.816308'},
                {'color': None, 'link': None, 'value': 'patch'},
                {'color': None, 'link': '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data', 'value': 'df6b9e04'},
                {'color': '#B2E2AD', 'link': None, 'value': 'Rinkimai 2'},
            ],
            [
                {'color': None, 'link': None, 'value': resp.context['data'][1][0]['value']},
                {'color': None, 'link': None, 'value': resp.context['data'][1][1]['value']},
                {'color': None, 'link': None, 'value': '2019-03-06T16:15:00.816308'},
                {'color': None, 'link': None, 'value': 'insert'},
                {'color': None, 'link': '/rinkimai/df6b9e04ac9e2467690bcad6d9fd673af6e1919b/:dataset/json/:resource/data', 'value': 'df6b9e04'},
                {'color': '#B2E2AD', 'link': None, 'value': 'Rinkimai 1'},
            ],
        ],
        'row': [],
    }


def test_count(context, app):
    consume(context.push([
        {
            'type': 'rinkimai/:dataset/json/:resource/data',
            'id': get_ref_id(1),
            'pavadinimas': 'Rinkimai 1',
        },
        {
            'type': 'rinkimai/:dataset/json/:resource/data',
            'id': get_ref_id(2),
            'pavadinimas': 'Rinkimai 2',
        },
    ]))

    app.authorize(['spinta_rinkimai_dataset_json_resource_data_search'])
    resp = app.get('/rinkimai/:dataset/json/:resource/data/:count', headers={'accept': 'text/html'})
    assert resp.status_code == 200

    resp.context.pop('request')
    assert resp.context['header'] == ['count']
    assert resp.context['data'] == [[{'color': None, 'link': None, 'value': 2}]]


def test_post(context, app):
    app.authorize([
        'spinta_country_insert',
        'spinta_country_getone',
    ])

    # tests basic object creation
    resp = app.post('/country', json={
        'title': 'Earth',
        'code': 'er',
    })
    assert resp.status_code == 201
    data = resp.json()
    id_ = data['id']
    assert uuid.UUID(id_).version == 4
    assert data == {
        'id': id_,
        'type': 'country',
        'code': 'er',
        'title': 'Earth',
        'revision': None,
    }

    resp = app.get(f'/country/{id_}')
    assert resp.status_code == 200
    assert resp.json() == {
        'type': 'country',
        'id': id_,
        'code': 'er',
        'title': 'Earth',
        'revision': None,
    }


def test_post_invalid_json(context, app):
    # tests 400 response on invalid json
    app.authorize(['spinta_country_insert'])
    headers = {"content-type": "application/json"}
    resp = app.post('/country', headers=headers, data="""{
        "title": "Earth",
        "code": "er"
    ]""")
    assert resp.status_code == 400
    assert resp.json() == {"error": "not a valid json"}


def test_post_empty_content(context, app):
    # tests posting empty content
    app.authorize(['spinta_country_insert'])
    headers = {
        "content-length": "0",
        "content-type": "application/json",
    }
    resp = app.post('/country', headers=headers, json=None)
    assert resp.status_code == 400
    assert resp.json() == {"error": "not a valid json"}


def test_post_id(context, app):
    # tests 400 response when trying to create object with id
    app.authorize(['spinta_country_insert'])
    resp = app.post('/country', json={
        'id': '42',
        'title': 'Earth',
        'code': 'er',
    })
    assert resp.status_code == 403
    assert resp.json() == {"error": "insufficient_scope"}


def test_post_update(context, app):
    # tests if update works with `id` present in the json
    app.authorize([
        'spinta_country_insert',
        'spinta_set_meta_fields',
    ])
    resp = app.post('/country', json={
        'id': '0007ddec-092b-44b5-9651-76884e6081b4',
        'title': 'Earth',
        'code': 'er',
    })

    assert resp.status_code == 201
    assert resp.json()['id'] == '0007ddec-092b-44b5-9651-76884e6081b4'


def test_post_revision(context, app):
    # tests 400 response when trying to create object with revision
    app.authorize(['spinta_country_insert'])
    resp = app.post('/country', json={
        'revision': 'r3v1510n',
        'title': 'Earth',
        'code': 'er',
    })
    assert resp.status_code == 400
    assert resp.json() == {"error": "cannot create 'revision'"}


@pytest.mark.skip('TODO')
def test_post_duplicate_id(context, app):
    # tests 400 response when trying to create object with id which exists
    app.authorize([
        'spinta_country_insert',
        'spinta_country_update',
        'spinta_set_meta_fields',
    ])
    resp = app.post('/country', json={
        'title': 'Earth',
        'code': 'er',
    })
    assert resp.status_code == 201
    data = resp.json()
    id = data['id']

    # TODO: this raises:
    #
    #           sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint
    #
    #       Should be handled some how and returned 400 error.
    resp = app.post('/country', json={
        'id': id,
        'title': 'Earth',
        'code': 'er',
    })
    assert resp.status_code == 400
    assert resp.json() == {"error": "cannot create duplicate 'id'"}


def test_post_non_json_content_type(context, app):
    # tests 400 response when trying to make non-json request
    app.authorize(['spinta_country_insert'])
    headers = {"content-type": "application/text"}
    resp = app.post('/country', headers=headers, json={
        "title": "Earth",
        "code": "er"
    })
    assert resp.status_code == 415
    assert resp.json() == {"error": "Only 'application/json' content-type is supported, got 'application/text'."}


def test_post_bad_auth_header(context, app):
    # tests 400 response when authorization header is missing `Bearer `
    auth_header = {'authorization': 'Fail f00b4rb4z'}
    resp = app.post('/country', headers=auth_header, json={
        'title': 'Earth',
        'code': 'er',
    })
    assert resp.status_code == 401
    assert resp.json() == {'error': 'unsupported_token_type'}


def test_streaming_response(context, app):
    consume(context.push([
        {
            'type': 'country',
            'code': 'fi',
            'title': 'Finland',
        },
        {
            'type': 'country',
            'code': 'lt',
            'title': 'Lithuania',
        },
    ]))

    app.authorize(['spinta_country_getall'])
    resp = app.get('/country').json()
    data = resp['data']
    data = sorted((x['code'], x['title']) for x in data)
    assert data == [
        ('fi', 'Finland'),
        ('lt', 'Lithuania'),
    ]
