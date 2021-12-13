import os.path
from io import StringIO
import json
from unittest.mock import patch, Mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
import pytest
import rdflib
import requests

from .admin import ManifestSelectWidget
from .models import Manifest, Canvas, IIIFImage, IIIFPresentation, \
    IIIFException, get_iiif_url
from .importer import ManifestImporter

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')


@patch('djiffy.models.requests')
def test_get_iiif_url(mockrequests):
    # by default, no auth token
    test_url = 'http://example.com/id1/manifest'
    get_iiif_url(test_url)
    mockrequests.get.assert_called_with(test_url)

    # token specified, domain matches
    with override_settings(DJIFFY_AUTH_TOKENS={'example.com': 'testauth'}):
        get_iiif_url(test_url)
        mockrequests.get.assert_called_with(test_url,
            params={'auth_token': 'testauth'})

    # token specified, domain doesn't match
    with override_settings(DJIFFY_AUTH_TOKENS={'not.me': 'testauth'}):
        get_iiif_url(test_url)
        mockrequests.get.assert_called_with(test_url)


class TestManifest(TestCase):

    def test_str(self):
        # no label - short id is used
        book = Manifest(short_id='bk123')
        assert str(book) == 'bk123'
        book.label = 'An item'
        assert str(book) == 'An item'

    def test_absolute_url(self):
        book = Manifest(short_id='bk123')
        assert book.short_id in book.get_absolute_url()
        # FIXME: is this a useful test or too specific
        assert book.get_absolute_url() == '/iiif/%s/' % book.short_id

    def test_admin_thumbnail(self):
        book = Manifest.objects.create(short_id='bk123')
        assert book.admin_thumbnail() is None

        canv = Canvas.objects.create(short_id='pg12', thumbnail=True,
            manifest=book, order=1)
        assert book.admin_thumbnail() == canv.admin_thumbnail()

    def test_logo(self):
        book = Manifest(short_id='bk123')
        assert book.logo is None

        book.extra_data['logo'] = 'http://so.me/logo.img'
        assert book.logo == book.extra_data['logo']

    def test_license(self):
        book = Manifest(short_id='bk123')
        assert book.license is None

        book.extra_data['license'] = 'http://rightsstatements.org/vocab/InC/1.0/'
        assert book.license == book.extra_data['license']

    def test_rights_statement_id(self):
        book = Manifest(short_id='bk123')
        assert book.rights_statement_id is None

        book.extra_data['license'] = 'http://rightsstatements.org/vocab/InC/1.0/'
        assert book.rights_statement_id == 'InC'

    @patch('djiffy.models.requests')
    @patch('djiffy.models.rdflib')
    def test_license_label(self, mockrdflib, mockrequests):


        book = Manifest(short_id='bk123')
        # no license, no label
        assert book.license_label() is None
        # non http license, no label
        book.extra_data['license'] = 'foo://bar'
        assert book.license_label() is None

        # rightsstatement.org license
        book.extra_data['license'] = 'http://rightsstatements.org/vocab/NKC/1.0/'
        # simulate expected return: 303 to data url
        mockresponse = mockrequests.get.return_value
        mockresponse.status_code = 303
        mockresponse.headers = {'location': 'http://rightsstatements.org/vocab/NKC/1.0/'}
        mockrequests.codes = requests.codes

        # load fixture data into an rdflib graph and return via mockrdflib
        testgraph = rdflib.Graph()
        testgraph.parse(os.path.join(FIXTURE_DIR, 'rightsstatement_org_NKC.json'),
                        format='json-ld')
        mockrdflib.Graph.return_value = testgraph
        # use actual uriref method
        mockrdflib.URIRef = rdflib.URIRef
        with patch.object(testgraph, 'parse') as mockparse:
            label = book.license_label()
            assert label == 'No Known Copyright'
            mockrequests.get.assert_called_with(
                book.license, headers={'Accept': 'application/json'},
                allow_redirects=False)
            mockrdflib.Graph.assert_any_call()
            mockparse.assert_called_with(mockresponse.headers['location'],
                                         format='json-ld')

            # with language code
            label = book.license_label(lang='de')
            assert label == 'Kein Urheberrechtsschutz bekannt'

        # CC license
        book = Manifest(short_id='bk123')
        book.extra_data['license'] = 'http://creativecommons.org/licenses/by-nc-nd/3.0/'
        testgraph = rdflib.Graph()
        testgraph.parse(os.path.join(FIXTURE_DIR, 'cc_by_nc_nd.rdf'),
                        format='xml')
        mockrdflib.Graph.return_value = testgraph

        with patch.object(testgraph, 'parse') as mockparse:
            label = book.license_label()
            assert label == 'Attribution-NonCommercial-NoDerivs 3.0 Unported'

            # with language code
            label = book.license_label(lang='fr')
            assert label == 'Attribution - Pas d’Utilisation Commerciale - Pas de Modification 3.0 non transposé'

        # rights label in extra data
        mockrequests.reset_mock()
        mockrdflib.reset_mock()
        local_label = 'copyright status unknown'
        book.extra_data['seeAlso'] = {'edm_rights': {'pref_label': local_label}}
        label = book.license_label()
        assert label == local_label
        # should not call requests or use rdflib
        mockrequests.get.assert_not_called()
        mockrdflib.Graph.assert_not_called()

        # error handling - shouldn't blow up if there's an error
        book = Manifest(short_id='bk123')
        testgraph = rdflib.Graph()
        mockrdflib.Graph.return_value = testgraph
        book.extra_data['license'] = 'http://rightsstatements.org/vocab/NKC/1.0/'
        # exception on parse
        with patch.object(testgraph, 'parse') as mockparse:
            mockparse.side_effect = Exception
            assert book.license_label() is None

        # exception on request
        mockrequests.get.side_effect = Exception
        assert book.license_label() is None


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

    def test_plain_text_url(self):

        # individual dictionary
        extra_data = {
            'rendering': {
                '@id': 'http://some.org/with/text',
                'format': 'text/plain',
                'label': 'Download page text',
            }
        }

        page = Canvas(extra_data=extra_data)
        assert isinstance(page.plain_text_url, str)
        # plain text url returned
        assert page.plain_text_url == 'http://some.org/with/text'
        # dimensions not in extra data
        assert page.height is None
        assert page.width is None

        # with dimensions in extra data
        extra_data['width'] = 400
        extra_data['height'] = 300
        assert page.width == 400
        assert page.height == 300

        # no plain text url, returns None
        page.extra_data['rendering']['format'] = 'some/other-mime'
        assert page.plain_text_url is None

        # test with a list
        extra_data = {
            'rendering': [
                {'@id': 'http://some.org/pdf', 'format': 'application/pdf',
                    'label': 'View PDF image'},
                {'@id': 'http://some.org/with/text', 'format': 'text/plain',
                    'label': 'Download page text'},
            ]
        }
        # returns the correct text/plain version
        page = Canvas(extra_data=extra_data)
        assert isinstance(page.plain_text_url, str)
        assert page.plain_text_url == 'http://some.org/with/text'
        # delete the plain text version
        del page.extra_data['rendering'][1]
        assert page.plain_text_url is None




    def test_absolute_url(self):
        manif = Manifest(short_id='bk123', label='Book 1')
        page = Canvas(manifest=manif, label='Image 1', short_id='pg123', order=1)
        assert manif.short_id in page.get_absolute_url()
        assert page.short_id in page.get_absolute_url()
        # FIXME: is this a useful test or too specific
        assert page.get_absolute_url() == \
            '/iiif/%s/canvases/%s/' % (manif.short_id, page.short_id)

    def test_admin_thumb(self):
        img_service = 'https://images.co'
        img_id = 'some-file.jp2'

        page = Canvas(iiif_image_id='/'.join([img_service, img_id]))
        admin_thumb = page.admin_thumbnail()
        assert '<img src="' in admin_thumb
        assert str(page.image.mini_thumbnail()) in admin_thumb


    def test_next(self):
        manif = Manifest.objects.create(short_id='bk123', label='Book 1')
        page1, page2, page3 = Canvas.objects.bulk_create([
            Canvas(label='P1', short_id='pg1', order=0, manifest=manif),
            Canvas(label='P2', short_id='pg2', order=1, manifest=manif),
            Canvas(label='P3', short_id='pg3', order=2, manifest=manif)
        ])

        assert page1.next().short_id == page2.short_id
        assert page2.next().short_id == page3.short_id
        assert not page3.next()

    def test_prev(self):
        manif = Manifest.objects.create(short_id='bk123', label='Book 1')
        page1, page2, page3 = Canvas.objects.bulk_create([
            Canvas(label='P1', short_id='pg1', order=0, manifest=manif),
            Canvas(label='P2', short_id='pg2', order=1, manifest=manif),
            Canvas(label='P3', short_id='pg3', order=2, manifest=manif)
        ])

        assert not page1.prev()
        assert page2.prev().short_id == page1.short_id
        assert page3.prev().short_id == page2.short_id


