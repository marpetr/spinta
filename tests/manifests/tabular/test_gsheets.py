from pathlib import Path

import py.path
from responses import GET
from responses import RequestsMock

from spinta.core.config import RawConfig
from spinta.testing.tabular import create_tabular_manifest
from spinta.testing.tabular import load_tabular_manifest


def test_gsheets(rc: RawConfig, tmpdir: py.path.local, responses: RequestsMock):
    path = Path(tmpdir) / 'manifest.csv'
    table = '''
    d | r | b | m | property | source      | prepare   | type       | ref     | level | access | uri | title   | description
    datasets/gov/example     |             |           |            |         |       | open   |     | Example |
      | data                 |             |           | postgresql | default |       | open   |     | Data    |
                             |             |           |            |         |       |        |     |         |
      |   |   | country      |             | code='lt' |            | code    |       | open   |     | Country |
      |   |   |   | code     | kodas       | lower()   | string     |         | 3     | open   |     | Code    |
      |   |   |   | name     | pavadinimas |           | string     |         | 3     | open   |     | Name    |
                             |             |           |            |         |       |        |     |         |
      |   |   | city         |             |           |            | name    |       | open   |     | City    |
      |   |   |   | name     | pavadinimas |           | string     |         | 3     | open   |     | Name    |
      |   |   |   | country  | šalis       |           | ref        | country | 4     | open   |     | Country |
    '''
    create_tabular_manifest(path, table)

    gsheet = (
        'https://docs.google.com/spreadsheets'
        '/d/1sS9B5QtX6IZjYhs8dCtk4PCWYpCmTdaGuSAkJwTQ_C0'
        '/edit#gid=0'
    )
    gsheet_csv = (
        'https://docs.google.com/spreadsheets'
        '/d/1sS9B5QtX6IZjYhs8dCtk4PCWYpCmTdaGuSAkJwTQ_C0'
        '/gviz/tq'
        '?tqx=out:csv'
        '&gid=0'
    )
    responses.add(
        GET, gsheet_csv,
        status=200,
        content_type='text/plain; charset=utf-8',
        body=path.read_bytes(),
    )

    manifest = load_tabular_manifest(rc, gsheet)
    assert manifest == table