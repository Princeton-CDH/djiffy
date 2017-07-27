from collections import OrderedDict

from djiffy.models import Manifest, Canvas, IIIFPresentation, IIIFException, \
    get_iiif_url


class ManifestImporter(object):
    '''Manifest importer.  Intended for use with Django manage commands.

    :param stdout: optional stdout, if status output is desired
    :param stderr: optional stderr, if error output is desired
    :param style: optional django command style object, for styled output
    '''

    stdout = None
    stderr = None
    style = None
    # verbosity level?

    # TODO: should have better reporting on what was done

    def __init__(self, stdout=None, stderr=None, style=None):
        self.stdout = stdout
        self.stderr = stderr
        self.style = style

    def output(self, msg):
        '''Output a message if stdout is configured (used to support output
        via manage command)'''
        if self.stdout:
            self.stdout.write(msg)

    def error_msg(self, msg):
        '''Output an error message if stderr is configured (used to support output
        via manage command).  '''
        if self.stderr:
            if self.style:
                msg = self.style.ERROR(msg)
            self.stderr.write(msg)

    def import_paths(self, paths):
        '''Import a list of paths - file or url, collection or manifest.'''
        for path in paths:
            try:
                manifest = IIIFPresentation.from_file_or_url(path)
            except IIIFException as err:
                self.stderr.write(str(err))
                continue

            if manifest.type == 'sc:Collection':
                self.import_collection(manifest)

            if manifest.type == 'sc:Manifest':
                self.import_manifest(manifest, path)

    def import_supported(self, manifest):
        '''Check if import is supported (currently limited to paged,
        left-to-right content).'''
        # FIXME: individuals vs paged?
        view_hint = getattr(manifest, 'viewingHint', None)
        view_direction = getattr(manifest, 'viewingDirection', None)
        if (view_hint and manifest.viewingHint == 'paged') or \
          (view_direction and manifest.viewingDirection == 'left-to-right'):
            return True

        else:
            self.error_msg('Currently import only supports paged, left-to-right manifests; skipping %s (hint: %s, direction: %s)' \
            % (manifest.id, view_hint, view_direction))
            return False

    def import_manifest(self, manifest, path):
        '''Process a single IIIF manifest and create
        :class:`~djiffy.models.Manifest` and
        :class:`~djiffy.models.Canvas` objects.

        :param manifest: :class:`~djiffy.models.IIIFPresentation`
        :param path: file or url import path
        '''

        # check if manifest with uri identifier has already been imported
        if Manifest.objects.filter(uri=manifest.id).count():
            # NOTE: not updating for now; may want to add later
            self.error_msg('%s has already been imported' % path)
            return
        # check if the type of manifest is supported
        if not self.import_supported(manifest):
            return

        # make sure the manifest has sequences defined
        # (workaround for a bug in Plum)
        try:
            getattr(manifest, 'sequences')
        except AttributeError:
            self.error_msg('%s has no sequences; skipping' % path)
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
        if hasattr(manifest, 'metadata'):
            metadata = OrderedDict([(item['label'], item['value'])
                 for item in manifest.metadata])
            # handle single values as well as lists
            for key, value in metadata.items():
                if not isinstance(value, list):
                    metadata[key] = (value, )
            manif.metadata = metadata

        # if manifest has any seeAlso links, store the urls;
        # if format is JSON, fetch it and store in the extra data
        # NOTE: primary reason for this is to store the ARK identifier
        # if there is one, since that will be more permanent than
        # the manifest id; extra data may also include important
        # rights information
        if hasattr(manifest, 'seeAlso'):
            links = []
            manif.extra_data = OrderedDict()
            # collect seeAlso links and formats, whether they
            # appear as a single element or a list

            # single link, not in a list
            if hasattr(manifest.seeAlso, 'format'):
                links.append((manifest.seeAlso.id, manifest.seeAlso.format))
            # list of seeAlso links
            else:
                for see_also in manifest.seeAlso:
                    links.append((see_also.id, see_also.format))

            # process all the seeAlso links and add to extra data
            for url, fmt in links:
                manif.extra_data[url] = {}
                if fmt == 'application/ld+json':
                    # TODO: error handling on the request?
                    response = get_iiif_url(url)
                    manif.extra_data[url] = response.json()

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

        # return the manifest db object that was created
        return manif

    def import_collection(self, manifest):
        '''Process a single IIIF collection and import
        all supported manifests referenced in the collection.

        :param manifest: :class:`~djiffy.models.IIIFPresentation`
        '''

        if manifest.type == 'sc:Collection':
            # import all manifests in the collection
            imported = []
            for brief_manifest in manifest.manifests:
                # check if content is supported
                if hasattr(brief_manifest, 'viewingHint') or \
                  hasattr(brief_manifest, 'viewingDirection'):
                    if not self.import_supported(brief_manifest):
                        continue
                self.output('Importing "%s" %s' % \
                    (brief_manifest.first_label, brief_manifest.id))

                try:
                    manifest = IIIFPresentation.from_file_or_url(brief_manifest.id)
                except IIIFException as err:
                    manifest = None
                    self.error_msg(str(err))

                if manifest:
                    db_manifest = self.import_manifest(manifest, brief_manifest.id)
                    imported.append(db_manifest)

            return imported



