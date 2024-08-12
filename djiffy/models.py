from collections import OrderedDict

import json
import os.path

import urllib

from functools import cached_property

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.templatetags.static import static
from django.utils.html import format_html
from piffle import image as iiif
from piffle import presentation
import rdflib
from rdflib.namespace import DC, SKOS, RDFS
import requests
from requests.exceptions import ConnectionError


def get_iiif_url(url):
    """Wrapper around :meth:`requests.get` to support conditionally
    adding an auth token based on the domain of the request url and
    any **AUTH_TOKENS** configured in django settings."""
    request_options = {}

    AUTH_TOKENS = getattr(settings, "DJIFFY_AUTH_TOKENS", None)
    if AUTH_TOKENS:
        domain = urllib.parse.urlparse(url).netloc
        if domain in AUTH_TOKENS:
            request_options["params"] = {"auth_token": AUTH_TOKENS[domain]}

    return requests.get(url, **request_options)


class IIIFPresentation(presentation.IIIFPresentation):
    """Extend iiif presentation class to add support for auth tokens
    when making requests on iiif urls."""

    @classmethod
    def get_iiif_url(cls, url):
        return get_iiif_url(url)


class Manifest(models.Model):
    """Minimal db model representation of an IIIF presentation manifest"""

    #: label
    label = models.TextField()
    #: short id extracted from URI
    short_id = models.CharField(max_length=255, unique=True)
    #: URI
    uri = models.URLField()
    #: iiif presentation metadata for display
    metadata = models.JSONField(default=dict)
    #: date local manifest cache was created
    created = models.DateField(auto_now_add=True)
    #: date local manifest cache was last modified
    last_modified = models.DateField(auto_now=True)
    #: extra data provided via a 'seeAlso' reference
    extra_data = models.JSONField(default=dict)

    class Meta:
        verbose_name = "IIIF Manifest"
        # add custom permissions; change and delete provided by django
        permissions = (("view_canvas", "Can view %s" % verbose_name),)

    # todo: metadata? thumbnail references
    # - should we cache the actual manifest file?
    # TODO: thumbnail doesn't have to be a IIIF image! Support thumbnail url?

    def __str__(self):
        return self.label or self.short_id

    @property
    def thumbnail(self):
        """thumbnail url for associated canvas"""
        return self.canvases.filter(thumbnail=True).first()

    def get_absolute_url(self):
        """'url for this manifest within the django site"""
        return reverse("djiffy:manifest", args=[self.short_id])

    def admin_thumbnail(self):
        """thumbnail for convenience display in admin interface"""
        if self.thumbnail:
            return self.thumbnail.admin_thumbnail()

    admin_thumbnail.short_description = "Thumbnail"

    @cached_property
    def logo(self):
        """manifest logo, if there is one"""
        return self.extra_data.get("logo", None)

    @cached_property
    def attribution(self):
        """manifest attribution, if there is one"""
        return self.extra_data.get("attribution", None)

    @cached_property
    def license(self):
        """manifest license, if there is one"""
        return self.extra_data.get("license", None)

    @cached_property
    def license_uri(self):
        """manifest license as :class:`rdflib.URIRef`, if there is a license"""
        license = self.license
        if license:
            # CC uri is also http rather than https
            if urllib.parse.urlparse(license).hostname == "creativecommons.org":
                # remove language from url if present
                url_parts = license.rstrip("/").split("/")
                # url looks like https://creativecommons.org/publicdomain/mark/1.0/deed.de
                # if the last part is a language code, remove it
                if url_parts[-1].startswith("deed."):
                    url_parts = url_parts[:-1]
                license = "%s/" % "/".join(url_parts)  # URI requires trailing slash
            return rdflib.URIRef(license)

    @cached_property
    def rights_statement_id(self):
        """short id for rightstatement.org license"""
        # rightstatement uri is http, not https
        if (
            self.license
            and urllib.parse.urlparse(self.license).hostname == "rightsstatements.org"
        ):
            return self.license.rstrip(" /").split("/")[-2]

    @cached_property
    def creativecommons_id(self):
        """short id for creative commons license"""
        if (
            self.license
            and urllib.parse.urlparse(self.license).hostname == "creativecommons.org"
        ):
            if "publicdomain/zero/" in self.license:
                return "cc-zero"
            if "publicdomain/mark/" in self.license:
                return "publicdomain"
            else:
                # strip last slash then split; last is version, preceding is code
                return self.license.rstrip("/").split("/")[-2]

    @cached_property
    def license_image(self):
        """license image, if we can generate one"""
        if self.rights_statement_id:
            return static("img/rightsstatements_org/%s.svg" % self.rights_statement_id)
        if self.creativecommons_id:
            return static("img/creativecommons/%s.svg" % self.creativecommons_id)

    _rights_graph = None

    # TODO: should use django current language if possible
    def license_label(self, lang="en"):
        """Get the text label for the rights license.  Uses local
        value from edm rights if available; otherwise uses
        data for the URI to get the preferred label or title."""

        # Some manifests have a seeAlso data contains an "edm_rights"
        # section with a label for the rights statement.
        # Use that if available (NOTE: ignores specified language)
        # NOTE: possibly PUL specific, but shouldn't hurt to look locally first
        for data in self.extra_data.values():
            if "edm_rights" in data and "pref_label" in data["edm_rights"]:
                return data["edm_rights"]["pref_label"]

        # if license/rights label is not available locally, get via uri
        if self._rights_graph is None:
            # if license is defined and a url
            if self.license and urllib.parse.urlparse(self.license).scheme in [
                "http",
                "https",
            ]:
                self._rights_graph = rdflib.Graph()
                url_hostname = urllib.parse.urlparse(self.license).hostname
                try:
                    # rights statement org does content-negotiation for json-jd,
                    # but rdflib doesn't handle that automatically
                    if url_hostname == "rightsstatements.org":
                        resp = requests.get(
                            self.license,
                            headers={"Accept": "application/json"},
                            allow_redirects=False,
                        )
                        if resp.status_code == requests.codes.see_other:
                            self._rights_graph.parse(
                                resp.headers["location"], format="json-ld"
                            )

                    # creative commons doesn't support content negotiation,
                    # but you can add rdf to the end of the url
                    elif url_hostname == "creativecommons.org":
                        # license uri removes language if present and adds trailing slash
                        self._rights_graph.parse("%srdf" % self.license_uri)

                except Exception:
                    # possible to get an exception when parsing the
                    # rdf, maybe on the request; don't choke if we do!

                    # NOTE: using generic Exception here becuase unfortunately
                    # that is what rdflib raises when it can't parse RDF
                    pass

        # get the preferred label for this license in the requested language;
        # returns a list of label, value; use the first value
        if self._rights_graph:
            return preferredLabel(self._rights_graph, self.license_uri, lang=lang)


