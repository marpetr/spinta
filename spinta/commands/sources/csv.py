import csv

import requests

from spinta.commands import Command


class CsvModel(Command):
    metadata = {
        'name': 'csv',
        'type': 'dataset.model',
    }

    def execute(self):
        return self.read_csv()

    def read_csv(self):
        with requests.get(self.args.source, stream=True) as r:
            if r.encoding is None:
                r.encoding = 'utf-8'
            lines = r.iter_lines(decode_unicode=True)
            reader = csv.DictReader(lines)
            yield from reader