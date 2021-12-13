from collections import OrderedDict
import json
import os.path
import urllib

from attrdict import AttrMap
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.html import format_html
from jsonfield import JSONField
from piffle import iiif
import rdflib
from rdflib.namespace import DC
import requests


def get_iiif_url(url):
    '''Wrapper around :meth:`requests.get` to support conditionally
    adding an auth token based on the domain of the request url and
    any **AUTH_TOKENS** configured in django settings.'''
    request_options = {}

    AUTH_TOKENS = getattr(settings, 'DJIFFY_AUTH_TOKENS', None)
    if AUTH_TOKENS:
        domain = urllib.parse.urlparse(url).netloc
        if domain in AUTH_TOKENS:
            request_options['params'] = {'auth_token': AUTH_TOKENS[domain]}

    return requests.get(url, **request_options)


class IIIFException(Exception):
    '''Custom exception for IIIF/djiffy specific errors'''
    pass


class Manifest(models.Model):
    '''Minimal db model representation of an IIIF presentation manifest'''
    #: label
    label = models.TextField()
    #: short id extracted from URI
    short_id = models.CharField(max_length=255, unique=True)
    #: URI
    uri = models.URLField()
    #: iiif presentation metadata for display
    metadata = JSONField(load_kwargs={'object_pairs_hook': OrderedDict})
    #: date local manifest cache was created
    created = models.DateField(auto_now_add=True)
    #: date local manifest cache was last modified
    last_modified = models.DateField(auto_now=True)
    #: extra data provided via a 'seeAlso' reference
    extra_data = JSONField(load_kwargs={'object_pairs_hook': OrderedDict},
        default=OrderedDict)

    class Meta:
        verbose_name = 'IIIF Manifest'
        # add custom permissions; change and delete provided by django
        permissions = (
            ('view_canvas', 'Can view %s' % verbose_name),
        )

    # todo: metadata? thumbnail references
    # - should we cache the actual manifest file?
    # TODO: thumbnail doesn't have to be a IIIF image! Support thumbnail url?

    def __str__(self):
        return self.label or self.short_id

    @property
    def thumbnail(self):
        '''thumbnail url for associated canvas'''
        return self.canvases.filter(thumbnail=True).first()

    def get_absolute_url(self):
        ''''url for this manifest within the django site'''
        return reverse('djiffy:manifest', args=[self.short_id])

    def admin_thumbnail(self):
        '''thumbnail for convenience display in admin interface'''
        if self.thumbnail:
            return self.thumbnail.admin_thumbnail()
    admin_thumbnail.short_description = 'Thumbnail'

    @property
    def logo(self):
        '''manifest logo, if there is one'''
        return self.extra_data.get('logo', None)

    @property
    def license(self):
        '''manifest license, if there is one'''
        return self.extra_data.get('license', None)

    @property
    def rights_statement_id(self):
        '''short id for rightstatement.org license'''
        if self.license and 'rightsstatements.org' in self.license:
            return self.license.rstrip(' /').split('/')[-2]

    _rights_graph = None

    def license_label(self, lang='en'):
        '''Get the text label for the rights license.  Uses local
        value from edm rights if available; otherwise uses
        data for the URI to get the preferred label or title.'''

        # Some manifests have a seeAlso data contains an "edm_rights"
        # section with a label for the rights statement.
        # Use that if available (NOTE: ignores specified language)
        # NOTE: possibly PUL specific, but shouldn't hurt to look locally first
        for data in self.extra_data.values():
            if 'edm_rights' in data and 'pref_label' in data['edm_rights']:
                return data['edm_rights']['pref_label']

        # if license/rights label is not available locally, get via uri
        if self._rights_graph is None:
            # if license is defined and a url
            if self.license and urllib.parse.urlparse(self.license).scheme in ['http', 'https']:
                self._rights_graph = rdflib.Graph()
                try:
                    # rights statement org does content-negotiation for json-jd,
                    # but rdflib doesn't handle that automatically
                    if 'rightsstatements.org' in self.license:
                        resp = requests.get(self.license,
                                            headers={'Accept': 'application/json'},
                                            allow_redirects=False)
                        if resp.status_code == requests.codes.see_other:
                            self._rights_graph.parse(resp.headers['location'], format='json-ld')

                    # creative commons doesn't support content negotiation,
                    # but you can add rdf to the end of the url
                    elif 'creativecommons.org' in self.license:
                        rdf_uri = '/'.join([self.license.rstrip('/'), 'rdf'])
                        self._rights_graph.parse(rdf_uri)

                except Exception:
                    # possible to get an exception when parsing the
                    # rdf, maybe on the request; don't choke if we do!

                    # NOTE: using generic Exception here becuase unfortunately
                    # that is what rdflib raises when it can't parse RDF
                    pass

        # get the preferred label for this license in the requested language;
        # returns a list of label, value; use the first value
        if self._rights_graph:
            license_uri = rdflib.URIRef(self.license)
            preflabel = self._rights_graph.preferredLabel(license_uri,
                                                          lang=lang)
            if preflabel:
                # convert rdflib Literal to string
                return str(preflabel[0][1])
            # otherwise, get dc title
            # iterate over all titles and return one with a matching language code
            for title in self._rights_graph.objects(subject=license_uri, predicate=DC.title):
                if title.language == lang:
                    return str(title)


