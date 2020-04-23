from typing import Iterator, Optional, Tuple

import csv
import itertools

from spinta import spyna
from spinta.components import Model
from spinta.manifests.components import Manifest
from spinta.manifests.tabular.components import TabularManifest
from spinta.manifests.tabular.constants import DATASET


def read_tabular_manifest(
    manifest: TabularManifest
) -> Iterator[Tuple[int, Optional[dict]]]:
    with manifest.path.open() as f:
        reader = csv.DictReader(f)
        header = next(reader, None)
        if header is None:
            return
        reader = itertools.chain([header], reader)
        header = list(header)

        unknown_columns = set(header[:len(DATASET)]) - set(DATASET)
        if unknown_columns:
            unknown_columns = ', '.join(sorted(unknown_columns, key=header.index))
            raise Exception(f"Unknown columns: {unknown_columns}.")

        dataset = None
        resource = None
        base = None
        model = {}
        models = {}
        datasets = {}
        category = ['dataset', 'resource', 'base', 'model']
        for i, row in enumerate(reader):
            if all(row[k] == '' for k in category + ['property']):
                continue

            if row['dataset']:
                if model:
                    yield model['eid'], model['schema']
                    model = None
                if dataset:
                    yield dataset['eid'], dataset['schema']
                if row['dataset'] in datasets:
                    eid = datasets[row['dataset']]
                    raise Exception(
                        f"Row {i}: dataset {row['dataset']} is already "
                        f"defined in {eid}."
                    )
                datasets[row['dataset']] = i
                dataset = {
                    'eid': i,
                    'resources': {},
                    'schema': {
                        'type': 'dataset',
                        'name': row['dataset'],
                        'id': row['id'],
                        'level': row['level'],
                        'access': row['access'],
                        'title': row['title'],
                        'description': row['description'],
                        'resources': {}
                    },
                }
                resource = None
                base = None

            elif row['resource']:
                if model:
                    yield model['eid'], model['schema']
                    model = None
                if dataset is None:
                    raise Exception(
                        f"Row {i}: dataset must be defined before resource."
                    )
                if row['resource'] in dataset['resources']:
                    eid = dataset['resources'][row['resource']]
                    raise Exception(
                        f"Row {i}: resource {row['resource']} is already "
                        f"defined in {eid}."
                    )
                resource = {
                    'eid': i,
                    'name': row['resource'],
                    'schema': {
                        'type': 'resource',
                        'external': row['source'],
                        'level': row['level'],
                        'access': row['access'],
                        'title': row['title'],
                        'description': row['description'],
                    }
                }
                dataset['resources'][row['resource']] = i
                dataset['schema']['resources'][row['resource']] = resource['schema']
                base = None

            elif row['base']:
                if model:
                    yield model['eid'], model['schema']
                    model = None
                if resource is None:
                    raise Exception(
                        f"Row {i}: resource must be defined before base."
                    )
                base = {
                    'model': get_relative_model_name(dataset, resource, row['base']),
                    'pk': row['ref'],
                }

            elif row['model']:
                if model:
                    yield model['eid'], model['schema']
                if resource is None:
                    raise Exception(
                        f"Row {i}: resource must be defined before model."
                    )
                if row['model'] in models:
                    eid = models[row['model']]
                    raise Exception(
                        f"Row {i}: model {row['model']} is already "
                        f"defined in {eid}."
                    )
                models[row['model']] = i
                model = {
                    'eid': i,
                    'properties': {},
                    'schema': {
                        'type': 'model',
                        'name': get_relative_model_name(dataset, resource, row['model']),
                        'id': row['id'],
                        'level': row['level'],
                        'access': row['access'],
                        'title': row['title'],
                        'description': row['description'],
                        'external': {
                            'dataset': dataset['schema']['name'],
                            'resource': resource['name'],
                            'name': row['source'],
                        },
                        'properties': {},
                    },
                }
                if row['prepare']:
                    model['schema']['external']['prepare'] = spyna.parse(row['prepare'])
                if row['ref']:
                    model['schema']['external']['pk'] = [
                        x.strip() for x in row['ref'].split(',')
                    ]
                if base:
                    model['base'] = base
                    base = None

            elif row['property']:
                if model is None:
                    raise Exception(
                        f"Row {i}: model must be defined before property."
                    )
                if row['property'] in model['properties']:
                    eid = model['properties'][row['properties']]
                    raise Exception(
                        f"Row {i}: property {row['property']} is already "
                        f"defined in {eid}."
                    )
                prop = {
                    'eid': i,
                    'schema': {
                        'type': row['type'],
                        'level': row['level'],
                        'access': row['access'],
                        'title': row['title'],
                        'description': row['description'],
                        'external': row['source'],
                    },
                }
                if row['prepare']:
                    prop['schema']['external'] = {
                        'name': row['source'],
                        'prepare': spyna.parse(row['prepare']),
                    }
                else:
                    prop['schema']['external'] = row['source']
                if row['ref']:
                    prop['schema']['object'] = get_relative_model_name(dataset, resource, row['ref'])
                model['properties'][row['property']] = i
                model['schema']['properties'][row['property']] = prop['schema']

        if dataset:
            yield dataset['eid'], dataset['schema']
        if model:
            yield model['eid'], model['schema']