class TestIIIFImage(TestCase):

    def setUp(self):
        self.img_id = 'testimage.png'
        self.img_service = 'https://ima.ge/loris/'
        self.iiif_img = IIIFImage(self.img_service, self.img_id)

    def test_thumbnail(self):
        thumb_img = self.iiif_img.thumbnail()
        size_info = thumb_img.size.as_dict()

        assert size_info['width'] == self.iiif_img.thumbnail_size
        assert size_info['height'] == self.iiif_img.thumbnail_size
        assert size_info['exact'] is True
        assert thumb_img.image_options['fmt'] == 'png'

    def test_mini_thumbnail(self):
        thumb_img = self.iiif_img.mini_thumbnail()
        size_info = thumb_img.size.as_dict()

        assert size_info['width'] == self.iiif_img.mini_thumbnail_size
        assert size_info['height'] == self.iiif_img.mini_thumbnail_size
        assert size_info['exact'] is True
        assert thumb_img.image_options['fmt'] == 'png'

    def test_page_size(self):
        thumb_img = self.iiif_img.page_size()
        size_info = thumb_img.size.as_dict()

        assert size_info['width'] == self.iiif_img.single_page_size
        assert size_info['height'] == self.iiif_img.single_page_size
        assert size_info['exact'] is True


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
            mockrequests.codes = requests.codes
            mockresponse = mockrequests.get.return_value
            mockresponse.status_code = requests.codes.ok
            mockresponse.json.return_value = data
            pres = IIIFPresentation.from_url(manifest_url)
            assert pres.type == 'sc:Manifest'
            mockrequests.get.assert_called_with(manifest_url)
            mockrequests.get.return_value.json.assert_called_with()

            # error handling
            # bad status code response on the url
            with pytest.raises(IIIFException) as excinfo:
                mockresponse.status_code = requests.codes.forbidden
                mockresponse.reason = 'Forbidden'
                IIIFPresentation.from_url(manifest_url)
            assert 'Error retrieving manifest' in str(excinfo.value)
            assert '403 Forbidden' in str(excinfo.value)

            # valid http response but not a json response
            with pytest.raises(IIIFException) as excinfo:
                mockresponse.status_code = requests.codes.ok
                # content type header does not indicate json
                mockresponse.headers = {'content-type': 'text/html'}
                mockresponse.json.side_effect = \
                    json.decoder.JSONDecodeError('err', 'doc', 1)
                IIIFPresentation.from_url(manifest_url)
            assert 'No JSON found' in str(excinfo.value)

            # json parsing error
            with pytest.raises(IIIFException) as excinfo:
                # content type header indicates json, but parsing failed
                mockresponse.headers = {'content-type': 'application/json'}
                mockresponse.json.side_effect = \
                    json.decoder.JSONDecodeError('err', 'doc', 1)
                IIIFPresentation.from_url(manifest_url)
            assert 'Error parsing JSON' in str(excinfo.value)

    def test_from_url_or_file(self):
        with patch.object(IIIFPresentation, 'from_url') as mock_from_url:
            # local fixture file
            pres = IIIFPresentation.from_file_or_url(self.test_manifest)
            assert pres.type == 'sc:Manifest'
            mock_from_url.assert_not_called()

            pres = IIIFPresentation.from_file_or_url('http://mani.fe/st')
            mock_from_url.assert_called_with('http://mani.fe/st')

            # nonexistent file path
            with pytest.raises(IIIFException) as excinfo:
                IIIFPresentation.from_file_or_url('/manifest/not/found')
            assert 'File not found: ' in str(excinfo.value)

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

    def test_first_label(self):
        pres = IIIFPresentation.from_file(self.test_manifest)
        assert pres.first_label == pres.label[0]
        pres.label = 'unlisted single title'
        assert pres.first_label == pres.label


