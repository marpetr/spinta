from typing import Iterator

from spinta import commands
from spinta.core.ufuncs import Expr
from spinta.components import Context
from spinta.components import Model
from spinta.typing import ObjectData
from spinta.backends.memory.components import Memory


@commands.getall.register(Context, Model, Memory)
def getall(
    context: Context,
    model: Model,
    backend: Memory,
    *,
    query: Expr = None,
) -> Iterator[ObjectData]:
    return backend.db[model.name].values()


@commands.getone.register(Context, Model, Memory)
def getone(
    context: Context,
    model: Model,
    backend: Memory,
    *,
    id_: str,
) -> ObjectData:
    return backend.db[model.name][id_]
