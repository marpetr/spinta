from pathlib import Path

from spinta.core.config import RawConfig
from spinta.testing.tabular import create_tabular_manifest
from spinta.testing.manifest import load_manifest


def test_xlsx(rc: RawConfig, tmp_path: Path):
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
    create_tabular_manifest(tmp_path / 'manifest.xlsx', table)
    manifest = load_manifest(rc, tmp_path / 'manifest.xlsx')
    assert manifest == table
