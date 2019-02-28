import collections

import pkg_resources as pres
import uvicorn

from starlette.applications import Starlette
from starlette.templating import Jinja2Templates

from spinta.utils.url import parse_url_path
from spinta.utils.tree import build_path_tree
from spinta.store import get_model_from_params


templates = Jinja2Templates(directory=pres.resource_filename('spinta', 'templates'))

app = Starlette()

store = None


@app.route('/{path:path}')
async def homepage(request):
    global store

    path = request.path_params['path'].strip('/')
    params = parse_url_path(path)
    path = params['path']
    loc = get_current_location(path, params)

    if 'source' in params:
        items = []
        datasets = []
        data = list(get_data(store, params))
        if len(data) == 1:
            data = []

    else:
        datasets_by_object = get_datasets_by_object(store)
        tree = build_path_tree(
            store.objects['default'].get('model', {}).keys(),
            datasets_by_object.keys(),
        )
        items = get_directory_content(tree, path) if path in tree else []
        datasets = list(get_directory_datasets(datasets_by_object, path))
        data = []

    return templates.TemplateResponse('base.html', {
        'request': request,
        'location': loc,
        'items': items,
        'datasets': datasets,
        'data': data,
    })


def run(store):
    set_store(store)
    app.debug = store.config.debug
    uvicorn.run(app, host='0.0.0.0', port=8000)


def set_store(store_):
    global store
    if store is not None:
        raise Exception("Store was already set.")
    store = store_


def get_current_location(path, params):
    parts = path.split('/') if path else []
    loc = [('root', '/')]

    if 'source' in params:
        loc += (
            [(p, '/' + '/'.join(parts[:i])) for i, p in enumerate(parts, 1)] +
            [(':source/' + params['source'], None)]
        )
    else:
        loc += (
            [(p, '/' + '/'.join(parts[:i])) for i, p in enumerate(parts[:-1], 1)] +
            [(p, None) for p in parts[-1:]]
        )
    return loc


def get_datasets_by_object(store):
    datasets = collections.defaultdict(dict)
    for dataset in store.objects['default'].get('dataset', {}).values():
        for obj in dataset.objects.values():
            datasets[obj.name][dataset.name] = dataset
    return datasets


def get_directory_content(tree, path):
    return [
        (item, ('/' if path else '') + path + '/' + item)
        for item in tree[path]
    ]


def get_directory_datasets(datasets, path):
    if path in datasets:
        for name in sorted(datasets[path].keys()):
            link = ('/' if path else '') + path + '/:source/' + name
            yield name, link


def get_data(store, params):
    model = get_model_from_params(store, 'default', params['path'], params)
    rows = store.getall(params['path'], {'limit': 100, **params})

    props = list(model.properties.values())

    yield [prop.name for prop in props]

    for data in rows:
        row = []
        for prop in props:
            row.append(data.get(prop.name))
        yield row