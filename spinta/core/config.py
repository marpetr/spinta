from typing import Any, Dict, List, Optional, Tuple, Union

import collections
import logging
import os
import pathlib
import enum
import sys

from ruamel.yaml import YAML
import pkg_resources as pres

from spinta.utils.imports import importstr
from spinta.utils.schema import NA

Schema = Dict[str, Any]
Key = Tuple[str]

yaml = YAML(typ='safe')

log = logging.getLogger(__name__)

SCHEMA = {
    'type': 'object',
    'items': yaml.load(
        pathlib.Path(pres.resource_filename('spinta', 'config.yml')).
        read_text()
    ),
}


def read_config(args=None):
    rc = RawConfig()
    rc.read([
        Path('spinta', 'spinta.config:CONFIG'),
        EnvFile('envfile', '.env'),
        EnvVars('envvars', os.environ),
        CliArgs('cliargs', args or []),
    ])

    # Inject extenstion provided defaults
    configs = rc.get('config', cast=list, default=[])
    if configs:
        rc.read([Path(c, c) for c in configs], after='spinta')

    return rc


class KeyFormat(enum.Enum):
    CFG = 'cfg'
    CLI = 'cli'
    ENV = 'env'


class ConfigSource:

    def __init__(self, name=None, config=None):
        self.name = self.getname(name)
        self.config = config

    def __str__(self):
        return self.name

    def __repr__(self):
        return type(self).__module__ + '.' + type(self).__name__ + '(' + repr(self.name) + ')'

    def getname(self, name):
        return name or self.name or type(self).__name__

    def read(self, schema: Schema):
        config = {}
        for k, v in self.config.items():
            v = dict(_traverse(v, k))
            v.update(_get_inner_keys(v, depth=len(k)))
            config.update(v)
        self.config = config

    def keys(self, env: str = None):
        if env:
            for key in self.config:
                if key[:2] == ('environments', env):
                    yield key[2:]
        else:
            for key in self.config:
                if key[:1] != ('environments',):
                    yield key

    def get(self, key: tuple, env: str = None):
        if env:
            return self.config.get(('environments', env) + key, NA)
        else:
            return self.config.get(key, NA)


class PyDict(ConfigSource):

    def read(self, schema: Schema):
        envs = self.config.pop('environments', {})
        config = {
            tuple(k.split('.')): v
            for k, v in self.config.items()
        }
        for env, values in envs.items():
            for k, v in values.items():
                config[('environments', env) + tuple(k.split('.'))] = v
        self.config = config
        super().read(schema)


class Path(PyDict):

    def read(self, schema: Schema):
        if self.config.endswith(('.yml', '.yaml')):
            path = pathlib.Path(self.config)
            self.config = yaml.load(path.read_text())
        else:
            self.config = importstr(self.config)
        super().read(schema)


class CliArgs(PyDict):
    name = 'cli'

    def read(self, schema: Schema):
        config = {}
        for arg in self.config:
            key, val = arg.split('=', 1)
            if ',' in val:
                val = [v.strip() for v in val.split(',')]
            config[key] = val
        self.config = config
        super().read(schema)


class EnvVars(ConfigSource):
    name = 'env'

    def read(self, schema: Schema):
        config = {}
        for key, val in self.config.items():
            if not key.startswith('SPINTA_'):
                continue
            key = key[len('SPINTA_'):]
            key = tuple(key.lower().split('__'))
            if len(key) > 1 and key[0] not in schema['items'] and key[1] in schema['items']:
                key = ('environments',) + key
            config[key] = val
        self.config = config
        super().read(schema)


class EnvFile(EnvVars):

    def read(self, schema: Schema):
        config = {}
        path = pathlib.Path(self.config)
        if path.exists():
            with path.open() as f:
                for line in f:
                    if line.startswith('#'):
                        continue
                    line = line.strip()
                    if line == '':
                        continue
                    if '=' not in line:
                        continue
                    name, value = line.split('=', 1)
                    config[name] = value
        self.config = config
        super().read(schema)


