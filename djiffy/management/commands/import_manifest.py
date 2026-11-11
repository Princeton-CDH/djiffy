'''
Generic manage command for importing IIIF Collections or manifests
into the database. Supports collections and individual manifests,
and local file paths as well as URLs.
'''

from django.core.management.base import BaseCommand

from djiffy.importer import ManifestImporter
from djiffy.models import Manifest


class Command(BaseCommand):
    '''Import IIIF Collections or Manifests into the local database.'''
    help = __doc__

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        # default=[] is required for the group to work on older Pythons
        group.add_argument('path', nargs='*', default=[],
            help='One or more IIIF Collections or Manifests as file or URL')
        group.add_argument('--all', action='store_true', dest='update_all',
            help='Re-import and update all manifests already in the database')
        parser.add_argument('--update', action='store_true',
            help='Update previously imported manifests')

    def handle(self, *args, **kwargs):
        paths = kwargs['path']
        update = kwargs['update']

        if kwargs['update_all']:
            paths = list(Manifest.objects.values_list('uri', flat=True))
            # --all only makes sense as an update
            update = True

        ManifestImporter(stdout=self.stdout, stderr=self.stderr,
                         style=self.style, update=update) \
            .import_paths(paths)
