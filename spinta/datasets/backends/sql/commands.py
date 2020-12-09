import logging
from typing import Any

import sqlalchemy as sa
import sqlalchemy.exc
from sqlalchemy.engine import RowProxy

from spinta import commands
from spinta.components import Context
from spinta.components import Model
from spinta.core.config import RawConfig
from spinta.core.ufuncs import Expr
from spinta.datasets.backends.sql.components import Sql
from spinta.datasets.backends.sql.query import Selected
from spinta.datasets.backends.sql.query import SqlQueryBuilder
from spinta.datasets.keymaps.components import KeyMap
from spinta.datasets.utils import iterparams
from spinta.manifests.components import Manifest
from spinta.types.datatype import PrimaryKey
from spinta.types.datatype import Ref

log = logging.getLogger(__name__)


@commands.load.register(Context, Sql, RawConfig)
def load(context: Context, backend: Sql, rc: RawConfig):
    dsn = rc.get('backends', backend.name, 'dsn', required=True)
    schema = rc.get('backends', backend.name, 'schema')
    backend.engine = sa.create_engine(dsn, echo=False)
    backend.schema = sa.MetaData(backend.engine, schema=schema)
    backend.dbschema = schema


@commands.wait.register(Context, Sql)
def wait(context: Context, backend: Sql, *, fail: bool = False) -> bool:
    rc = context.get('rc')
    dsn = rc.get('backends', backend.name, 'dsn', required=True)
    engine = sa.create_engine(dsn)
    try:
        conn = engine.connect()
    except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.DBAPIError):
        if fail:
            raise
        else:
            return False
    else:
        conn.close()
        engine.dispose()
        return True


@commands.prepare.register(Context, Sql, Manifest)
def prepare(context: Context, backend: Sql, manifest: Manifest):
    # XXX: Moved reflection to spinta/datasets/backends/sql/components:Sql.get_table
    # log.info(f"Reflecting database for {backend.name!r} backend, this might take time...")
    # backend.schema.reflect()
    pass


@commands.bootstrap.register(Context, Sql)
def bootstrap(context: Context, backend: Sql):
    pass


def _get_row_value(row: RowProxy, sel: Any) -> Any:
    if isinstance(sel, Selected):
        # TODO: `sel.prep is not na`.
        if sel.prep is not None:
            return _get_row_value(row, sel.prep)
        else:
            return row[sel.item]
    if isinstance(sel, tuple):
        return tuple(_get_row_value(row, v) for v in sel)
    if isinstance(sel, list):
        return [_get_row_value(row, v) for v in sel]
    if isinstance(sel, dict):
        return {k: _get_row_value(row, v) for k, v in sel.items()}
    if isinstance(sel, Expr):
        # Value preparation is not yet implemented.
        raise NotImplemented
    return sel


@commands.getall.register(Context, Model, Sql)
def getall(
    context: Context,
    model: Model,
    backend: Sql,
    *,
    query: Expr = None,
):
    conn = context.get(f'transaction.{backend.name}')
    builder = SqlQueryBuilder(context)
    builder.update(model=model)

    if model.external.prepare:
        # Join user passed query with query set in manifest.
        prepare = model.external.prepare
        if query:
            if query.name == 'and' and prepare.name == 'and':
                query.args = query.args + prepare.args
            elif query.name == 'and':
                query.args = query.args + (prepare,)
            elif prepare.name == 'and':
                query = Expr('and', query, *prepare.args)
            else:
                query = Expr('and', query, prepare)
        else:
            query = prepare

    keymap: KeyMap = context.get(f'keymap.{model.keymap.name}')

    for params in iterparams(model):
        table = model.external.name.format(**params)
        table = backend.get_table(model, table)

        env = builder.init(backend, table)
        expr = env.resolve(query)
        where = env.execute(expr)
        qry = env.build(where)

        for row in conn.execute(qry):
            res = {
                '_type': model.model_type(),
            }
            for key, sel in env.selected.items():
                val = _get_row_value(row, sel)
                if sel.prop:
                    if isinstance(sel.prop.dtype, PrimaryKey):
                        val = keymap.encode(sel.prop.model.model_type(), val)
                    elif isinstance(sel.prop.dtype, Ref):
                        val = keymap.encode(sel.prop.dtype.model.model_type(), val)
                        val = {'_id': val}
                res[key] = val
            res = commands.cast_backend_to_python(context, model, backend, res)
            yield res
