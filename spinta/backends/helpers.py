from typing import Dict

from spinta import commands
from spinta import exceptions
from spinta.backends import Backend
from spinta.components import Component
from spinta.components import Context


def load_backend(
    context: Context,
    component: Component,
    name: str,
    data: Dict[str, str]
) -> Backend:
    config = context.get('config')
    type_ = data['type']
    if type_ not in config.components['backends']:
        raise exceptions.BackendNotFound(component, name=type_)
    Backend_ = config.components['backends'][type_]
    backend: Backend = Backend_()
    backend.type = type_
    backend.name = name
    backend.config = data
    commands.load(context, backend, data)
    return backend