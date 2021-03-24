from __future__ import annotations

import logging
import pathlib
from typing import List
from typing import Optional

from typer import Context as TyperContext
from typer import Option
from typer import Typer
from typer import echo

import spinta
from spinta.cli import auth
from spinta.cli import config
from spinta.cli import data
from spinta.cli import inspect
from spinta.cli import manifest
from spinta.cli import migrate
from spinta.cli import pii
from spinta.cli import pull
from spinta.cli import push
from spinta.cli import server
from spinta.cli.init import init
from spinta.cli.show import show
from spinta.cli.helpers.typer import add
from spinta.core.context import create_context

log = logging.getLogger(__name__)

app = Typer()

add(app, 'config', config.config, short_help="Show current configuration values")
add(app, 'check', config.check, short_help="Check configuration and manifests")

add(app, 'genkeys', auth.genkeys, short_help="Generate client token validation keys")
add(app, 'token', auth.token, short_help="Tools for encoding/decode auth tokens")
add(app, 'client', auth.client, short_help="Manage auth clients")

add(app, 'init', init, short_help="Initialize a new manifest table")
add(app, 'inspect', inspect.inspect, short_help=(
    "Update manifest schema from an external data source"
))
add(app, 'pii', pii.app, short_help="Manage Person Identifying Information")

add(app, 'copy', manifest.copy, short_help="Copy only specified metadata from a manifest")
add(app, 'show', show, short_help="Show manifest as ascii table")

add(app, 'bootstrap', migrate.bootstrap, short_help="Initialize backends")
add(app, 'sync', migrate.sync, short_help="Sync source manifests into main manifest")
add(app, 'migrate', migrate.migrate, short_help="Migrate schema changes to backends")
add(app, 'freeze', migrate.freeze, short_help=(
    "Detect schema changes and create new schema version"
))

add(app, 'import', data.import_, short_help="Import data from a file")
add(app, 'pull', pull.pull, short_help="Pull data from an external data source")
add(app, 'push', push.push, short_help="Push data into an external data store")

add(app, 'run', server.run, short_help="Run development server")
add(app, 'wait', server.wait, short_help="Wait while all backends are up")


@app.callback(invoke_without_command=True)
def main(
    ctx: TyperContext,
    option: Optional[List[str]] = Option(None, '-o', '--option', help=(
        "Set configuration option, example: `-o option.name=value`."
    )),
    env_file: Optional[pathlib.Path] = Option(None, '--env-file', help=(
        "Load configuration from a given .env file."
    )),
    version: bool = Option(False, help="Show version number.")
):
    ctx.obj = ctx.obj or create_context('cli', args=option, envfile=env_file)
    if version:
        echo(spinta.__version__)


