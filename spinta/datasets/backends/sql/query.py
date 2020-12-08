from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import sqlalchemy as sa
import sqlalchemy.sql.functions

from spinta.auth import authorized
from spinta.components import Action
from spinta.components import Property
from spinta.core.ufuncs import Bind
from spinta.core.ufuncs import Env
from spinta.core.ufuncs import Expr
from spinta.core.ufuncs import Negative
from spinta.core.ufuncs import ufunc
from spinta.datasets.backends.sql.components import Sql
from spinta.exceptions import PropertyNotFound
from spinta.exceptions import UnknownExpr
from spinta.types.datatype import DataType
from spinta.types.datatype import PrimaryKey
from spinta.types.datatype import Ref
from spinta.utils.data import take


class ForeignProperty:
    """Representation of a reference.

    When querying `/city?select(country.code)`, `left` points to `country` and
    `right` points to `code`. `chain` will be:

        [
            ForeignProperty(country:Ref, code:String),
        ]

    Multiple references can be joined like this:

        /city?select(country.continent.planet.name)

    `chain` will look like this:

        [
            ForeignProperty(country:Ref, continent:Ref),
            ForeignProperty(continent:Ref, name:String),
        ]

    """

    left: Ref
    right: DataType
    chain: List[ForeignProperty]

    def __init__(
        self,
        fpr: Optional[ForeignProperty],
        left: Ref,
        right: Ref,
    ):
        if fpr is None:
            self.name = left.prop.place
            self.chain = [self]
        else:
            self.name += '->' + left.prop.place
            self.chain = fpr.chain + [self]

        self.left = left
        self.right = right

    def __repr__(self):
        return f'<{self.name}->{self.right.prop.name}:{self.right.prop.name}>'


class SqlFrom:
    backend: Sql
    joins: Dict[str, sa.Table]
    from_: sa.Table

    def __init__(self, backend: Sql, table: sa.Table):
        self.backend = backend
        self.joins = {}
        self.from_ = table

    def get_table(self, prop: ForeignProperty) -> sa.Table:
        fpr: Optional[ForeignProperty] = None
        for fpr in prop.chain:
            if fpr.name in self.joins:
                continue

            ltable = self.backend.get_table(fpr.left.prop.model)
            lrkeys = [self.backend.get_column(ltable, fpr.left.prop)]

            rmodel = fpr.right.prop.model
            rtable = self.backend.get_table(rmodel)
            rpkeys = []
            for rpk in fpr.left.refprops:
                if isinstance(rpk.dtype, PrimaryKey):
                    rpkeys += [
                        self.backend.get_column(rtable, rpk)
                        for rpk in rmodel.external.pkeys
                    ]
                else:
                    rpkeys += [
                        self.backend.get_column(rtable, rpk)
                    ]

            assert len(lrkeys) == len(rpkeys), (lrkeys, rpkeys)
            condition = []
            for lrk, rpk in zip(lrkeys, rpkeys):
                condition += [lrk == rpk]

            assert len(condition) > 0
            if len(condition) == 1:
                condition = condition[0]
            else:
                condition = sa.and_(condition)

            self.from_ = self.joins[fpr.name] = self.from_.join(rtable,
                                                                condition)

        model = fpr.right.prop.model
        table = self.backend.get_table(model)
        return table


