Changelog
=========

0.3
---

* Import script now supports updating previously imported manifests.
* Import script now allows manifests with viewing hint 'individuals'
  as well as paged.


0.2
---

* Support for optional configurable per-domain auth tokens, to
  allow retrieving restricted IIIF manifests.  (See documentation
  in the README for **DJIFFY_AUTH_TOKENS** format.)
* New custom Django view permissions for manifests and canvases.
* Now supports Django 1.11.
* Manifest extra data is restructured and includes seeAlso URLs even
  if content is not included locally.
* Canvas autocomplete view powered by django-autocomplete-light, to support
  selecting canvases in admin forms without loading all canvases in
  the database.

0.1 Initial release
--------------------

* Simple database models for caching IIIF Manifest and Canvas information
  intended to support paged content
* Basic manifest and canvas views to navigate and view content;
  manifest/canvas templates adapted from `Readux`_
* Manage command for importing IIIF Collections and Manifests into the
  local database, designed to be extended to support customized import
  logic.

.. _Readux: https://github.com/ecds/readux
