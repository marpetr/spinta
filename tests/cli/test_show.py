from spinta.testing.cli import SpintaCliRunner
from spinta.manifests.tabular.helpers import striptable
from spinta.testing.tabular import create_tabular_manifest


def test_show(rc, cli: SpintaCliRunner, tmp_path):
    manifest = striptable('''
    id | d | r | b | m | property | type   | ref     | source      | prepare | level | access    | uri | title | description
       | datasets/gov/example     |        |         |             |         |       | protected |     |       |
       |   | data                 | memory | default |             |         |       | protected |     |       |
       |                          |        |         |             |         |       |           |     |       |
       |   |   |   | Country      |        | code    | salis       |         |       | open      |     |       |
       |   |   |   |   | code     | string |         | kodas       |         |       | public    |     |       |
       |   |   |   |   | name     | string |         | pavadinimas |         |       | open      |     |       |
       |                          |        |         |             |         |       |           |     |       |
       |   |   |   | City         |        | name    | miestas     |         |       | open      |     |       |
       |   |   |   |   | name     | string |         | pavadinimas |         |       | open      |     |       |
       |   |   |   |   | country  | ref    | Country | salis       |         |       | open      |     |       |
       |                          |        |         |             |         |       |           |     |       |
       |   |   |   | Capital      |        | name    | miestas     |         |       | protected |     |       |
       |   |   |   |   | name     | string |         | pavadinimas |         |       | protected |     |       |
       |   |   |   |   | country  | ref    | Country | salis       |         |       | protected |     |       |
    ''')

    create_tabular_manifest(tmp_path / 'manifest.csv', manifest)

    result = cli.invoke(rc, ['show', tmp_path / 'manifest.csv'])

    assert striptable(result.stdout) == manifest