class SqlQueryBuilder(Env):
    backend: Sql
    table: sa.Table
    joins: SqlFrom
    columns: List[sa.Column]
    # `resolved` is used to map which prop.place properties are already
    # resolved, usually it maps to Selected, but different DataType's can return
    # different results.
    resolved: Dict[str, Selected]
    selected: Dict[str, Selected] = None

    def init(self, backend: Sql, table: sa.Table):
        return self(
            backend=backend,
            table=table,
            columns=[],
            resolved={},
            selected=None,
            joins=SqlFrom(backend, table),
            sort=[],
            limit=None,
            offset=None,
        )

    def build(self, where):
        if self.selected is None:
            # If select list was not explicitly given by client, then select all
            # properties.
            self.call('select', Expr('select'))

        qry = sa.select(self.columns)
        qry = qry.select_from(self.joins.from_)

        if where is not None:
            qry = qry.where(where)

        if self.sort:
            qry = qry.order_by(*self.sort)

        if self.limit is not None:
            qry = qry.limit(self.limit)

        if self.offset is not None:
            qry = qry.offset(self.offset)

        return qry

    def default_resolver(self, expr, *args, **kwargs):
        raise UnknownExpr(expr=str(expr(*args, **kwargs)), name=expr.name)

    def add_column(self, column: sa.Column) -> int:
        if column not in self.columns:
            self.columns.append(column)
        return self.columns.index(column)


class Selected:
    # Item index in select list.
    item: int = None
    # Model property if a property is selected.
    prop: Property = None
    # A value or a an Expr for further processing on selected value.
    # TODO: Probably default `prep` value should be `na`.
    prep: Any = None

    def __init__(
        self,
        item: int = None,
        prop: Property = None,
        # `prop` can be Expr or any other value.
        # TODO: Probably default `prep` value should be `na`.
        prep: Any = None,
    ):
        self.item = item
        self.prop = prop
        self.prep = prep


@ufunc.resolver(SqlQueryBuilder, Bind, Bind, name='getattr')
def getattr_(env: SqlQueryBuilder, field: Bind, attr: Bind):
    prop = env.model.properties[field.name]
    return env.call('getattr', prop.dtype, attr)


@ufunc.resolver(SqlQueryBuilder, Ref, Bind, name='getattr')
def getattr_(env: SqlQueryBuilder, dtype: Ref, attr: Bind) -> ForeignProperty:
    prop = dtype.model.properties[attr.name]
    return ForeignProperty(None, dtype, prop.dtype)


@ufunc.resolver(SqlQueryBuilder, str, object)
def eq(env: SqlQueryBuilder, field: str, value: Any):
    # XXX: Backwards compatible resolver, `str` arguments are deprecated.
    prop = env.model.properties[field]
    column = env.backend.get_column(env.table, prop)
    return column == value


@ufunc.resolver(SqlQueryBuilder, Bind, object)
def eq(env: SqlQueryBuilder, field: Bind, value: Any):
    prop = env.model.properties[field.name]
    column = env.backend.get_column(env.table, prop)
    return column == value


@ufunc.resolver(SqlQueryBuilder, ForeignProperty, object)
def eq(env: SqlQueryBuilder, fpr: ForeignProperty, value: Any):
    table = env.joins.get_table(fpr)
    column = env.backend.get_column(table, fpr.right.prop)
    return column == value


@ufunc.resolver(SqlQueryBuilder, ForeignProperty, list)
def eq(env: SqlQueryBuilder, fpr: ForeignProperty, value: list):
    table = env.joins.get_table(fpr)
    column = env.backend.get_column(table, fpr.right.prop)
    return column.in_(value)


@ufunc.resolver(SqlQueryBuilder, sqlalchemy.sql.functions.Function, object)
def eq(
    env: SqlQueryBuilder,
    func: sqlalchemy.sql.functions.Function,
    value: Any,
):
    return func == value


@ufunc.resolver(SqlQueryBuilder, str, object)
def ne(env: SqlQueryBuilder, field: str, value: Any):
    # XXX: Backwards compatible resolver, `str` arguments are deprecated.
    prop = env.model.properties[field]
    column = env.backend.get_column(env.table, prop)
    return column != value


@ufunc.resolver(SqlQueryBuilder, Bind, object)
def ne(env: SqlQueryBuilder, field: Bind, value: Any):
    prop = env.model.properties[field.name]
    column = env.backend.get_column(env.table, prop)
    return column != value


@ufunc.resolver(SqlQueryBuilder, ForeignProperty, object)
def ne(env: SqlQueryBuilder, fpr: ForeignProperty, value: Any):
    table = env.joins.get_table(fpr)
    column = env.backend.get_column(table, fpr.right.prop)
    return column != value


