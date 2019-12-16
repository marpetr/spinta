import urllib.parse

from spinta import exceptions

RULES = {
    'path': {
        'minargs': 0,
    },
    'ns': {
        'maxargs': 0,
    },
    # Recursivelly return all objects under that namespace.
    'all': {
        'maxargs': 0,
    },
    'dataset': {
        'minargs': 1,
    },
    'resource': {
        'minargs': 1,
    },
    'origin': {
        'minargs': 1,
    },
    'changes': {
        'minargs': 0,
        'maxargs': 1,
    },
    'format': {
        'maxargs': 1,
    },
    # In batch requests, return summary of what was done.
    'summary': {
        'maxargs': 0,
    },
    # In batch requests, continue execution even if some actions fail.
    'fault-tolerant': {
        'maxargs': 0,
    },
    # Wipe all data of a model or all models in a namespace.
    'wipe': {
        'maxargs': 0,
    },
}


def apply_query_rules(RULES, params):
    for param in params:
        name = param['name']
        args = param['args']

        if name not in RULES:
            raise exceptions.UnknownRequestParameter(name=name)

        rules = RULES[name]
        maxargs = rules.get('maxargs')
        minargs = rules.get('minargs', 0 if maxargs == 0 else 1)
        if len(args) < minargs:
            # FIXME: This should be an UserError.
            raise Exception(f"At least {minargs} argument is required for {name!r} URL parameter.")

        if maxargs is not None and len(args) > maxargs:
            # FIXME: This should be an UserError.
            raise Exception(f"URL parameter {name!r} can only have {maxargs} arguments.")
    return params


def parse_url_path(path):
    query = []
    name = None if path.startswith(':') else 'path'
    args = []
    parts = map(urllib.parse.unquote, path.split('/')) if path else []
    for part in parts:
        if part.startswith(':'):
            if name is not None:
                query.append({
                    'name': name,
                    'args': args,
                })
            name = part[1:]
            args = []
        else:
            args.append(part)
    query.append({
        'name': name,
        'args': args,
    })
    apply_query_rules(RULES, query)
    return query


def build_url_path(query):
    parts = []
    for param in query:
        name = param['name']
        args = param['args']
        if name == 'path':
            parts.extend(args)
        else:
            parts.extend([f':{name}'] + args)
    return '/'.join(map(str, parts))
