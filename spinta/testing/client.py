import datetime

import pprintpp as pprint
import starlette.testclient

from spinta import auth


class TestClient(starlette.testclient.TestClient):

    def __init__(self, context, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._spinta_context = context

    def authorize(self, scopes=None):
        context = self._spinta_context
        context.load_if_not_loaded()
        private_key = auth.load_key(context, 'private.json')
        client_id = 'baa448a8-205c-4faa-a048-a10e4b32a136'
        client = auth.query_client(context, client_id)
        grant_type = 'client_credentials'
        expires_in = int(datetime.timedelta(days=10).total_seconds())
        token = auth.create_access_token(context, private_key, client, grant_type, expires_in, scopes=scopes)
        self.headers.update({'authorization': f'bearer {token}'})

    def request(self, *args, **kwargs):
        self._spinta_context.load_if_not_loaded()
        return super().request(*args, **kwargs)

    def getdata(self, *args, **kwargs):
        resp = self.get(*args, **kwargs)
        assert resp.status_code == 200, f'status_code: {resp.status_code}, response: {resp.text}'
        resp = resp.json()
        assert 'data' in resp, pprint.pformat(resp)
        return resp['data']
