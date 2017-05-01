from collections import OrderedDict
from django.core.management.base import BaseCommand

from djiffy.models import Manifest, Canvas, IIIFPresentation, IIIFException


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('path',
            help='IIIF Collection or Manifest as file or URL')

    def handle(self, *args, **kwargs):
        try:
            manifest = IIIFPresentation.from_file_or_url(kwargs['path'])
        except IIIFException as err:
            self.stderr.write(str(err))
            return

        if manifest.type == 'sc:Collection':
            # import all manifests in the collection
            for brief_manifest in manifest.manifests:
                # check if content is supported
                if hasattr(brief_manifest, 'viewingHint') or \
                  hasattr(brief_manifest, 'viewingDirection'):
                    if not self.is_supported(brief_manifest):
                        continue
                self.stdout.write('Importing %s %s' % \
                    (brief_manifest.label, brief_manifest.id))

                try:
                    manifest = IIIFPresentation.from_file_or_url(brief_manifest.id)
                except IIIFException as err:
                    manifest = None
                    self.stderr.write(str(err))

                if manifest:
                    self.import_book(manifest, brief_manifest.id)

        if manifest.type == 'sc:Manifest':
            if self.is_supported(manifest):
                self.stdout.write('Importing %s %s' % \
                    (manifest.label, manifest.id))
                self.import_book(manifest, kwargs['path'])

    def is_supported(self, manifest):
        # print('viewing hint, direction = %s %s' % (manifest.viewingHint,
            # getattr(manifest, 'viewingDirection', None)))
        # FIXME: individuals vs paged?
        view_hint = getattr(manifest, 'viewingHint', None)
        view_direction = getattr(manifest, 'viewingDirection', None)
        if (view_hint and manifest.viewingHint == 'paged') or \
           (view_direction and manifest.viewingDirection == 'left-to-right'):
           return True

        self.stdout.write(self.style.ERROR('Currently import only supports paged, left-to-right manifests; skipping %s (%s, %s)' \
            % (manifest.id, manifest.viewingHint, manifest.viewingDirection)))
        return False

    def import_book(self, manifest, path):
        # check if book with uri identifier already exists
        if Manifest.objects.filter(uri=manifest.id).count():
            # NOTE: not updating for now; may want to add later
            self.stderr.write('%s has already been imported' % path)
            return
        # check if the type of manifest is supported
        if not self.is_supported(manifest):
            return

        # create a new book
        manif = Manifest()

        # label can be either a list/tuple or a bare string; handle both
        # TODO: generalize this and move into model classes
        if isinstance(manifest.label, str):
            manif.label = manifest.label
        else:
            if len(manifest.label) == 1:
                manif.label = manifest.label[0]
            else:
                manif.label = '; '.join(manifest.label)

        manif.uri = manifest.id
        manif.short_id = IIIFPresentation.short_id(manifest.id)
        # convert metadata into a more usable format
        metadata = OrderedDict([(item['label'], item['value'])
             for item in manifest.metadata])
        # handle single values as well as lists
        for key, value in metadata.items():
            if not isinstance(value, list):
                metadata[key] = (value, )
        manif.metadata = metadata
        manif.save()

        thumbnail_id = None
        if hasattr(manifest, 'thumbnail'):
            thumbnail_id = manifest.thumbnail.service.id

        # for now, only worry about the first sequence
        order = 0
        # create a db canvas element for each canvas
        for canvas in manifest.sequences[0].canvases:
            db_canvas = Canvas(manifest=manif, order=order)
            db_canvas.label = canvas.label
            # this is canvas id, is that meaningful? do we want image id?
            db_canvas.uri = canvas.id
            db_canvas.short_id = IIIFPresentation.short_id(canvas.id)
            # only support single image per canvas for now
            db_canvas.iiif_image_id = canvas.images[0].resource.service.id
            # check if this page is the thumbnail image
            if thumbnail_id is not None and db_canvas.iiif_image_id == thumbnail_id:
                db_canvas.thumbnail = True
            db_canvas.save()

            order += 1


