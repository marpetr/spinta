import logging

from spinta import commands
from spinta.components import Context
from spinta.manifests.components import Manifest
from spinta.manifests.helpers import load_manifest_nodes
from spinta.manifests.tabular.components import TabularManifest
from spinta.manifests.tabular.helpers import read_tabular_manifest

log = logging.getLogger(__name__)


@commands.load.register(Context, TabularManifest)
def load(
    context: Context,
    manifest: TabularManifest,
    *,
    into: Manifest = None,
    freezed: bool = True,
):
    assert freezed, (
        "TabularManifest does not have unfreezed version of manifest."
    )
    target = into or manifest
    store = context.get('store')
    commands.load(context, store.internal, into=target)

    if into:
        log.info(
            'Loading freezed manifest %r into %r from %s.',
            manifest.name,
            into.name,
            manifest.path.resolve(),
        )
    else:
        log.info(
            'Loading freezed manifest %r from %s.',
            manifest.name,
            manifest.path.resolve(),
        )
    schemas = read_tabular_manifest(manifest)
    load_manifest_nodes(context, target, schemas)