class RawConfig:

    def __init__(self, sources=None):
        self._locked = False
        self._sources = sources or []
        self._keys: Dict[Tuple[str], Tuple[int, List[str]]] = {}
        self._schema = SCHEMA

    def read(
        self,
        sources: List[ConfigSource],
        after: Optional[int] = None,
    ):
        if self._locked:
            raise Exception(
                "Configuration is locked, use `rc.fork()` if you need to "
                "change configuration."
            )

        for config in sources:
            log.info(f"Reading config from {config.name}.")
            config.read(self._schema)

        if after is not None:
            pos = (i for i, s in enumerate(self._sources) if s.name == after)
            pos = next(pos, None)
            if pos is None:
                raise Exception(f"Given after value {after!r} does not exist.")
            pos += 1
            self._sources[pos:pos] = sources
        else:
            self._sources.extend(sources)

        self._keys = self._update_keys()

    def add(self, name, params):
        self.read([PyDict(name, params)])
        return self

    def fork(self, sources=None, after=None):
        rc = RawConfig(list(self._sources))
        if sources:
            rc.read(sources, after)
        else:
            rc._keys = rc._update_keys()
        return rc

    def lock(self):
        self._locked = True

    def get(self, *key, default=None, cast=None, required=False, exists=False, origin=False):
        env, _ = self._get_config_value(('env',), default=None)
        value, config = self._get_config_value(key, default, env)

        if cast is not None:
            if cast is list and isinstance(value, str):
                value = value.split(',') if value else []
            elif value is not None:
                value = cast(value)

        if required and not value:
            name = '.'.join(key)
            raise Exception(f"{name!r} is a required configuration option.")

        if exists and isinstance(value, pathlib.Path) and not value.exists():
            name = '.'.join(key)
            raise Exception(f"{name} ({value}) path does not exist.")

        if origin:
            if config:
                return value, config.name
            else:
                return value, ''
        else:
            return value

    def keys(self, *key, origin=False) -> Union[
        List[str],
        Tuple[List[str], str]
    ]:
        config, keys = self._keys.get(key, (None, []))
        return (keys, config.name) if origin else keys

    def getall(self, *key, origin=False):
        keys = self.keys(*key)
        if keys:
            for k in keys:
                yield from self.getall(*key, k, origin=origin)
        else:
            res = self.get(*key, origin=origin)
            res = res if origin else (res,)
            yield (key,) + res

    def dump(self, *names, fmt: KeyFormat = KeyFormat.CFG, file=sys.stdout):
        table = [('Origin', 'Name', 'Value')]
        sizes = [len(x) for x in table[0]]
        for key, val, origin in self.getall(origin=True):
            if names:
                for name in names:
                    it = enumerate(name.split('.'))
                    if all(key[i].startswith(k) for i, k in it if k):
                        break
                else:
                    continue

            if fmt == KeyFormat.ENV:
                key = 'SPINTA_' + '__'.join(key).upper()
            else:
                key = '.'.join(key)

            if isinstance(val, list):
                for i, v in enumerate(val):
                    row = (origin, key + f'.{i}', v)
                    table.append(row)
                    sizes = [max(x) for x in zip(sizes, map(len, map(str, row)))]
            else:
                row = (origin, key, val)
                table.append(row)
                sizes = [max(x) for x in zip(sizes, map(len, map(str, row)))]

        table = (
            table[:1] +
            [tuple(['-' * s for s in sizes])] +
            table[1:]
        )
        if file:
            for row in table:
                print('  '.join([str(x).ljust(s) for x, s in zip(row, sizes)]), file=file)
        else:
            return table

    def _update_keys(self) -> Dict[Key, List[str]]:
        """Update inner keys respecting already set values."""
        keys = {}
        env, _ = self._get_config_value(('env',), default=None)
        for config in self._sources:
            self._update_config_keys(keys, config, config.keys())
            if env:
                self._update_config_keys(keys, config, config.keys(env), env)
        return keys

    def _update_config_keys(self, keys, config, ckeys, env=None):
        # Update `keys` in place.
        if () not in keys:
            keys[()] = config, []
        for key in ckeys:
            if key and key[0] not in keys[()][1]:
                keys[()][1].append(key[0])
            n = len(key)
            schema = self._schema
            for i in range(1, n + 1):
                schema = self._get_object_schema(schema, key[i - 1])
                if schema is None or schema['type'] != 'object':
                    # Skip all non object keys, only objects can have keys.
                    break
                k = tuple(key[:i])
                v = config.get(k, env)
                if v is not NA:
                    # Source has explicit value set.
                    if isinstance(v, str):
                        v = [x.strip() for x in v.split(',')]
                    else:
                        v = list(v)
                    keys[k] = config, v
                elif i < n:
                    # No explicit value set, just collect all parents.
                    if k not in keys:
                        keys[k] = config, []
                    if key[i] not in keys[k][1]:
                        keys[k][1].append(key[i])

    def _get_object_schema(self, schema: Schema, key: str):
        if schema['type'] == 'object':
            if 'items' in schema:
                return schema['items'].get(key)
            if 'keys' in schema and schema['keys']['type'] == 'string':
                return schema['values']

    def _get_config_value(self, key: Key, default: Any = None, env: str = None):
        assert isinstance(key, tuple)
        for config in reversed(self._sources):
            val = config.get(key, env)
            if env and val is NA:
                val = config.get(key)
            if val is not NA:
                return val, config
        return default, None


def _traverse(value, path=()):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _traverse(v, path + (k,))
    else:
        yield path, value


def _get_inner_keys(config: Dict[tuple, Any], depth=1):
    """Get inner keys for config.

    `config` is flattened dict, that looks like this:

        {
            ('a', 'b', 'c'): 1,
            ('a', 'b', 'd'): 2,
        }

    Nested version of this would look like this:

        {
            'a': {
                'b': {
                    'c': 1,
                    'd': 1,
                }
            }
        }

    Then, the purpose of this function is to add keys to all inner nesting
    levels. For this example, function result will be:

        {
            ('a'): ['b'],
            ('a', 'b'): ['c', 'd'],
        }

    This is needed for `RawConfig` class, in order to be able to do things like
    this:

        config.keys('a', 'b')
        ['c', 'd']

    And this functionality is needed, because of environment variables. For
    example, in order to add a new backend, first you need to add new keys, like
    this:

        SPINTA_A=b,x

    And then, you can add values to it:

        SPINTA_A_X=3

    And the end configuration will look like this:

        {
            'a': {
                'b': {
                    'c': 1,
                    'd': 1,
                },
                'x': '3'
            }
        }

    """
    inner = collections.defaultdict(list)
    for key in config.keys():
        for i in range(depth, len(key)):
            k = tuple(key[:i])
            if key[i] not in inner[k]:
                inner[k].append(key[i])
    return inner


def _get_from_prefix(config: dict, prefix: tuple):
    for k, v in config.items():
        if k[:len(prefix)] == prefix:
            yield k[len(prefix):], v