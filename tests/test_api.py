import os
import json
import shutil

from mock import patch

from betty.conf.app import settings
from betty.cropper.models import Image

TEST_DATA_PATH = os.path.join(os.path.dirname(__file__), 'images')


import pytest


def test_no_api_key(client):
    res = client.post('/images/api/new')
    assert res.status_code == 403

    res = client.get('/images/api/1')
    assert res.status_code == 403

    res = client.post('/images/api/1/1x1')
    assert res.status_code == 403

    res = client.post('/images/api/1', REQUEST_METHOD="PATCH")
    assert res.status_code == 403

    res = client.get('/images/api/search')
    assert res.status_code == 403


@pytest.mark.django_db
def test_image_upload(admin_client):

    lenna_path = os.path.join(TEST_DATA_PATH, 'Lenna.png')
    with open(lenna_path, "rb") as lenna:
        data = {"image": lenna, "name": "LENNA DOT PNG", "credit": "Playboy"}
        res = admin_client.post('/images/api/new', data)
    assert res.status_code == 200
    response_json = json.loads(res.content.decode("utf-8"))
    del response_json["selections"]  # We don't care about selections in this test
    assert response_json == {
        "id": 1,
        "name": "LENNA DOT PNG",
        "credit": "Playboy",
        "height": 512,
        "width": 512
    }

    image = Image.objects.get(id=response_json['id'])
    assert os.path.exists(image.path())
    assert os.path.exists(image.source.path)
    assert os.path.exists(image.optimized.path)
    assert os.path.basename(image.source.path) == "Lenna.png"
    assert image.name == "LENNA DOT PNG"
    assert image.credit == "Playboy"


@pytest.mark.django_db
def test_update_selection(admin_client):

    image = Image.objects.create(name="Testing", width=512, height=512)

    new_selection = {
        "x0": 1,
        "y0": 1,
        "x1": 510,
        "y1": 510
    }

    res = admin_client.post(
        "/images/api/{0}/1x1".format(image.id),
        data=json.dumps(new_selection),
        content_type="application/json",
    )
    assert res.status_code == 200

    image = Image.objects.get(id=image.id)
    assert new_selection == image.selections['1x1']

    res = admin_client.post(
        "/images/api/{0}/original".format(image.id),
        data=json.dumps(new_selection),
        content_type="application/json",
    )
    assert res.status_code == 400

    bad_selection = {
        'x0': 1,
        'x1': 510
    }
    res = admin_client.post(
        "/images/api/{0}/1x1".format(image.id),
        data=json.dumps(bad_selection),
        content_type="application/json",
    )
    assert res.status_code == 400

    res = admin_client.post(
        "/images/api/1000001/1x1",
        data=json.dumps(bad_selection),
        content_type="application/json",
    )
    assert res.status_code == 404


@pytest.mark.django_db
def test_image_selection_source(admin_client):
    image = Image.objects.create(name="Testing", width=512, height=512)
    image.selections = {"1x1": {"x0": 1, "y0": 1, "x1": 510, "y1": 510}}
    image.save()

    res = admin_client.get("/images/api/{0}".format(image.id))
    assert res.status_code == 200
    data = json.loads(res.content.decode("utf-8"))
    assert data["selections"]["1x1"]["source"] == "user"
    assert data["selections"]["16x9"]["source"] == "auto"


@pytest.mark.django_db
def test_crop_clearing(admin_client):
    lenna_path = os.path.join(TEST_DATA_PATH, 'Lenna.png')
    with open(lenna_path, "rb") as lenna:
        data = {"image": lenna, "name": "LENNA DOT PNG", "credit": "Playboy"}
        res = admin_client.post('/images/api/new', data)
    assert res.status_code == 200

    response_json = json.loads(res.content.decode("utf-8"))
    image_id = response_json['id']

    # Now let's generate a couple crops
    admin_client.get("/images/{}/1x1/240.jpg".format(image_id))
    admin_client.get("/images/{}/16x9/640.png".format(image_id))

    image = Image.objects.get(id=image_id)

    assert os.path.exists(os.path.join(image.path(), "1x1", "240.jpg"))
    assert os.path.exists(os.path.join(image.path(), "16x9", "640.png"))

    # Now we update the selection
    new_selection = {
        "x0": 1,
        "y0": 1,
        "x1": 510,
        "y1": 510
    }

    res = admin_client.post(
        "/images/api/{0}/1x1".format(image_id),
        data=json.dumps(new_selection),
        content_type="application/json",
    )
    assert res.status_code == 200

    # Let's make sure that the crops got removed
    assert not os.path.exists(os.path.join(image.path(), "1x1", "240.jpg"))
    assert os.path.exists(os.path.join(image.path(), "16x9", "640.png"))


@pytest.mark.django_db
def test_image_delete(admin_client):
    image = Image.objects.create(name="Testing", width=512, height=512)
    path = image.path()  # Save path before deletion

    res = admin_client.get("/images/api/{0}".format(image.id))
    assert res.status_code == 200

    with patch('betty.cropper.models.settings.BETTY_CACHE_FLUSHER') as mock_flusher:
        with patch('shutil.rmtree') as mock_rmtree:
            res = admin_client.post(
                "/images/api/{0}".format(image.id),
                content_type="application/json",
                REQUEST_METHOD="DELETE",
            )
            assert res.status_code == 200
            assert not Image.objects.filter(id=image.id)
            mock_flusher.assert_called_with('/images/1/16x9/640.png')
            mock_rmtree.assert_called_with(path, ignore_errors=True)


@pytest.mark.django_db
def test_image_delete_invalid_id(admin_client):
    res = admin_client.post(
        "/images/api/{0}".format(101),
        content_type="application/json",
        REQUEST_METHOD="DELETE",
    )
    assert res.status_code == 404


@pytest.mark.django_db
def test_image_detail(admin_client):
    image = Image.objects.create(name="Testing", width=512, height=512)

    res = admin_client.get("/images/api/{0}".format(image.id))
    assert res.status_code == 200

    res = admin_client.post(
        "/images/api/{0}".format(image.id),
        data=json.dumps({"name": "Updated"}),
        content_type="application/json",
        REQUEST_METHOD="PATCH",
    )
    assert res.status_code == 200

    image = Image.objects.get(id=image.id)
    assert image.name == "Updated"


def test_image_search(admin_client):
    image = Image.objects.create(name="BLERGH", width=512, height=512)

    res = admin_client.get('/images/api/search?q=blergh')
    assert res.status_code == 200
    results = json.loads(res.content.decode("utf-8"))
    assert len(results) == 1
    assert results["results"][0]["id"] == image.id


def test_bad_image_data(admin_client):
    shutil.rmtree(settings.BETTY_IMAGE_ROOT, ignore_errors=True)

    lenna_path = os.path.join(TEST_DATA_PATH, 'Lenna.png')
    with open(lenna_path, "rb") as lenna:
        res = admin_client.post('/images/api/new', {"image": lenna})

    assert res.status_code == 200
    response_json = json.loads(res.content.decode("utf-8"))
    assert response_json.get("name") == "Lenna.png"
    assert response_json.get("width") == 512
    assert response_json.get("height") == 512

    # Now that the image is uploaded, let's fuck up the data.
    image = Image.objects.get(id=response_json['id'])
    image.width = 1024
    image.height = 1024
    image.save()

    id_string = ""
    for index, char in enumerate(str(image.id)):
        if index % 4 == 0:
            id_string += "/"
        id_string += char
    res = admin_client.get('/images/{0}/1x1/400.jpg'.format(id_string))
    assert res.status_code == 200
