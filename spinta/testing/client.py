from typing import Optional, List, Union

import datetime

import pprintpp as pprint
import requests
import starlette.testclient

from spinta import auth
from spinta import commands
from spinta import api
from spinta.components import Context
from spinta.core.config import RawConfig
from spinta.testing.context import create_test_context


def create_test_client(rc_or_context: Union[RawConfig, Context]):
    if isinstance(rc_or_context, RawConfig):
        rc = rc_or_context
        context = create_test_context(rc, name='pytest/client')
    else:
        context = rc_or_context
    if not context.loaded:
        context.load()
    app = api.init(context)
    return TestClient(context, app, base_url='https://testserver')


class TestClient(starlette.testclient.TestClient):

    def __init__(self, context, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._spinta_context = context
        self._requests_session = None
        self._requests_session_base_url = None
        self._scopes = []

    def start_session(self, base_url):
        self._requests_session = requests.Session()
        self._requests_session_base_url = base_url.rstrip('/')

    def authmodel(self, model: str, actions: List[str], creds=None):
        scopes = commands.get_model_scopes(self._spinta_context, model, actions)
        self.authorize(scopes, creds=creds)

    def authorize(self, scopes: Optional[list] = None, creds=None):
        # Calling `authorize` multiple times, will preserve previous scopes.
        self._scopes += [s for s in (scopes or []) if s not in self._scopes]

        if creds:
            # Request access token using /auth/token endpoint.
            resp = self.request('POST', '/auth/token', auth=creds, data={
                'grant_type': 'client_credentials',
                'scope': ' '.join(self._scopes),
            })
            assert resp.status_code == 200, resp.text
            token = resp.json()['access_token']
        else:
            # Create access token using private key.
            context = self._spinta_context
            private_key = auth.load_key(context, auth.KeyType.private)
            client = 'test-client'
            expires_in = int(datetime.timedelta(days=10).total_seconds())
            token = auth.create_access_token(context, private_key, client, expires_in, scopes=self._scopes)

        if self._requests_session:
            session = self._requests_session
        else:
            session = self

        session.headers.update({
            'Authorization': f'Bearer {token}'
        })

    def request(self, method: str, url: str, *args, **kwargs):
        if self._requests_session:
            url = self._requests_session_base_url + url
            return self._requests_session.request(method, url, *args, **kwargs)
        else:
            return super().request(method, url, *args, **kwargs)

    def getdata(self, *args, **kwargs):
        resp = self.get(*args, **kwargs)
        assert resp.status_code == 200, f'status_code: {resp.status_code}, response: {resp.text}'
        resp = resp.json()
        assert '_data' in resp, pprint.pformat(resp)
        return resp['_data']
