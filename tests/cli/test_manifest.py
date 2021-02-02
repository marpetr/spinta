from spinta.testing.cli import SpintaCliRunner
from spinta.manifests.tabular.helpers import striptable
from spinta.testing.tabular import create_tabular_manifest
from spinta.testing.tabular import load_tabular_manifest
from spinta.manifests.tabular.helpers import render_tabular_manifest


def test_copy(rc, cli: SpintaCliRunner, tmpdir):
    create_tabular_manifest(tmpdir / 'manifest.csv', striptable('''
    d | r | b | m | property | type   | ref     | source      | access
    datasets/gov/example     |        |         |             |
      | data                 | sql    |         |             |
                             |        |         |             |
      |   |   | country      |        | code    | salis       |
      |   |   |   | code     | string |         | kodas       | public
      |   |   |   | name     | string |         | pavadinimas | open
      |   |                  |        |         |             |
      |   |   | city         |        | name    | miestas     |
      |   |   |   | name     | string |         | pavadinimas | open
      |   |   |   | country  | ref    | country | salis       | open
                             |        |         |             |
      |   |   | capital      |        | name    | miestas     |
      |   |   |   | name     | string |         | pavadinimas |
      |   |   |   | country  | ref    | country | salis       |
    '''))

    cli.invoke(rc, [
        'copy', '--no-source', '--access', 'open',
        tmpdir / 'manifest.csv',
        tmpdir / 'result.csv',
    ])

    manifest = load_tabular_manifest(rc, tmpdir / 'result.csv')
    cols = [
        'dataset', 'resource', 'base', 'model', 'property',
        'type', 'ref', 'source', 'level', 'access',
    ]
    assert render_tabular_manifest(manifest, cols) == striptable('''
    d | r | b | m | property | type   | ref     | source | level | access
    datasets/gov/example     |        |         |        |       | protected
      | data                 | sql    |         |        |       | protected
                             |        |         |        |       |
      |   |   | country      |        |         |        |       | open
      |   |   |   | name     | string |         |        |       | open
                             |        |         |        |       |
      |   |   | city         |        |         |        |       | open
      |   |   |   | name     | string |         |        |       | open
      |   |   |   | country  | ref    | country |        |       | open
    ''')


def test_copy_with_filters_and_externals(rc, cli, tmpdir):
    create_tabular_manifest(tmpdir / 'manifest.csv', striptable('''
    d | r | b | m | property | type   | ref     | source      | prepare   | access
    datasets/gov/example     |        |         |             |           |
      | data                 | sql    |         |             |           |
                             |        |         |             |           |
      |   |   | country      |        | code    | salis       | code='lt' |
      |   |   |   | code     | string |         | kodas       |           | private
      |   |   |   | name     | string |         | pavadinimas |           | open
                             |        |         |             |           |
      |   |   | city         |        | name    | miestas     |           |
      |   |   |   | name     | string |         | pavadinimas |           | open
      |   |   |   | country  | ref    | country | salis       |           | open
                             |        |         |             |           |
      |   |   | capital      |        | name    | miestas     |           |
      |   |   |   | name     | string |         | pavadinimas |           |
      |   |   |   | country  | ref    | country | salis       |           |
    '''))

    cli.invoke(rc, [
        'copy', '--access', 'open',
        tmpdir / 'manifest.csv',
        tmpdir / 'result.csv',
    ])

    manifest = load_tabular_manifest(rc, tmpdir / 'result.csv')
    cols = [
        'dataset', 'resource', 'base', 'model', 'property',
        'type', 'ref', 'source', 'prepare', 'level', 'access',
    ]
    assert render_tabular_manifest(manifest, cols) == striptable('''
    d | r | b | m | property | type   | ref     | source      | prepare   | level | access
    datasets/gov/example     |        |         |             |           |       | protected
      | data                 | sql    |         |             |           |       | protected
                             |        |         |             |           |       |
      |   |   | country      |        |         | salis       | code='lt' |       | open
      |   |   |   | name     | string |         | pavadinimas |           |       | open
                             |        |         |             |           |       |
      |   |   | city         |        | name    | miestas     |           |       | open
      |   |   |   | name     | string |         | pavadinimas |           |       | open
      |   |   |   | country  | ref    | country | salis       |           |       | open
    ''')