def preferredLabel(graph, uri, lang):
    """Get label or title from rdf graph for given uri with specified language.
    Checks for SKOS.prefLabel, RDFS.label, DC.title in that order.
    """
    for predicate in [SKOS.prefLabel, RDFS.label, DC.title]:
        for value in graph.objects(uri, predicate):
            if value.language is None or value.language == lang:
                return str(value)


class IIIFImage(iiif.IIIFImageClient):
    """Subclass of :class:`piffle.iiif.IIIFImageClient`, for generating
    IIIF Image URIs for manifest canvas images."""

    #: long edge size for single page display
    single_page_size = 1000
    #: long edge size for thumbnail
    thumbnail_size = 300
    #: long edge size for mini thumbnail
    mini_thumbnail_size = 100

    thumbnail_format = getattr(settings, "DJIFFY_THUMBNAIL_FORMAT", "png")

    def thumbnail(self):
        """thumbnail"""
        return self.size(
            height=self.thumbnail_size, width=self.thumbnail_size, exact=True
        ).format(self.thumbnail_format)

    def mini_thumbnail(self):
        """mini thumbnail"""
        return self.size(
            height=self.mini_thumbnail_size, width=self.mini_thumbnail_size, exact=True
        ).format(self.thumbnail_format)

    def page_size(self):
        """page size for display: :attr:`SINGLE_PAGE_SIZE` on the long edge"""
        return self.size(
            height=self.single_page_size, width=self.single_page_size, exact=True
        )


