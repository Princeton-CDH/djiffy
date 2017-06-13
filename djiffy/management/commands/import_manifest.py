'''
Generic manage command for importing IIIF Collections or manifests
nto the database. Supports collections and individual manifests,
and local file paths as well as URLs.
'''

from django.core.management.base import BaseCommand

from djiffy.importer import ManifestImporter

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('path', nargs='+',
            help='One or more IIIF Collections or Manifests as file or URL')

    def handle(self, *args, **kwargs):
        ManifestImporter(stdout=self.stdout, stderr=self.stderr,
                         style=self.style) \
            .import_paths(kwargs['path'])