class IIIFImage(iiif.IIIFImageClient):
    '''Subclass of :class:`piffle.iiif.IIIFImageClient`, for generating
    IIIF Image URIs for manifest canvas images.'''

    #: long edge size for single page display
    single_page_size = 1000
    #: long edge size for thumbnail
    thumbnail_size = 300
    #: long edge size for mini thumbnail
    mini_thumbnail_size = 100

    thumbnail_format = getattr(settings, 'DJIFFY_THUMBNAIL_FORMAT', 'png')

    def thumbnail(self):
        '''thumbnail'''
        return self.size(height=self.thumbnail_size, width=self.thumbnail_size,
                         exact=True).format(self.thumbnail_format)

    def mini_thumbnail(self):
        '''mini thumbnail'''
        return self.size(height=self.mini_thumbnail_size,
                         width=self.mini_thumbnail_size, exact=True) \
                   .format(self.thumbnail_format)

    def page_size(self):
        '''page size for display: :attr:`SINGLE_PAGE_SIZE` on the long edge'''
        return self.size(height=self.single_page_size,
                         width=self.single_page_size, exact=True)


class Canvas(models.Model):
    '''Minimal db model representation of a canvas from an IIIF manifest'''

    #: label
    label = models.TextField()
    #: short id extracted from URI
    short_id = models.CharField(max_length=255)
    #: URI
    uri = models.URLField()
    #: URL of IIIF image for this canvas
    iiif_image_id = models.URLField()
    #: :class:`Manifest` this canvas vbelongs to
    manifest = models.ForeignKey(Manifest, related_name='canvases',
                                 on_delete=models.CASCADE)
    #: boolean flag to indicate if this canvas should be used as thumbnail
    thumbnail = models.BooleanField(default=False)
    #: order of this canvas within associated manifest primary sequence
    order = models.PositiveIntegerField()
    # (for now only stores a single sequence, so just store order on the page)
    # format? size? (ocr text eventually?)
    #: extra data not otherwise given its own field, serialized as json
    extra_data = JSONField(load_kwargs={'object_pairs_hook': OrderedDict},
                           default=OrderedDict)

    class Meta:
        ordering = ["manifest", "order"]
        verbose_name = 'IIIF Canvas'
        verbose_name_plural = 'IIIF Canvases'
        unique_together = ("short_id", "manifest")
        # add custom permissions; change and delete provided by django
        permissions = (
            ('view_manifest', 'Can view %s' % verbose_name),
        )

    def __str__(self):
        return '%s %d (%s)%s' % (self.manifest, self.order + 1, self.label,
            '*' if self.thumbnail else '')

    @property
    def image(self):
        '''Associated IIIF image for this canvas as :class:`IIIFImage`'''
        # NOTE: piffle iiif image wants service & id split out.
        # Should update to handle iiif image ids as provided in manifests
        # for now, split into service and image id. (is this reliable?)
        return IIIFImage(*self.iiif_image_id.rsplit('/', 1))

    @property
    def plain_text_url(self):
        '''Return plain text url for a canvas if one exists'''

        rendering = self.extra_data.get('rendering', None)
        if rendering:
            # handle both cases where this is a list and where it is just
            # a dictionary, to be safe
            if isinstance(rendering, list):
                for item in rendering:
                    # iterate over the list and return the first plain text url
                    # we find
                    if 'format' in item and item['format'] == 'text/plain':
                        return item['@id']
            else:
                # otherwise, if it's a dictionary, check if it's plaintext and
                # return
                if 'format' in rendering \
                        and rendering['format'] == 'text/plain':
                    return rendering['@id']
        # finally return None if no plain text is available or no rendering
        return None

    @property
    def width(self):
        return self.extra_data.get('width', None)

    @property
    def height(self):
        return self.extra_data.get('height', None)

    def get_absolute_url(self):
        ''''url for this canvas within the django site'''
        return reverse('djiffy:canvas', args=[self.manifest.short_id, self.short_id])

    def next(self):
        '''Next canvas after this one in sequence (within manifest
        primary sequence).  Returns an empty queryset if there is no next
        canvas.'''
        return Canvas.objects.filter(manifest=self.manifest, order__gt=self.order) \
            .first()

    def prev(self):
        '''Previous canvas before this one in sequence
        (within manifest primary sequence).  Returns an empty queryset
        if there is no next canvas.'''
        return Canvas.objects.filter(manifest=self.manifest, order__lt=self.order) \
            .last()

    def admin_thumbnail(self):
        '''thumbnail for convenience display in admin interface'''
        return format_html('<img src="{}" />', self.image.mini_thumbnail())
    admin_thumbnail.short_description = 'Thumbnail'