class TestManifestImporter(TestCase):
    test_manifest = os.path.join(FIXTURE_DIR, 'chto-manifest.json')
    test_coll_manifest = os.path.join(FIXTURE_DIR,
        'cotsen-collection-manifest.json')
    test_manifest_noseq = os.path.join(FIXTURE_DIR, 'manifest-noseq.json')

    def setUp(self):
        self.importer = ManifestImporter()

    def test_import_supported(self):
        # currently only supports paged/left-to-right
        pres = IIIFPresentation.from_file(self.test_manifest)
        assert self.importer.import_supported(pres) == True

        # non paged
        pres.viewingHint = 'non-paged'
        pres.viewingDirection = None
        assert self.importer.import_supported(pres) == False

        # no viewing hint or direction
        pres.viewingHint = None
        assert self.importer.import_supported(pres) == False

    @patch('djiffy.importer.get_iiif_url')
    def test_import_manifest(self, mock_getiiifurl):
        pres = IIIFPresentation.from_file(self.test_manifest)
        mock_extra_data = {
            'title': {
                '@value': 'Sample extra metadata',
                '@language': 'eng'
            },
            'identifier': ['ark:/88435/tm70mz058']
        }
        # doctor one sequence to add a rendering field
        added_rendering = {
            '@id': 'https://someurl/with/plain/text',
            'format': 'text/plain',
            'label': 'Download page text'
        }
        # set first canvas, first sequence with a link to OCR text
        pres.sequences[0].canvases[0].rendering = added_rendering
        mock_getiiifurl.return_value.json.return_value = mock_extra_data
        manif = self.importer.import_manifest(pres, self.test_manifest)
        assert isinstance(manif, Manifest)

        assert manif.label == "Chto my stroim : Tetrad\u02b9 s kartinkami"
        assert manif.short_id == 'ph415q7581'
        assert manif.metadata['Creator'] == ["Savel\u02b9ev, L. (Leonid), 1904-1941"]
        assert manif.metadata['Format'] == ["Book"]
        # extra data requested and saved from seeAlso when present
        assert pres.seeAlso.id in manif.extra_data
        assert manif.extra_data[pres.seeAlso.id] == mock_extra_data
        assert mock_getiiifurl.called_with(pres.seeAlso.id)
        assert mock_getiiifurl.return_value.json.called_with()
        # license & logo available
        assert manif.license == "http://rightsstatements.org/vocab/NKC/1.0/"
        assert manif.logo == "https://example.com/logo.png"

        assert len(manif.canvases.all()) == len(pres.sequences[0].canvases)
        assert manif.thumbnail.iiif_image_id == \
             'https://libimages1.princeton.edu/loris/plum_prod/p0%2F28%2F71%2Fv9%2F8d-intermediate_file.jp2'

        # check handling of canvas with rendering data
        # should have rendering stored as a dictionary
        assert manif.canvases.first().extra_data['rendering'] \
            == added_rendering
        # now check that another canvas does not have a rendering field if
        # doesn't have one in the manifest data
        assert 'rendering' not in manif.canvases.last().extra_data

        # check other canvas fields
        first = manif.canvases.first()
        assert first.label == 'image 1'
        assert first.short_id == 'p02871v98d'
        assert first.uri == \
            'https://plum.princeton.edu/concern/scanned_resources/ph415q7581/manifest/canvas/p02871v98d'
        assert first.iiif_image_id == 'https://libimages1.princeton.edu/loris/plum_prod/p0%2F28%2F71%2Fv9%2F8d-intermediate_file.jp2'
        # first canvas, so it happens to be used as thumbnail
        assert first.thumbnail
        assert first.order == 0
        # won't import if already in db
        assert self.importer.import_manifest(pres, self.test_manifest) is None

        # check that the last canvas is not used as thumbnail and is in order
        assert not manif.canvases.last().thumbnail
        assert manif.canvases.last().order == manif.canvases.count() - 1

        # non-json seeAlso data should store the url
        manif.delete()
        pres.seeAlso.format = 'text/xml'
        manif = self.importer.import_manifest(pres, self.test_manifest)
        assert pres.seeAlso.id in manif.extra_data
        assert manif.extra_data[pres.seeAlso.id] == {}

        # handle multiple seeAlso links
        manif.delete()
        link1 = 'https://bibdata.princeton.edu/bibliographic/4765261/jsonld'
        link2 = 'https://findingaids.princeton.edu/collections/RBD1.1/c8193.xml?scope=record'
        pres.seeAlso = [
            {'@id': link1, 'format': 'application/ld+json'},
            {'@id': link2, 'format': 'text/xml'}
        ]
        manif = self.importer.import_manifest(pres, self.test_manifest)
        assert link1 in manif.extra_data
        assert link2 in manif.extra_data
        assert manif.extra_data[link1] == mock_extra_data
        assert manif.extra_data[link2] == {}

        # no error if seeAlso is not present
        manif.delete()
        del pres.seeAlso
        manif = self.importer.import_manifest(pres, self.test_manifest)
        assert set(manif.extra_data.keys()) == set(['logo', 'license'])

        # unsupported type won't import
        pres.id = 'http://some.other/uri'
        pres.viewingHint = 'non-paged'
        pres.viewingDirection = None
        assert self.importer.import_manifest(pres, self.test_manifest) is None

        # manifest with no sequence (not valid IIIF, but shouldn't chocke)
        pres = IIIFPresentation.from_file(self.test_manifest_noseq)
        assert self.importer.import_manifest(pres, self.test_manifest) is None

        # TODO: test import handling for fields that could be string or list

    @patch('djiffy.importer.get_iiif_url')
    def test_import_manifest_update(self, mock_getiiifurl):
        # test updating a previously imported manifest
        pres = IIIFPresentation.from_file(self.test_manifest)
        # simulate no extra data
        mock_getiiifurl.return_value.json.return_value = {}
        # remove a canvas before first import to test adding it in update
        orig_canvases = list(pres.sequences[0].canvases)
        pres.sequences[0].canvases = orig_canvases[:-1]

        # import once
        db_manifest = self.importer.import_manifest(pres, self.test_manifest)
        assert db_manifest.canvases.count() == len(pres.sequences[0].canvases)

        # modify manifest and update - new label, new canvas
        pres.sequences[0].canvases[0].label = 'New label'
        pres.sequences[0].canvases = orig_canvases

        self.importer.update = True
        db_manifest = self.importer.import_manifest(pres, self.test_manifest)
        assert isinstance(db_manifest, Manifest)
        # new canvas was added
        assert db_manifest.canvases.count() == len(orig_canvases)
        # label updated
        assert db_manifest.canvases.first().label == 'New label'

        # modify manifest to remove canvases and update
        pres.sequences[0].canvases = orig_canvases[:5]
        self.importer.stdout = StringIO()
        db_manifest = self.importer.import_manifest(pres, self.test_manifest)
        assert db_manifest.canvases.count() == len(pres.sequences[0].canvases)
        output = self.importer.stdout.getvalue()
        assert 'removing %d canvases' % (len(orig_canvases) - 5, ) in output

    @patch('djiffy.models.get_iiif_url')
    def test_import_collection(self, mock_getiiifurl):
        pres = IIIFPresentation.from_file(self.test_manifest)
        assert self.importer.import_collection(pres) is None

        # mock actual request to avoid hitting real urls when
        # importing the collection
        mock_getiiifurl.return_value.status_code = requests.codes.ok
        # needs to return a non-empty dict for import to happen
        test_json_result = {"@type": "sc:Manifest"}
        mock_getiiifurl.return_value.json.return_value = test_json_result
        coll = IIIFPresentation.from_file(self.test_coll_manifest)
        with patch.object(self.importer, 'import_manifest') as mock_import_manifest:
            imported = self.importer.import_collection(coll)

            mockpres = IIIFPresentation(test_json_result)
            for i in range(3):
                mock_import_manifest.assert_any_call(mockpres, coll.manifests[i].id)

        assert len(imported) == 4

        # error handling
        with patch('djiffy.importer.IIIFPresentation') as mockiiifpres:
            mockiiifpres.from_file_or_url.side_effect = IIIFException
            imported = IIIFPresentation.from_file(self.test_coll_manifest)
            assert self.test_manifest not in imported

    @patch('djiffy.importer.IIIFPresentation')
    def test_import_paths(self, mockiiifpres):
        iiifmanifest = mockiiifpres.from_file_or_url.return_value
        with patch.object(self.importer, 'import_collection') as mock_coll_import:
            iiifmanifest.type = 'sc:Collection'
            self.importer.import_paths([self.test_coll_manifest])
            mockiiifpres.from_file_or_url.assert_called_with(self.test_coll_manifest)
            mock_coll_import.assert_called_with(iiifmanifest)

        with patch.object(self.importer, 'import_manifest') as mock_manif_import:
            iiifmanifest.type = 'sc:Manifest'
            self.importer.import_paths([self.test_manifest])
            mockiiifpres.from_file_or_url.assert_called_with(self.test_manifest)
            mock_manif_import.assert_called_with(iiifmanifest,
                                                 self.test_manifest)

        # skips error
        mockiiifpres.from_file_or_url.side_effect = IIIFException
        with patch.object(self.importer, 'import_manifest') as mock_manif_import:
            self.importer.stderr = StringIO()
            self.importer.import_paths([self.test_manifest])
            mockiiifpres.from_file_or_url.assert_called_with(self.test_manifest)
            mock_manif_import.assert_not_called()

    def test_output(self):
        # with no stdout defined, no error
        self.importer.output('test')

        # if stdout is defined, writes message
        self.importer.stdout = StringIO()
        self.importer.output('test')
        self.importer.stdout.seek(0)
        assert self.importer.stdout.read() == 'test'

    def test_error_msg(self):
        # no stderr
        self.importer.error_msg('oops')

        # stderr but no style
        self.importer.stderr = StringIO()
        self.importer.error_msg('oops')
        self.importer.stderr.seek(0)
        assert self.importer.stderr.read() == 'oops'

        # both stderr and style
        self.importer.stderr = StringIO()

        def err_style(msg):
            return '<i>%s</i>' % msg

        self.importer.style = Mock()
        self.importer.style.ERROR = err_style
        self.importer.error_msg('oops')
        self.importer.stderr.seek(0)
        assert self.importer.stderr.read() == '<i>oops</i>'