class Canvas(models.Model):
    """Minimal db model representation of a canvas from an IIIF manifest"""

    #: label
    label = models.TextField()
    #: short id extracted from URI
    short_id = models.CharField(max_length=255)
    #: URI
    uri = models.URLField()
    #: URL of IIIF image for this canvas
    iiif_image_id = models.URLField()
    #: :class:`Manifest` this canvas vbelongs to
    manifest = models.ForeignKey(
        Manifest, related_name="canvases", on_delete=models.CASCADE
    )
    #: boolean flag to indicate if this canvas should be used as thumbnail
    thumbnail = models.BooleanField(default=False)
    #: order of this canvas within associated manifest primary sequence
    order = models.PositiveIntegerField()
    # (for now only stores a single sequence, so just store order on the page)
    # format? size? (ocr text eventually?)
    #: extra data not otherwise given its own field, serialized as json
    extra_data = models.JSONField(default=dict)

    class Meta:
        ordering = ["manifest", "order"]
        verbose_name = "IIIF Canvas"
        verbose_name_plural = "IIIF Canvases"
        unique_together = ("short_id", "manifest")
        # add custom permissions; change and delete provided by django
        permissions = (("view_manifest", "Can view %s" % verbose_name),)

    def __str__(self):
        return "%s %d (%s)%s" % (
            self.manifest,
            self.order + 1,
            self.label,
            "*" if self.thumbnail else "",
        )

    @property
    def image(self):
        """Associated IIIF image for this canvas as :class:`IIIFImage`"""
        # NOTE: piffle iiif image wants service & id split out.
        # Should update to handle iiif image ids as provided in manifests
        # for now, split into service and image id. (is this reliable?)
        return IIIFImage(*self.iiif_image_id.rsplit("/", 1))

    @property
    def plain_text_url(self):
        """Return plain text url for a canvas if one exists"""

        rendering = self.extra_data.get("rendering", None)
        if rendering:
            # handle both cases where this is a list and where it is just
            # a dictionary, to be safe
            if isinstance(rendering, list):
                for item in rendering:
                    # iterate over the list and return the first plain text url
                    # we find
                    if "format" in item and item["format"] == "text/plain":
                        return item["@id"]
            else:
                # otherwise, if it's a dictionary, check if it's plaintext and
                # return
                if "format" in rendering and rendering["format"] == "text/plain":
                    return rendering["@id"]
        # finally return None if no plain text is available or no rendering
        return None

    @property
    def width(self):
        return self.extra_data.get("width", None)

    @property
    def height(self):
        return self.extra_data.get("height", None)

    def get_absolute_url(self):
        """'url for this canvas within the django site"""
        return reverse("djiffy:canvas", args=[self.manifest.short_id, self.short_id])

    def next(self):
        """Next canvas after this one in sequence (within manifest
        primary sequence).  Returns an empty queryset if there is no next
        canvas."""
        return Canvas.objects.filter(
            manifest=self.manifest, order__gt=self.order
        ).first()

    def prev(self):
        """Previous canvas before this one in sequence
        (within manifest primary sequence).  Returns an empty queryset
        if there is no next canvas."""
        return Canvas.objects.filter(
            manifest=self.manifest, order__lt=self.order
        ).last()

    def admin_thumbnail(self):
        """thumbnail for convenience display in admin interface"""
        return format_html('<img src="{}" />', self.image.mini_thumbnail())

    admin_thumbnail.short_description = "Thumbnail"
