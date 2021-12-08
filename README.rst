djiffy
======

.. sphinx-start-marker-do-not-remove

Django application to index and display IIIF Manifests for books

.. image:: https://travis-ci.org/Princeton-CDH/djiffy.svg?branch=develop
   :target: https://travis-ci.org/Princeton-CDH/djiffy
   :alt: Build Status
.. image:: https://codecov.io/gh/Princeton-CDH/djiffy/branch/develop/graph/badge.svg
   :target: https://codecov.io/gh/Princeton-CDH/djiffy
   :alt: Code Coverage
.. image:: https://landscape.io/github/Princeton-CDH/djiffy/develop/landscape.svg?style=flat
   :target: https://landscape.io/github/Princeton-CDH/djiffy/develop
   :alt: Code Health
.. image:: https://requires.io/github/Princeton-CDH/djiffy/requirements.svg?branch=develop
   :target: https://requires.io/github/Princeton-CDH/djiffy/requirements/?branch=develop
   :alt: Requirements Status
.. image:: https://img.shields.io/pypi/pyversions/djiffy
   :alt: PyPI - Python Version
.. image:: https://img.shields.io/pypi/djversions/djiffy
   :alt: PyPI - Django Version



**djiffy** is intended to be a reusable `Django`_ application for
working with digitized book content provided via `IIIF Presentation`_
manifests.  This is an *alpha* version and it does *not* yet support
the full IIIF Presentation specification.

.. Note::
    djiffy is tested against Django 2.2 through 3.1.

.. _Django: https://www.djangoproject.com/
.. _IIIF Presentation: http://iiif.io/api/presentation/2.1/


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

- recommended: create and activate a python 3.5 virtualenv::

    virtualenv djiffy -p python3.5
    source djiffy/bin/activate

- pip install the package with its python dependencies::

    pip install -e .


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

To build and publish documentation for a release, add the ``gh-pages`` branch
to the ``docs`` folder in your worktree::

    git worktree add -B gh-pages docs origin/gh-pages

In the ``sphinx-docs`` folder, use ``make docs`` to build the HTML documents
and static assets, add it to the docs folder, and commit it for publication on
Github Pages. After the build completes, push to GitHub from the ``docs`` folder.

License
-------

**djiffy** is distributed under the Apache 2.0 License.

©2019 Trustees of Princeton University.  Permission granted via
Princeton Docket #20-3618 for distribution online under a standard Open Source
license.  Ownership rights transferred to Rebecca Koeser provided software
is distributed online via open source.