import importlib
import pathlib

from spinta.core.config import RawConfig
from spinta.utils.imports import importstr


def create_context(**kwargs):
    rc = RawConfig()
    rc.read(**kwargs)

    load_commands(rc.get('commands', 'modules', cast=list))

    Context = rc.get('components', 'core', 'context', cast=importstr)
    context = Context('base')
    context.set('config.raw', rc)

    Config = rc.get('components', 'core', 'config', cast=importstr)
    context.set('config', Config())

    Store = rc.get('components', 'core', 'store', cast=importstr)
    context.set('store', Store())

    return context


def load_commands(modules):
    for module_path in modules:
        module = importlib.import_module(module_path)
        path = pathlib.Path(module.__file__).resolve()
        if path.name != '__init__.py':
            continue
        path = path.parent
        base = path.parents[module_path.count('.')]
        for path in path.glob('**/*.py'):
            if path.name == '__init__.py':
                module_path = path.parent.relative_to(base)
            else:
                module_path = path.relative_to(base).with_suffix('')
            module_path = '.'.join(module_path.parts)
            module = importlib.import_module(module_path)
