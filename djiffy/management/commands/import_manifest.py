from django.core.management.base import BaseCommand

from djiffy.importer import Importer

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('path', nargs='+',
            help='One or more IIIF Collections or Manifests as file or URL')

    def handle(self, *args, **kwargs):
        Importer(stdout=self.stdout, stderr=self.stderr, style=self.style) \
            .import_paths(kwargs['path'])