def get_relative_model_name(dataset: dict, resource: dict, name: str) -> str:
    if name.startswith('/'):
        return name[1:]
    else:
        return '/'.join([
            dataset['schema']['name'],
            resource['name'],
            name,
        ])


def to_relative_model_name(base: Model, model: Model) -> str:
    """Convert absolute model `name` to relative."""
    if (
        base.external.dataset.name == model.external.dataset.name and
        base.external.resource.name == model.external.resource.name
    ):
        prefix = '/'.join([
            base.external.dataset.name,
            base.external.resource.name,
        ])
        return model.name[len(prefix) + 1:]
    else:
        return '/' + model.name


def tabular_eid(model: Model):
    if isinstance(model.eid, int):
        return model.eid
    else:
        return 0


def datasets_to_tabular(manifest: Manifest):
    dataset = None
    resource = None
    for model in sorted(manifest.objects['model'].values(), key=tabular_eid):
        if not model.external:
            continue

        if dataset is None or dataset.name != model.external.dataset.name:
            dataset = model.external.dataset
            yield torow(DATASET, {
                'id': dataset.id,
                'dataset': dataset.name,
                'level': dataset.level,
                'access': dataset.access,
                'title': dataset.title,
                'description': dataset.description,
            })

        if resource is None or resource.name != model.external.resource.name:
            resource = model.external.resource
            yield torow(DATASET, {
                'resource': resource.name,
                'level': resource.level,
                'access': resource.access,
                'title': resource.title,
                'description': resource.description,
            })

        yield torow(DATASET, {})

        data = {
            'id': model.id,
            'model': to_relative_model_name(model, model),
            'source': ','.join(model.external.name),
            'prepare': spyna.unparse(model.external.prepare) if model.external.prepare else None,
            'ref': ','.join([p.name for p in model.external.pkeys]),
            'level': model.level,
            'access': model.access,
            'title': model.title,
            'description': model.description,
        }
        yield torow(DATASET, data)

        for prop in model.properties.values():
            if prop.name.startswith('_'):
                continue
            data = {
                'property': prop.name,
                'source': prop.external.name if prop.external else None,
                'prepare': spyna.unparse(prop.external.prepare) if prop.external and prop.external.prepare else None,
                'type': prop.dtype.name,
                'level': prop.level,
                'access': prop.access,
                'title': prop.title,
                'description': prop.description,
            }
            if prop.dtype.name == 'ref':
                data['ref'] = to_relative_model_name(model, model.manifest.models[prop.dtype.object])
            yield torow(DATASET, data)


def torow(keys, values):
    return {k: values.get(k) for k in keys}