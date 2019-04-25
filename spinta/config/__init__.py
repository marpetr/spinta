import collections
import os
import pathlib

from spinta.utils.imports import importstr


CONFIG = {
    'config': [],
    'commands': {
        'modules': [
            'spinta.types',
            'spinta.backends',
            'spinta.urlparams',
        ],
        'source': {
            'csv': 'spinta.commands.sources.csv:read_csv',
            'html': 'spinta.commands.sources.html:read_html',
            'json': 'spinta.commands.sources.json:read_json',
            'url': 'spinta.commands.sources.url:read_url',
            'xlsx': 'spinta.commands.sources.xlsx:read_xlsx',
            'xml': 'spinta.commands.sources.xml:read_xml',
        },
        'service': {
            'range': 'spinta.commands.helpers:range_',
        },
    },
    'components': {
        'backends': {
            'postgresql': 'spinta.backends.postgresql:PostgreSQL',
            'mongo': 'spinta.backends.mongo:Mongo',
        },
        'nodes': {
            'model': 'spinta.components:Model',
            'project': 'spinta.types.project:Project',
            'dataset': 'spinta.types.dataset:Dataset',
            'owner': 'spinta.types.owner:Owner',
        },
        'types': {
            'integer': 'spinta.types.type:Integer',
            'any': 'spinta.types.type:Type',
            'pk': 'spinta.types.type:PrimaryKey',
            'date': 'spinta.types.type:Date',
            'datetime': 'spinta.types.type:DateTime',
            'string': 'spinta.types.type:String',
            'integer': 'spinta.types.type:Integer',
            'number': 'spinta.types.type:Number',
            'boolean': 'spinta.types.type:Boolean',
            'url': 'spinta.types.type:URL',
            'image': 'spinta.types.type:Image',
            'spatial': 'spinta.types.type:Spatial',
            'ref': 'spinta.types.type:Ref',
            'backref': 'spinta.types.type:BackRef',
            'generic': 'spinta.types.type:Generic',
            'array': 'spinta.types.type:Array',
            'object': 'spinta.types.type:Object',
        },
        'urlparams': {
            'component': 'spinta.urlparams:UrlParams',
            # do not bother with versions for this time
            # 'versions': {
            #     '1': 'spinta.urlparams:Version',
            # },
        },
    },
    'exporters': {
        'ascii': 'spinta.commands.formats.ascii:Ascii',
        'csv': 'spinta.commands.formats.csv:Csv',
        'json': 'spinta.commands.formats.json:Json',
        'jsonl': 'spinta.commands.formats.jsonl:JsonLines',
    },
    'backends': {
        'default': {
            'backend': 'spinta.backends.postgresql:PostgreSQL',
            'dsn': 'postgresql:///spinta',
        },
    },
    'manifests': {
        'default': {
            'backend': 'default',
            'path': pathlib.Path(),
        },
    },
    'ignore': [
        '.travis.yml',
        '/prefixes.yml',
        '/schema/',
        '/env/',
    ],
    'debug': False,

    # How much time to wait in seconds for the backends to go up.
    'wait': 30,

    'env': 'dev',

    'environments': {
        'dev': {
            'backends': {
                'mongo': {
                    'backend': 'spinta.backends.mongo:Mongo',
                    'dsn': 'mongodb://admin:admin123@localhost:27017/',
                    'db': 'splat',
                },
            },
            'manifests': {
                'default': {
                    'backend': 'default',
                    'path': pathlib.Path() / 'tests/manifest',
                },
            },
        },
        'test': {
            'backends': {
                'default': {
                    'backend': 'spinta.backends.postgresql:PostgreSQL',
                    'dsn': 'postgresql:///spinta_tests',
                },
                'mongo': {
                    'backend': 'spinta.backends.mongo:Mongo',
                    'dsn': 'mongodb://admin:admin123@localhost:27017/',
                    'db': 'spinta_test',
                },
            },
            'manifests': {
                'default': {
                    'backend': 'default',
                    'path': pathlib.Path() / 'tests/manifest',
                },
            },
        }
    },
}