class TestManifestSelectWidget(TestCase):
    # test admin select widget

    def test_render(self):
        widget = ManifestSelectWidget()
        # no value set - should not error
        assert widget.render('manifest', None, {'id': 123})
        # empty string - shoudl not error
        assert widget.render('manifest', '', {'id': 123})

        # create test manifest to render
        manif = Manifest.objects.create(label='test manifest', short_id='abc3')
        rendered = widget.render('person', manif.id, {'id': 1234})
        # no thumbnail - should not display text 'none'
        assert 'None' not in rendered
        assert manif.get_absolute_url() in rendered
        assert reverse('admin:djiffy_manifest_change', args=[manif.id]) in \
            rendered

        # associate canvas for thumbnail
        canv = Canvas.objects.create(short_id='def4', thumbnail=True,
                                     manifest=manif, order=1)
        rendered = widget.render('person', manif.id, {'id': 1234})
        # no thumbnail - should not display text 'none'
        assert canv.admin_thumbnail() in rendered


class TestViews(TestCase):

    def setUp(self):
        self.manif1 = Manifest.objects.create(short_id='bk123', label='Book 1')
        self.pages = Canvas.objects.bulk_create([
            Canvas(label='P1', short_id='pg1', order=0, manifest=self.manif1),
            Canvas(label='P2', short_id='pg2', order=1, manifest=self.manif1),
            Canvas(label='P3', short_id='pg3', order=2, manifest=self.manif1)
        ])
        self.manif2 = Manifest.objects.create(short_id='bk456', label='Book 2')

    def test_manifest_list(self):
        manifest_list_url = reverse('djiffy:list')
        response = self.client.get(manifest_list_url)
        assert self.manif1 in response.context['object_list']
        assert self.manif2 in response.context['object_list']
        self.assertTemplateUsed(template_name='djiffy/manifest_list.html')

    def test_manifest_detail(self):
        manifest_url = reverse('djiffy:manifest',
                               kwargs={'id': self.manif1.short_id})
        response = self.client.get(manifest_url)
        assert response.context['manifest'] == self.manif1
        self.assertTemplateUsed(template_name='djiffy/manifest_detail.html')

        # bad id
        bad_manifest_url = reverse('djiffy:manifest', kwargs={'id': 'bogus'})
        response = self.client.get(bad_manifest_url)
        assert response.status_code == 404

    def test_canvas_detail(self):
        canvas_url = reverse(
            'djiffy:canvas',
            kwargs={'id': self.pages[0].short_id,
                    'manifest_id': self.manif1.short_id})
        response = self.client.get(canvas_url)
        assert response.context['canvas'].short_id == self.pages[0].short_id
        self.assertTemplateUsed(template_name='djiffy/canvas_detail.html')

        # bogus canvas id
        bad_canvas_url = reverse(
            'djiffy:canvas',
            kwargs={'id': 'bogus', 'manifest_id': self.manif1.short_id})
        response = self.client.get(bad_canvas_url)
        assert response.status_code == 404

        # bogus manifest id
        bad_canvas_url = reverse(
            'djiffy:canvas',
            kwargs={'id': self.pages[0].short_id, 'manifest_id': 'bogus'})
        response = self.client.get(bad_canvas_url)
        assert response.status_code == 404

        # existing manifest and canvas ids that don't belong together
        bad_canvas_url = reverse(
            'djiffy:canvas',
            kwargs={'id': self.pages[0].short_id,
                    'manifest_id': self.manif2.short_id})
        response = self.client.get(bad_canvas_url)
        assert response.status_code == 404

    def test_canvas_autocomplete(self):
        canvas_autocomplete_url = reverse('djiffy:canvas-autocomplete')
        response = self.client.get(canvas_autocomplete_url,
                                   params={'q': 'pg1'})
        assert response.status_code == 200
        data = json.loads(response.content.decode('utf-8'))
        assert 'results' in data
        assert data['results'][0]['text'] == str(self.pages[0])
        # check the manifest label functionality -- all pages for a manifest
        response = self.client.get(canvas_autocomplete_url,
                                   params={'q': 'Book'})
        assert response.status_code == 200
        data = json.loads(response.content.decode('utf-8'))
        assert 'results' in data
        # should bring back all three since the manifest label is Book 1
        assert len(data['results']) == 3


@patch('djiffy.management.commands.import_manifest.ManifestImporter')
class TestImportManifest(TestCase):
    # test manage command

    def test_command(self, mockmanifestimporter):
        # the real import logic is tested elsewhere, this is
        # just a test to ensure the manage command runs
        uris = ['manifest1.json', 'manifest2.json', 'http://so.me/manifest']
        call_command('import_manifest', *uris)

        importer_call_kwargs = mockmanifestimporter.call_args[1]
        for expected_arg in ['stdout', 'stderr', 'style']:
            assert expected_arg in importer_call_kwargs

        mockmanifestimporter.return_value.import_paths.assert_called_with(uris)