@ufunc.resolver(SqlQueryBuilder, str, list)
def ne(env: SqlQueryBuilder, field: str, value: List[Any]):
    # XXX: Backwards compatible resolver, `str` arguments are deprecated.
    prop = env.model.properties[field]
    column = env.backend.get_column(env.table, prop)
    return ~column.in_(value)


@ufunc.resolver(SqlQueryBuilder, Bind, list)
def ne(env: SqlQueryBuilder, field: Bind, value: List[Any]):
    prop = env.model.properties[field.name]
    column = env.backend.get_column(env.table, prop)
    return ~column.in_(value)


@ufunc.resolver(SqlQueryBuilder, ForeignProperty, list)
def ne(env: SqlQueryBuilder, fpr: ForeignProperty, value: List[Any]):
    table = env.joins.get_table(fpr)
    column = env.backend.get_column(table, fpr.right.prop)
    return ~column.in_(value)


@ufunc.resolver(SqlQueryBuilder, Expr, name='and')
def and_(env: SqlQueryBuilder, expr: Expr):
    args, kwargs = expr.resolve(env)
    args = [a for a in args if a is not None]
    if len(args) > 1:
        return sa.and_(*args)
    elif args:
        return args[0]


@ufunc.resolver(SqlQueryBuilder, Expr, name='or')
def or_(env: SqlQueryBuilder, expr: Expr):
    args, kwargs = expr.resolve(env)
    args = [a for a in args if a is not None]
    if len(args) > 1:
        return sa.or_(*args)
    elif args:
        return args[0]


@ufunc.resolver(SqlQueryBuilder, Expr, name='list')
def list_(env: SqlQueryBuilder, expr: Expr) -> List[Any]:
    args, kwargs = expr.resolve(env)
    return list(args)


@ufunc.resolver(SqlQueryBuilder, Expr)
def testlist(env: SqlQueryBuilder, expr: Expr) -> Tuple[Any]:
    args, kwargs = expr.resolve(env)
    return tuple(args)


@ufunc.resolver(SqlQueryBuilder)
def count(env: SqlQueryBuilder):
    return sa.func.count()


@ufunc.resolver(SqlQueryBuilder, Expr)
def select(env: SqlQueryBuilder, expr: Expr):
    keys = [str(k) for k in expr.args]
    args, kwargs = expr.resolve(env)
    args = list(zip(keys, args)) + list(kwargs.items())

    if env.selected is not None:
        raise RuntimeError("`select` was already called.")

    env.selected = {}
    if args:
        for key, arg in args:
            env.selected[key] = env.call('select', arg)
    else:
        for prop in take(['_id', all], env.model.properties).values():
            if authorized(env.context, prop, Action.GETALL):
                env.selected[prop.place] = env.call('select', prop)

    if not env.columns:
        raise RuntimeError(
            f"{expr} didn't added anything to select list."
        )


@ufunc.resolver(SqlQueryBuilder, object)
def select(env: SqlQueryBuilder, value: Any) -> Selected:
    """For things like select(1, count())."""
    return Selected(item=env.add_column(value))


@ufunc.resolver(SqlQueryBuilder, Bind)
def select(env: SqlQueryBuilder, item: Bind):
    prop = _get_property_for_select(env, item.name)
    return env.call('select', prop)


@ufunc.resolver(SqlQueryBuilder, str)
def select(env: SqlQueryBuilder, item: str):
    # XXX: Backwards compatible resolver, `str` arguments are deprecated.
    prop = _get_property_for_select(env, item)
    return env.call('select', prop)


def _get_property_for_select(env: SqlQueryBuilder, name: str) -> Property:
    # TODO: `name` can refer to (in specified order):
    #       - var - a defined variable
    #       - param - a parameter if parametrization is used
    #       - item - an item of a dict or list
    #       - prop - a property
    #       Currently only `prop` is resolved.
    prop = env.model.flatprops.get(name)
    if prop and authorized(env.context, prop, Action.SEARCH):
        return prop
    else:
        raise PropertyNotFound(env.model, property=name)


