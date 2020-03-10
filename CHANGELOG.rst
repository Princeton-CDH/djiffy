Changelog
=========

0.6
---

* Now supports Django 1.11 through 2.2; dropped support for Django 1.10


0.5.2 Maintenance release
---------------------------

* Update for pytest 5.x and mysql change on Travis-CI


0.5.1
-----

* Fix pytest version requirement for failing build on Travis-CI

0.5
---

* New method on Manifest object to get text label for rights license

0.4.1
-----
* Fix a git merge issue that resulted in some code not being merged into master

0.4
---
* Canvas now has extra_data field to capture additional manifest information
  (currently `rendering`) as part of the import.
* Canvas has `plain_text_url` property to supply url for plain-text
  transcription/OCR if available from manifest.


0.3
---

* Import script now supports updating previously imported manifests;
  use `--update` option.
* Import script now allows manifests with viewing hint 'individuals'
  as well as paged.
* Manifest object now has properties for logo, license, and
  rightstatement.org id
* Canvas short id logic can be customized in ManifestImporter subclasses
* Project app verbose name is now 'IIIF Content' for listing in Django
  admin, so it will be more meaningful & recognizable to users
* Minor template improvements
* bugfix: ManifestSelectWidget now handles empty string


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
