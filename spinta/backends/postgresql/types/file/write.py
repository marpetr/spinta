import cgi

from starlette.requests import Request

from spinta import commands
from spinta.backends.fs.components import FileSystem
from spinta.utils.aiotools import aiter
from spinta.utils.data import take
from spinta.renderer import render
from spinta.components import Context, Action, UrlParams, DataItem
from spinta.types.datatype import DataType, File
from spinta.commands.write import prepare_patch, simple_response, validate_data
from spinta.components import Context, DataSubItem
from spinta.backends.components import Backend
from spinta.backends.postgresql.files import DatabaseFile
from spinta.backends.postgresql.constants import TableType
from spinta.backends.postgresql.components import PostgreSQL


@commands.push.register(Context, Request, File, PostgreSQL)
async def push(
    context: Context,
    request: Request,
    dtype: File,
    backend: PostgreSQL,
    *,
    action: Action,
    params: UrlParams,
):
    if params.propref:
        return await push[type(context), Request, DataType, type(backend)](
            context, request, dtype, backend,
            action=action,
            params=params,
        )

    prop = dtype.prop

    # XXX: This command should just prepare AsyncIterator[DataItem] and call
    #      push_stream or something like that. Now I think this command does
    #      too much work.

    commands.authorize(context, action, prop)

    data = DataItem(
        prop.model,
        prop,
        propref=False,
        backend=backend,
        action=action
    )

    if action == Action.DELETE:
        data.given = {
            prop.name: {
                '_id': None,
                '_content_type': None,
                '_content': None,
            }
        }
    else:
        data.given = {
            prop.name: {
                '_content_type': request.headers.get('content-type'),
                '_content': await request.body(),
            }
        }
        if 'Content-Disposition' in request.headers:
            _, cdisp = cgi.parse_header(request.headers['Content-Disposition'])
            if 'filename' in cdisp:
                data.given[prop.name]['_id'] = cdisp['filename']

    if 'Revision' in request.headers:
        data.given['_revision'] = request.headers['Revision']

    commands.simple_data_check(context, data, data.prop, data.model.backend)

    data.saved = commands.getone(context, prop, dtype, prop.model.backend, id_=params.pk)

    dstream = aiter([data])
    dstream = validate_data(context, dstream)
    dstream = prepare_patch(context, dstream)

    if action in (Action.UPDATE, Action.PATCH, Action.DELETE):
        dstream = commands.update(context, prop, dtype, prop.model.backend, dstream=dstream)
        dstream = commands.create_changelog_entry(
            context, prop.model, prop.model.backend, dstream=dstream,
        )

    elif action == Action.DELETE:
        dstream = commands.delete(context, prop, dtype, prop.model.backend, dstream=dstream)
        dstream = commands.create_changelog_entry(
            context, prop.model, prop.model.backend, dstream=dstream,
        )

    else:
        raise Exception(f"Unknown action {action!r}.")

    status_code, response = await simple_response(context, dstream)
    return render(context, request, prop, params, response, status_code=status_code)


@commands.before_write.register(Context, File, PostgreSQL)
def before_write(  # noqa
    context: Context,
    dtype: File,
    backend: PostgreSQL,
    *,
    data: DataSubItem,
):
    content = take('_content', data.patch)
    if isinstance(content, bytes) and isinstance(dtype.backend, PostgreSQL):
        transaction = context.get('transaction')
        connection = transaction.connection
        prop = dtype.prop
        table = backend.get_table(prop, TableType.FILE)
        with DatabaseFile(connection, table, mode='w') as f:
            f.write(data.patch['_content'])
            data.patch['_size'] = f.size
            data.patch['_blocks'] = f.blocks
            data.patch['_bsize'] = f.bsize
    elif isinstance(content, bytes) and isinstance(dtype.backend, FileSystem):
        filepath = dtype.backend.path / data.given['_id']
        with open(filepath, 'wb') as f:
            f.write(content)
    return commands.before_write[type(context), File, Backend](
        context,
        dtype,
        backend,
        data=data,
    )