@ufunc.resolver(SqlQueryBuilder, Property)
def select(env: SqlQueryBuilder, prop: Property) -> Selected:
    if prop.place not in env.resolved:
        if isinstance(prop.external, list):
            raise ValueError("Source can't be a list, use prepare instead.")
        # TODO: Probably here we should check if `prepare is not NA`. Because
        #       prepare could be set to None by user.
        if prop.external is None:
            pass
        if prop.external.prepare is not None:
            if isinstance(prop.external.prepare, Expr):
                result = env(this=prop).resolve(prop.external.prepare)
                result = env.call('select', result)
            else:
                result = prop.external.prepare
            result = Selected(prop=prop, prep=result)
        else:
            # If prepare is not given, then take value from `source`.
            result = env.call('select', prop.dtype)
            assert isinstance(result, Selected), prop
        env.resolved[prop.place] = result
    return env.resolved[prop.place]


@ufunc.resolver(SqlQueryBuilder, DataType)
def select(env: SqlQueryBuilder, dtype: DataType) -> Selected:
    table = env.backend.get_table(env.model)
    column = env.backend.get_column(table, dtype.prop, select=True)
    return Selected(
        item=env.add_column(column),
        prop=dtype.prop,
    )


@ufunc.resolver(SqlQueryBuilder, PrimaryKey)
def select(
    env: SqlQueryBuilder,
    dtype: PrimaryKey,
) -> Selected:
    model = dtype.prop.model
    pkeys = model.external.pkeys

    if not pkeys:
        # If primary key is not specified use all properties to uniquely
        # identify row.
        pkeys = take(model.properties).values()

    if len(pkeys) == 1:
        prop = pkeys[0]
        result = env.call('select', prop)
    else:
        result = [
            env.call('select', prop)
            for prop in pkeys
        ]
    return Selected(prop=dtype.prop, prep=result)


@ufunc.resolver(SqlQueryBuilder, list)
def select(
    env: SqlQueryBuilder,
    prep: List[Any],
) -> List[Any]:
    return [env.call('select', v) for v in prep]


@ufunc.resolver(SqlQueryBuilder, tuple)
def select(
    env: SqlQueryBuilder,
    prep: Tuple[Any],
) -> Tuple[Any]:
    return tuple(env.call('select', v) for v in prep)


@ufunc.resolver(SqlQueryBuilder, Bind, name='len')
def len_(env: SqlQueryBuilder, bind: Bind):
    prop = env.model.flatprops[bind.name]
    return env.call('len', prop.dtype)


@ufunc.resolver(SqlQueryBuilder, str, name='len')
def len_(env: SqlQueryBuilder, bind: str):
    # XXX: Backwards compatible resolver, `str` arguments are deprecated.
    prop = env.model.flatprops[bind]
    return env.call('len', prop.dtype)


@ufunc.resolver(SqlQueryBuilder, DataType, name='len')
def len_(env: SqlQueryBuilder, dtype: DataType):
    column = env.backend.get_column(env.table, dtype.prop)
    return sa.func.length(column)


@ufunc.resolver(SqlQueryBuilder, Expr)
def sort(env: SqlQueryBuilder, expr: Expr):
    args, kwargs = expr.resolve(env)
    env.sort = []
    for key in args:
        prop = env.model.properties[key.name]
        column = env.backend.get_column(env.table, prop)
        if isinstance(key, Negative):
            column = column.desc()
        else:
            column = column.asc()
        env.sort.append(column)


@ufunc.resolver(SqlQueryBuilder, int)
def limit(env: SqlQueryBuilder, n: int):
    env.limit = n


@ufunc.resolver(SqlQueryBuilder, int)
def offset(env: SqlQueryBuilder, n: int):
    env.offset = n
