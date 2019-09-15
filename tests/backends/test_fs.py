import pathlib

from spinta.testing.utils import get_error_codes, get_error_context


def test_crud(app):
    app.authorize([
        'spinta_photo_insert',
        'spinta_photo_update',
        'spinta_photo_image_update',
        'spinta_photo_patch',
        'spinta_photo_delete',
        'spinta_photo_getone',
        'spinta_photo_image_getone',
        'spinta_photo_image_delete',
    ])

    # Create a new photo resource.
    resp = app.post('/photos', json={
        'type': 'photo',
        'name': 'myphoto',
    })
    assert resp.status_code == 201, resp.text
    id_ = resp.json()['id']

    # PUT image to just create photo resource.
    resp = app.put(f'/photos/{id_}/image', data=b'BINARYDATA', headers={
        'content-type': 'image/png',
        # TODO: with content-disposition header it is possible to specify file
        #       name directly, but there should be option, to use model id as a
        #       file name, but that is currently not implemented.
        'content-disposition': 'attachment; filename="myimg.png"',
    })
    assert resp.status_code == 200, resp.text

    resp = app.get(f'/photos/{id_}')
    assert resp.json() == {
        'type': 'photo',
        'id': id_,
        'revision': resp.json()['revision'],
        'name': 'myphoto',
    }

    resp = app.get(f'/photos/{id_}/image:ref')
    assert resp.json() == {
        'content_type': 'image/png',
        'filename': 'myimg.png',
    }

    resp = app.get(f'/photos/{id_}/image')
    assert resp.content == b'BINARYDATA'

    print('============================')
    resp = app.delete(f'/photos/{id_}/image')
    assert resp.status_code == 200, resp.text
    assert resp.json() is None

    resp = app.get(f'/photos/{id_}/image:ref')
    assert resp.status_code == 200
    assert resp.json() is None

    resp = app.get(f'/photos/{id_}/image')
    assert resp.status_code == 404
    assert get_error_codes(resp.json()) == ["ResourceNotFound"]
    assert get_error_context(resp.json(), "ResourceNotFound") == {
        'schema': 'tests/manifest/models/photos.yml',
        'manifest': 'default',
        'model': 'photo',
        'property': 'image',
        'id': id_,
    }

    resp = app.get(f'/photos/{id_}')
    assert resp.json() == {
        'id': id_,
        'name': 'myphoto',
        'revision': resp.json()['revision'],
        'type': 'photo',
    }


def test_add_existing_file(app, tmpdir):
    app.authorize([
        'spinta_photo_insert',
        'spinta_photo_image_getone',
        'spinta_photo_image_patch',
    ])

    image = pathlib.Path(tmpdir) / 'image.png'
    image.write_bytes(b'IMAGEDATA')

    resp = app.post('/photos', json={
        'type': 'photo',
        'name': 'myphoto',
        'image': {
            'content_type': 'image/png',
            'filename': str(image),
        },
    })
    assert resp.status_code == 201, resp.text
    id_ = resp.json()['id']

    resp = app.patch(f'/photos/{id_}/image:ref', json={
        'content_type': 'image/png',
        'filename': str(image),
    })
    assert resp.status_code == 200

    resp = app.get(f'/photos/{id_}/image')
    assert resp.content == b'IMAGEDATA'


def test_add_missing_file(app, tmpdir):
    app.authorize([
        'spinta_photo_insert',
        'spinta_photo_getone',
    ])

    image = pathlib.Path(tmpdir) / 'missing.png'

    resp = app.post('/photos', json={
        'type': 'photo',
        'name': 'myphoto',
        'image': {
            'content_type': 'image/png',
            'filename': str(image),
        },
    })
    assert resp.status_code == 400, resp.text
    assert get_error_codes(resp.json()) == ["FileNotFound"]
    assert get_error_context(resp.json(), "FileNotFound") == {
        'schema': 'tests/manifest/models/photos.yml',
        'manifest': 'default',
        'model': 'photo',
        'property': 'image',
        'file': str(image),
    }


def test_add_missing_file_as_prop(app, tmpdir):
    app.authorize([
        'spinta_photo_insert',
        'spinta_photo_getone',
        'spinta_photo_image_update',
    ])

    resp = app.post('/photos', json={
        'type': 'photo',
        'name': 'myphoto',
    })
    id_ = resp.json()['id']

    image = pathlib.Path(tmpdir) / 'missing.png'
    resp = app.put(f'/photos/{id_}/image:ref', json={
        'content_type': 'image/png',
        'filename': str(image),
    })
    assert resp.status_code == 400, resp.text
    assert get_error_codes(resp.json()) == ["FileNotFound"]
    assert get_error_context(resp.json(), "FileNotFound") == {
        'schema': 'tests/manifest/models/photos.yml',
        'manifest': 'default',
        'model': 'photo',
        'property': 'image',
        'file': str(image),
    }


def test_id_as_filename(app, tmpdir):
    app.authorize([
        'spinta_photo_insert',
        'spinta_photo_getone',
        'spinta_photo_image_update',
        'spinta_photo_image_getone',
    ])

    resp = app.post('/photos', json={
        'type': 'photo',
        'name': 'myphoto',
    })
    id_ = resp.json()['id']

    resp = app.put(f'/photos/{id_}/image', data=b'BINARYDATA', headers={
        'content-type': 'image/png',
    })
    assert resp.status_code == 200, resp.text

    resp = app.get(f'/photos/{id_}/image:ref')
    assert resp.status_code == 200
    assert resp.json() == {
        'content_type': 'image/png',
        'filename': id_,
    }

    resp = app.get(f'/photos/{id_}/:show/name')
    assert resp.status_code == 200
    assert resp.json() == {
        'name': 'myphoto',
    }
