import os.path
from django.test import TestCase
from unittest.mock import patch
import json

from .models import Manifest, Canvas, IIIFImage, IIIFPresentation

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')

class TestManifest(TestCase):

    def test_str(self):
        # no label - short id is used
        book = Manifest(short_id='bk123')
        assert str(book) == 'bk123'
        book.label = 'An item'
        assert str(book) == 'An item'


class TestCanvas(TestCase):

    def test_str(self):
        manif = Manifest(short_id='bk123', label='Book 1')
        page = Canvas(manifest=manif, label='Image 1', short_id='pg123', order=1)
        assert str(page) == '%s %d (%s)' % (str(manif), page.order + 1, page.label)

        page.thumbnail = True
        assert str(page).endswith('*')

    def test_image(self):
        img_service = 'https://images.co'
        img_id = 'some-file.jp2'

        page = Canvas(iiif_image_id='/'.join([img_service, img_id]))
        assert isinstance(page.image, IIIFImage)
        assert page.image.api_endpoint == img_service
        assert page.image.image_id == img_id


class TestIIIFPresentation(TestCase):
    test_manifest = os.path.join(FIXTURE_DIR, 'chto-manifest.json')

    def test_from_file(self):
        pres = IIIFPresentation.from_file(self.test_manifest)
        assert isinstance(pres, IIIFPresentation)
        assert pres.type == 'sc:Manifest'

    def test_from_url(self):
        manifest_url = 'http://ma.ni/fe.st'
        with open(self.test_manifest) as manifest:
            data = json.loads(manifest.read())
        with patch('djiffy.models.requests') as mockrequests:
            mockrequests.get.return_value.json.return_value = data
            pres = IIIFPresentation.from_url(manifest_url)
            assert pres.type == 'sc:Manifest'
            mockrequests.get.assert_called_with(manifest_url)
            mockrequests.get.return_value.json.assert_called_with()

    def test_from_url_or_file(self):
        with patch.object(IIIFPresentation, 'from_url') as mock_from_url:
            pres = IIIFPresentation.from_file_or_url(self.test_manifest)
            assert pres.type == 'sc:Manifest'
            mock_from_url.assert_not_called()

            pres = IIIFPresentation.from_file_or_url('http://mani.fe/st')
            mock_from_url.assert_called_with('http://mani.fe/st')

    def test_short_id(self):
        manifest_uri = 'https://ii.if/resources/p0c484h74c/manifest'
        assert IIIFPresentation.short_id(manifest_uri) == 'p0c484h74c'
        canvas_uri = 'https://ii.if/resources/p0c484h74c/manifest/canvas/ps7527b878'
        assert IIIFPresentation.short_id(canvas_uri) == 'ps7527b878'



    def test_toplevel_attrs(self):
        pres = IIIFPresentation.from_file(self.test_manifest)
        assert pres.context == "http://iiif.io/api/presentation/2/context.json"
        assert pres.id == "https://plum.princeton.edu/concern/scanned_resources/ph415q7581/manifest"
        assert pres.type == "sc:Manifest"
        assert pres.label[0] == "Chto my stroim : Tetrad\u02b9 s kartinkami"
        assert pres.viewingHint == "paged"
        assert pres.viewingDirection == "left-to-right"

    def test_nested_attrs(self):
        pres = IIIFPresentation.from_file(self.test_manifest)
        assert isinstance(pres.sequences, tuple)
        assert pres.sequences[0].id == \
            "https://plum.princeton.edu/concern/scanned_resources/ph415q7581/manifest/sequence/normal"
        assert pres.sequences[0].type == "sc:Sequence"
        assert isinstance(pres.sequences[0].canvases, tuple)
        assert pres.sequences[0].canvases[0].id == \
            "https://plum.princeton.edu/concern/scanned_resources/ph415q7581/manifest/canvas/p02871v98d"

    def test_set(self):
        pres = IIIFPresentation.from_file(self.test_manifest)
        pres.label = 'New title'
        pres.type = 'sc:Collection'
        assert pres.label == 'New title'
        assert pres.type == 'sc:Collection'

    def test_del(self):
        pres = IIIFPresentation.from_file(self.test_manifest)
        del pres.label
        del pres.type
        assert not hasattr(pres, 'label')
        assert not hasattr(pres, 'type')