class Config:

    def __init__(self):
        self._config = {
            'cliargs': {},
            'environ': {},
            'envfile': {},
            'default': {},
        }

    def read(self, config=None, *, env_vars=None, env_files=None, cli_args=None):
        # Default configuration.
        self._add_config(CONFIG)

        # Add CLI args
        if cli_args:
            self._add_cli_args(cli_args)

        # Environment variables.
        if env_vars is None or env_vars is True:
            self._set_env_vars(os.environ)
        elif isinstance(env_vars, dict):
            self._set_env_vars(env_vars)

        # Environment files.
        if env_files is None or env_files is True:
            self._add_env_file('.env')
        elif isinstance(env_files, list):
            for env_file in env_files:
                self._add_env_file(env_file)

        # Add user supplied config.
        if config:
            self._add_config(config)

        # Override defaults from other locations.
        for _config in self.get('config', cast=list, default=[]):
            _config = importstr(_config)
            self._add_config(_config)

        # Update defaults from specified environment.
        environment = self.get('env', default=None)
        if environment:
            self._config['default'].update(dict(_get_from_prefix(
                self._config['default'],
                ('environments', environment),
            )))

        # Create inner keys
        self._config['default'].update(_get_inner_keys(self._config['default']))

    def get(self, *key, default=None, cast=None, env=True, required=False):
        environment = self._get_config_value('environment', default=None, envvar=True)
        value = self._get_config_value(key, default, env, environment=environment)

        if cast is not None:
            if cast is list and isinstance(value, str):
                value = value.split(',') if value else []
            elif value is not None:
                value = cast(value)

        if required and not value:
            raise Exception("'%s' is a required configuration option." % '.'.join(key))

        return value

    def keys(self, *key, **kwargs):
        kwargs.setdefault('default', [])
        return self.get(*key, cast=list, **kwargs)

    def getall(self):
        for key, value in self._config['default'].items():
            yield key, self.get(*key, cast=type(value))

    def _add_config(self, config):
        self._config['default'].update(_traverse(config))

    def _add_cli_args(self, args):
        for arg in args:
            name, value = arg.split('=', 1)
            key = tuple(name.split('.'))
            self._config['cliargs'][key] = value
        self._config['cliargs'].update(_get_inner_keys(self._config['cliargs']))

    def _add_env_file(self, path):
        if isinstance(path, str):
            path = pathlib.Path(path)

        if not path.exists():
            return

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
                self._config['envfile'][name] = value

    def _set_env_vars(self, environ):
        self._config['environ'] = environ

    def _get_config_value(self, key: tuple, default, envvar, environment=None):

        # 1. Get value from command line arguments.
        if key in self._config['cliargs']:
            return self._config['cliargs'][key]

        # Auto-generate environment variable name.
        if envvar is True:
            envvar = 'SPINTA_' + '_'.join(key).upper()

        # 2. Get value from environment.
        if envvar and envvar in self._config['environ']:
            return self._config['environ'][envvar]

        # 3. Get value from env file.
        if envvar and envvar in self._config['envfile']:
            return self._config['envfile'][envvar]

        # 4. Get value from default configs.
        if key in self._config['default']:
            return self._config['default'][key]

        return default


def _traverse(value, path=()):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from _traverse(v, path + (k,))
    else:
        yield path, value


def _get_inner_keys(config: dict):
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

    This is needed for Config class, in order to be able to do things like this:

        >>> config.keys('a', 'b')
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
        for i in range(1, len(key)):
            k = tuple(key[:i])
            if key[i] not in inner[k]:
                inner[k].append(key[i])
    return inner


def _get_from_prefix(config: dict, prefix: tuple):
    for k, v in config.items():
        if k[:len(prefix)] == prefix:
            yield k[len(prefix):], v