class IIIFPresentation(AttrMap):
    ''':class:`attrdict.AttrMap` subclass for read access to IIIF Presentation
    content'''

    # TODO: document sample use, e.g. @ fields

    at_fields = ['type', 'id', 'context']

    @classmethod
    def from_file(cls, path):
        '''Iniitialize :class:`IIIFPresentation` from a file.'''
        with open(path) as manifest:
            data = json.loads(manifest.read())
        return cls(data)

    @classmethod
    def from_url(cls, uri):
        '''Iniitialize :class:`IIIFPresentation` from a URL.

        :raises: :class:`IIIFException` if URL is not retrieved successfully,
            if the response is not JSON content, or if the JSON cannot be parsed.
        '''
        response = get_iiif_url(uri)
        if response.status_code == requests.codes.ok:
            try:
                return cls(response.json())
            except json.decoder.JSONDecodeError as err:
                # if json fails, two possibilities:
                # - we didn't actually get json (e.g. redirect for auth)
                if 'application/json' not in response.headers['content-type']:
                    raise IIIFException('No JSON found at %s' % uri)
                # - there is something wrong with the json
                raise IIIFException('Error parsing JSON for %s: %s' %
                    (uri, err))

        raise IIIFException('Error retrieving manifest at %s: %s %s' %
            (uri, response.status_code, response.reason))

    @classmethod
    def is_url(cls, url):
        '''Utility method to check if a path is a url or file'''
        return urllib.parse.urlparse(url).scheme != ""

    @classmethod
    def from_file_or_url(cls, path):
        '''Iniitialize :class:`IIIFPresentation` from a file or a url.'''
        if os.path.isfile(path):
            return cls.from_file(path)
        elif cls.is_url(path):
            return cls.from_url(path)
        else:
            raise IIIFException('File not found: %s' % path)

    @classmethod
    def short_id(cls, uri):
        '''Generate a short id from full manifest/canvas uri identifiers
        for use in local urls.  Logic is based on the recommended
        url pattern from the IIIF Presentation 2.0 specification.'''

        # shortening should work reliably for uris that follow
        # recommended url patterns from the spec
        # http://iiif.io/api/presentation/2.0/#a-summary-of-recommended-uri-patterns
        #   manifest:  {scheme}://{host}/{prefix}/{identifier}/manifest
        #   canvas: {scheme}://{host}/{prefix}/{identifier}/canvas/{name}

        # remove trailing /manifest at the end of the url, if present
        if uri.endswith('/manifest'):
            uri = uri[:-len('/manifest')]
        # split on slashes and return the last portion
        return uri.split('/')[-1]


    def __getattr__(self, key):
        """
        Access an item as an attribute.
        """
        # override getattr to allow use of keys with leading @,
        # which are otherwise not detected as present and not valid
        at_key = self._handle_at_keys(key)
        if key not in self or \
          (key not in self.at_fields and at_key not in self) or \
          not self._valid_name(key):
            raise AttributeError(
                "'{cls}' instance has no attribute '{name}'".format(
                    cls=self.__class__.__name__, name=key
                )
            )
        return self._build(self[key])

    def _handle_at_keys(self, key):
        if key in self.at_fields:
            key = '@%s' % key
        return key

    def __getitem__(self, key):
        """
        Access a value associated with a key.
        """
        return self._mapping[self._handle_at_keys(key)]

    def __setitem__(self, key, value):
        """
        Add a key-value pair to the instance.
        """
        self._mapping[self._handle_at_keys(key)] = value

    def __delitem__(self, key):
        """
        Delete a key-value pair
        """
        del self._mapping[self._handle_at_keys(key)]

    @property
    def first_label(self):
        # label can be a string or list of strings
        if isinstance(self.label, str):
            return self.label
        else:
            return self.label[0]
