from collections import OrderedDict
import json
import os.path

from attrdict import AttrMap
from django.db import models
try:
    # django 1.10
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse
from jsonfield import JSONField
from piffle import iiif
import requests
import urllib


class IIIFException(Exception):
    pass


class Manifest(models.Model):
    '''Minimal db model representation of an IIIF presentation manifest'''
    label = models.TextField()
    short_id = models.CharField(max_length=255, unique=True)
    uri = models.URLField()
    metadata = JSONField(load_kwargs={'object_pairs_hook': OrderedDict})
    created = models.DateField(auto_now_add=True)
    last_modified = models.DateField(auto_now=True)

    class Meta:
        verbose_name = 'IIIF Manifest'

    # todo: metadata? thumbnail references
    # - should we cache the actual manifest file?

    def __str__(self):
        return self.label or self.short_id

    @property
    def thumbnail(self):
        return self.canvases.filter(thumbnail=True).first()

    def get_absolute_url(self):
        return reverse('djiffy:manifest', args=[self.short_id])

    def admin_thumbnail(self):
        if self.thumbnail:
            return self.thumbnail.admin_thumbnail()
    admin_thumbnail.short_description = 'Thumbnail'
    admin_thumbnail.allow_tags = True


class IIIFImage(iiif.IIIFImageClient):
    '''Subclass of :class:`piffle.iiif.IIIFImageClient`, for generating
    IIIF Image URIs for manifest canvas images.'''

    #: long edge size for single page display
    single_page_size = 1000
    #: long edge size for thumbnail
    thumbnail_size = 300
    #: long edge size for mini thumbnail
    mini_thumbnail_size = 100

    def thumbnail(self):
        'thumbnail'
        return self.size(height=self.thumbnail_size, width=self.thumbnail_size,
                         exact=True).format('png')

    def mini_thumbnail(self):
        'mini thumbnail'
        return self.size(height=self.mini_thumbnail_size,
                         width=self.mini_thumbnail_size, exact=True) \
                   .format('png')

    def page_size(self):
        'page size for display: :attr:`SINGLE_PAGE_SIZE` on the long edge'
        return self.size(height=self.single_page_size,
                         width=self.single_page_size, exact=True)


class Canvas(models.Model):
    '''Minimal db model representation of a canvas from an IIIF manifest'''

    label = models.TextField()
    short_id = models.CharField(max_length=255)
    uri = models.URLField()
    iiif_image_id = models.URLField()
    manifest = models.ForeignKey(Manifest, related_name='canvases')
    thumbnail = models.BooleanField(default=False)
    # for now only storing a single sequence, so just store order on the page
    order = models.PositiveIntegerField()
    # format? size? (ocr text eventually?)

    class Meta:
        ordering = ["manifest", "order"]
        verbose_name = 'IIIF Canvas'
        verbose_name_plural = 'IIIF Canvases'
        unique_together = ("short_id", "manifest")

    def __str__(self):
        return '%s %d (%s)%s' % (self.manifest, self.order + 1, self.label,
            '*' if self.thumbnail else '')

    @property
    def image(self):
        # NOTE: piffle iiif image wants service & id split out.
        # Should update to handle iiif image ids as provided in manifests
        # for now, split into service and image id. (is this reliable?)
        return IIIFImage(*self.iiif_image_id.rsplit('/', 1))

    def get_absolute_url(self):
        return reverse('djiffy:canvas', args=[self.manifest.short_id, self.short_id])

    def next(self):
        return Canvas.objects.filter(manifest=self.manifest, order__gt=self.order) \
            .first()

    def prev(self):
        return Canvas.objects.filter(manifest=self.manifest, order__lt=self.order) \
            .last()

    def admin_thumbnail(self):
        return u'<img src="%s" />' % self.image.mini_thumbnail()
    admin_thumbnail.short_description = 'Thumbnail'
    admin_thumbnail.allow_tags = True


class IIIFPresentation(AttrMap):

    at_fields = ['type', 'id', 'context']

    @classmethod
    def from_file(cls, path):
        with open(path) as manifest:
            data = json.loads(manifest.read())
        return cls(data)

    @classmethod
    def from_url(cls, uri):
        response = requests.get(uri)
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
        return urllib.parse.urlparse(url).scheme != ""

    @classmethod
    def from_file_or_url(cls, path):
        if os.path.isfile(path):
            return cls.from_file(path)
        elif cls.is_url(path):
            return cls.from_url(path)
        else:
            raise IIIFException('File not found: %s' % path)

    @classmethod
    def short_id(cls, uri):
        '''Generate a short id from full manifest/canvas uri identifiers
        for use in local urls.'''

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

