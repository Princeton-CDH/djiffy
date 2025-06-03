Changelog
=========

1.0
---

* Reintroduce updates for django 4.0 and newer versions of python
  (breaking change for users of djiffy <= 0.9.1; must first upgrade to 0.9.2)


0.9.2
-----

* bugfix: Restore replaced migrations to resolve migration dependency issues


0.9.1
-----

* Relax minimum django version requirement to 3.2
  (only tested against 4.2-5.1, but expected to be compatible with 3.2+)


0.9
---

* Expand license image logic to handle standard CC licenses
* Updated for compatibility with python 3.9-3.11
* Updated for compatibility with django 4.2-5.1


0.8
---

* Manifest dynamic properties for license uris and labels are now cached
* Manifest license logic now handles CreativeCommons license URIs.
* Images for rightstatement.org and some CC licenses are now included in static content
* License image path can be generated using the `license_image` property for Manifests with supported licenses

0.7.3
-----

* `ManifestImporter.import_paths` now returns a list of database manifest
   objects for the requested uris, whether newly imported or already available
* Setup GitHub Actions workflow for sphinx documentation


0.7.2
-----

* Include manifest attribution information in ``extra_data`` on import


0.7.1
-----

* Improved error handling for connection errors when importing IIIF manifests

0.7
---

* Now tested against  Django 3.1 and 3.2; dropped support for Django 1.11 and 2.2
* Now tested on python 3.7, 3.8; dropped support for python 3.5 and 3.6
* Shifted continuous integration from Travis-CI to GitHub Actions
* Admin thumbnail format is now configurable in django settings via **DJIFFY_THUMBNAIL_FORMAT**; default is png
* Manifest import check for "supported" manifests can be disabled by setting **DJIFFY_IMPORT_CHECK_SUPPORTED** to False in django settings
* Canvas data now includes dimensions, with convenience properties `width` and `height`

0.6
---

* Now supports Django 1.11 through 3.0; dropped support for Django 1.10


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
