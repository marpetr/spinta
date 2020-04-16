from spinta import commands
from spinta.components import Context
from spinta.types.datatype import Array
from spinta.backends.postgresql.constants import TableType
from spinta.backends.postgresql.components import PostgreSQL


@commands.wipe.register()
def wipe(context: Context, dtype: Array, backend: PostgreSQL):
    wipe(context, dtype.items.dtype, backend)
    table = backend.get_table(dtype.prop, TableType.LIST)
    connection = context.get('transaction').connection
    connection.execute(table.delete())