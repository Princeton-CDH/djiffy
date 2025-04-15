djiffy
======

.. sphinx-start-marker-do-not-remove

Django application to index and display IIIF Manifests for books

.. image:: https://github.com/Princeton-CDH/djiffy/actions/workflows/unit_tests.yml/badge.svg
   :target: https://github.com/Princeton-CDH/djiffy/actions/workflows/unit_tests.yml
   :alt: Unit Tests status
.. image:: https://codecov.io/gh/Princeton-CDH/djiffy/branch/main/graph/badge.svg
   :target: https://codecov.io/gh/Princeton-CDH/djiffy
   :alt: Code Coverage
.. image:: https://img.shields.io/pypi/pyversions/djiffy
   :alt: PyPI - Python Version
.. image:: https://img.shields.io/pypi/djversions/djiffy
   :alt: PyPI - Django Version
.. image:: https://github.com/Princeton-CDH/djiffy/actions/workflows/sphinx_docs.yml/badge.svg
   :alt: Sphinx Docs build status


**djiffy** is intended to be a reusable `Django`_ application for
working with digitized book-like content provided via `IIIF Presentation`_
manifests.  This is an *alpha* version and it does *not* yet support
the full IIIF Presentation specification.

.. Note::
    djiffy is tested against Django 4.1-5.2 and Python 3.9-3.11.

.. _Django: https://www.djangoproject.com/
.. _IIIF Presentation: http://iiif.io/api/presentation/2.1/

Code documentation is available at https://princeton-cdh.github.io/djiffy/


Installation
------------

Use pip to install::

    pip install djiffy


You can also install from GitHub.  Use a branch or tag name, e.g.
``@develop`` or ``@1.0``, to install a specific tagged release or branch::

    pip install git+https://github.com/Princeton-CDH/djiffy.git@develop#egg=djiffy


Configuration
-------------

Add `djiffy` to installed applications and make sure that `django.contrib.humanize`
is also enabled::

    INSTALLED_APPS = (
        ...
        'django.contrib.humanize',
        'dal',
        'dal_select2',
        'djiffy',
        ...
    )


Include the default djiffy urls at the desired base url with the namespace
`djiffy`::

    urlpatterns = [
        ...
        url(r'^iiif-books/', include('djiffy.urls', namespace='djiffy')),
        ...
    ]

Run migrations to create database tables::

    python manage.py migrate

.. NOTE::

    The templates included require that you have a url configured with
    the name ``site-index``.


If you are need to use djiffy to access manifests that require an
authorization token, use **DJIFFY_AUTH_TOKENS** in your project settings
to configure each domain that requires an auth token.  The configuration
should be formatted like this::

    DJIFFY_AUTH_TOKENS = {
        'example.com': 'myauthtoken',
    }

Usage
-----

Import IIIF content using the `import_manifest` manage command.  This
command can take an IIIF Collection or single Manifest, via local file
or URL.  Imported content can be viewed in Django admin.::

    python manage.py import_manifest http://url.for/iiif/manifest
    python manage.py import_manifest /path/to/local/collection


Development instructions
------------------------

This git repository uses `git flow`_ branching conventions.

.. _git flow: https://github.com/nvie/gitflow

Initial setup and installation:

- recommended: create and activate a python 3.9 virtualenv::

    virtualenv djiffy -p python3.9
    source djiffy/bin/activate

- pip install the package with its python dependencies::

    pip install -e .


Upgrading to v1.0.0
^^^^^^^^^^^^^^^^^^^^

If you have used any version of ``djiffy`` prior to v1.0.0, then it is required
to upgrade to v0.9.2 first, and run all migrations on your Django project. The
Django project must be running Django version 3.2 at this point.

After you have run those migrations, you can upgrade to any Django version 3.2+,
and install ``djiffy`` v1.0.0.

Unit Testing
^^^^^^^^^^^^

Unit tests are written with `py.test <http://doc.pytest.org/>`_ but use some
Django test classes for convenience and compatibility with django test suites.
Running the tests requires a minimal settings file for Django required
configurations.

- Copy sample test settings and add a **SECRET_KEY**::

    cp ci/testsettings.py testsettings.py

- To run the tests, either use the configured setup.py test command::

    python setup.py test

- Or install test requirements and use py.test directly::

    pip install -e '.[test]'
    pytest

Documentation
^^^^^^^^^^^^^

Documentation is generated using `sphinx <http://www.sphinx-doc.org/>`_.
To generate documentation, first install development requirements::

    pip install -r dev-requirements.txt

Then build documentation using the customized make file in the `docs`
directory::

    cd sphinx-docs
    make html

As of v0.7.3, documentation is automatically built with GitHub Actions
and published using GitHub pages.

Adding license images
^^^^^^^^^^^^^^^^^^^^^

When adding new license image SVG files to this repo, add ``id="licenseimg"`` to
the ``<svg>`` element of each. This allows djiffy users to embed the SVG inline
with a ``<use>`` tag, with its ``href`` attribute pointing to ``#licenseimg``.

If the image will need to be recolored for different backgrounds, as in the
case of the ``rightsstatement_org/`` SVG icons, you can enable this for up to
two tones in each SVG. To do this, set ``fill`` attributes on paths to
``fill="inherit"`` (controlled by the ``fill`` CSS property) or
``fill="currentColor"`` (controlled by the ``color`` CSS property).

License
-------

**djiffy** is distributed under the Apache 2.0 License.

©2024 Trustees of Princeton University.  Permission granted via
Princeton Docket #20-3618 for distribution online under a standard Open Source
license.  Ownership rights transferred to Rebecca Koeser provided software
is distributed online via open source.
