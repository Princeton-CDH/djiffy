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


class IfBook(models.Model):
    '''Minimal db model representation of a Book from an IIIF manifest'''
    label = models.TextField()
    short_id = models.CharField(max_length=255)
    uri = models.URLField()
    metadata = JSONField(load_kwargs={'object_pairs_hook': OrderedDict})
    created = models.DateField(auto_now_add=True)
    last_modified = models.DateField(auto_now=True)

    class Meta:
        verbose_name = 'IIIF Book'

    # todo: metadata? thumbnail references

    def __str__(self):
        return self.label or self.short_id

    @property
    def thumbnail(self):
        print(self.pages.filter(thumbnail=True))
        return self.pages.filter(thumbnail=True).first()

    def get_absolute_url(self):
        return reverse('djiffy:book', args=[self.short_id])

    def admin_thumbnail(self):
        if self.thumbnail:
            return u'<img src="%s" />' % self.thumbnail.image.mini_thumbnail()
    admin_thumbnail.short_description = 'Thumbnail'
    admin_thumbnail.allow_tags = True


class IIIFImage(iiif.IIIFImageClient):
    '''Subclass of :class:`piffle.iiif.IIIFImageClient`, for generating
    IIIF Image URIs for book page images.'''

    long_side = 'height'

    # NOTE: using long edge instead of specifying both with exact
    # results in cleaner urls/filenams (no !), and more reliable result
    # depending on IIIF implementation

    def thumbnail(self):
        'default thumbnail: 300px on the long edge'
        return self.size(**{self.long_side: 300}).format('png')

    def mini_thumbnail(self):
        'mini thumbnail: 100px on the long edge'
        return self.size(**{self.long_side: 100}).format('png')

    #: long edge size for single page display
    SINGLE_PAGE_SIZE = 1000

    def page_size(self):
        'page size for display: :attr:`SINGLE_PAGE_SIZE` on the long edge'
        return self.size(**{self.long_side: self.SINGLE_PAGE_SIZE})


class IfPage(models.Model):
    '''Minimal db model representation of a Page from an IIIF manifest'''
    label = models.TextField()
    short_id = models.CharField(max_length=255)
    uri = models.URLField()
    iiif_image_id = models.URLField()
    book = models.ForeignKey(IfBook, related_name='pages')
    thumbnail = models.BooleanField(default=False)
    # for now only storing a single sequence, so just store order on the page
    order = models.PositiveIntegerField()
    # format? size? (ocr text eventually?)

    class Meta:
        ordering = ["book", "order"]
        verbose_name = 'IIIF Page'

    def __str__(self):
        return '%s %d (%s)%s' % (self.book, self.order + 1, self.label,
            '*' if self.thumbnail else '')

    @property
    def image(self):
        # NOTE: piffle iiif image wants service & id split out.
        # Should update to handle iiif image ids as provided in manifests
        # for now, split into service and image id. (is this reliable?)
        return IIIFImage(*self.iiif_image_id.rsplit('/', 1))

    def get_absolute_url(self):
        return reverse('djiffy:page', args=[self.book.short_id, self.short_id])

    def next(self):
        return IfPage.objects.filter(book=self.book, order__gt=self.order) \
            .first()

    def prev(self):
        return IfPage.objects.filter(book=self.book, order__lt=self.order) \
            .last()


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
        return cls(response.json())

    @classmethod
    def from_file_or_url(cls, path):
        if os.path.isfile(path):
            return cls.from_file(path)
        else:
            return cls.from_url(path)

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

