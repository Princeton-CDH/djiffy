from collections import OrderedDict
from django.core.management.base import BaseCommand

from djiffy.models import IfBook, IfPage, IIIFPresentation


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('path',
            help='IIIF Collection or Manifest as file or URL')

    def handle(self, *args, **kwargs):

        manifest = IIIFPresentation.from_file_or_url(kwargs['path'])
        if manifest.type == 'sc:Collection':
            # import all manifests in the collection
            for brief_manifest in manifest.manifests:
                # check if content is supported
                if not self.is_supported(brief_manifest):
                    continue
                print('Importing %s %s' % (brief_manifest.label, brief_manifest.id))

                manifest = IIIFPresentation.from_file_or_url(brief_manifest.id)
                if manifest:
                    self.import_book(manifest, brief_manifest.id)

        if manifest.type == 'sc:Manifest':
            if self.is_supported(manifest):
                print('Importing %s %s' % (manifest.label, manifest.id))
                self.import_book(manifest, kwargs['path'])

    def is_supported(self, manifest):
        print('viewing hint, direction = %s %s' % (manifest.viewingHint, manifest.viewingDirection))
        # FIXME: individuals vs paged?
        if manifest.viewingHint == 'paged' and \
           manifest.viewingDirection == 'left-to-right':
           return True

        self.stdout.write(self.style.ERROR('Currently import only supports paged, left-to-right manifests; skipping %s (%s, %s)' \
            % (manifest.id, manifest.viewingHint, manifest.viewingDirection)))
        return False

    def import_book(self, manifest, path):
        # check if book with uri identifier already exists
        if IfBook.objects.filter(uri=manifest.id).count():
            # NOTE: not updating for now; may want to add later
            self.stderr.write('%s has already been imported' % path)
            return
        # check if the type of manifest is supported
        if not self.is_supported(manifest):
            return

        # create a new book
        ifbk = IfBook()
        # TODO: how do we want to handle lists of labels?
        if len(manifest.label) == 1:
            ifbk.label = manifest.label[0]
        else:
            ifbk.label = '; '.join(manifest.label)
        ifbk.uri = manifest.id
        ifbk.short_id = self.short_id(manifest.id)
        # convert metadata into a more usable format
        metadata = OrderedDict([(item['label'], item['value'])
             for item in manifest.metadata])
        ifbk.metadata = metadata
        ifbk.save()

        thumbnail_id = None
        if hasattr(manifest, 'thumbnail'):
            thumbnail_id = manifest.thumbnail.service.id

        # for now, only worry about the first sequence
        order = 0
        # create a page for each canvas
        for canvas in manifest.sequences[0].canvases:
            ifpage = IfPage(book=ifbk, order=order)
            ifpage.label = canvas.label
            # this is canvas id, is that meaningful? do we want image id?
            ifpage.uri = canvas.id
            ifpage.short_id = self.short_id(canvas.id)
            # only support single image per canvas for now
            ifpage.iiif_image_id = canvas.images[0].resource.service.id
            # check if this page is the thumbnail image
            if thumbnail_id is not None and ifpage.iiif_image_id == thumbnail_id:
                ifpage.thumbnail = True
            ifpage.save()

            order += 1


    def short_id(self, uri):
        # generate a short id from full manifest/canvas uri identifiers
        # for use in urls

        # NOTE: very PUL specific for now, will need to be generalized or
        # adapted for other sources
        # example: https://plum.princeton.edu/concern/scanned_resources/ph415q7581/manifest
        # remove trailing /manifest at the end of the url
        if uri.endswith('/manifest'):
            uri = uri[:-len('/manifest')]
        # split on slashes and return the last portion
        return uri.split('/')[-1]


