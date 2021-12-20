from collections import OrderedDict

from django.conf import settings

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

    check_import_supported = getattr(settings, 'DJIFFY_IMPORT_CHECK_SUPPORTED', True)

    # TODO: should have better reporting on what was done

    def __init__(self, stdout=None, stderr=None, style=None, update=False):
        self.stdout = stdout
        self.stderr = stderr
        self.style = style
        self.update = update

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
        '''Check if import is supported (currently limited to paged or individuals,
        left-to-right content).'''

        # if import check is disabled, bypass checks and return true
        if not self.check_import_supported:
            return True

        view_hint = getattr(manifest, 'viewingHint', None)
        view_direction = getattr(manifest, 'viewingDirection', None)
        if (view_hint and manifest.viewingHint in ['paged', 'individuals', None]) or \
          (view_direction and manifest.viewingDirection in ['left-to-right', 'right-to-left']):
            return True

        else:
            self.error_msg('Currently import only supports paged or individuals, left-to-right manifests; skipping %s (hint: %s, direction: %s)' \
            % (manifest.id, view_hint, view_direction))
            return False

    def import_manifest(self, manifest, path):
        '''Process a single IIIF manifest and create
        :class:`~djiffy.models.Manifest` and
        :class:`~djiffy.models.Canvas` objects.

        :param manifest: :class:`~djiffy.models.IIIFPresentation`
        :param path: file or url import path
        '''

        self.output('Importing %s' % path)

        # flag to indicate if we are updating an existing record
        update_existing = False

        # check if manifest with uri identifier has already been imported
        db_manifest = Manifest.objects.filter(uri=manifest.id).first()
        if db_manifest:
            # TODO: would be nice to compare last-modified or etag
            # and see if we actually need to update..
            # NOTE: not updating for now; may want to add later
            if self.update:
                update_existing = True
            else:
                self.error_msg('%s has already been imported; use --update to request update' % path)
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

        # create a new manifest if not updating a previous import
        if not update_existing:
            db_manifest = Manifest()

        # label can be either a list/tuple or a bare string; handle both
        # TODO: generalize this and move into model classes
        if isinstance(manifest.label, str):
            db_manifest.label = manifest.label
        else:
            if len(manifest.label) == 1:
                db_manifest.label = manifest.label[0]
            else:
                db_manifest.label = '; '.join(manifest.label)

        # set uri & short id if creating a new record
        if not update_existing:
            db_manifest.uri = manifest.id
            db_manifest.short_id = IIIFPresentation.short_id(manifest.id)
        # convert metadata into a more usable format
        if hasattr(manifest, 'metadata'):
            metadata = OrderedDict([(item['label'], item['value'])
                 for item in manifest.metadata])
            # handle single values as well as lists
            for key, value in metadata.items():
                if not isinstance(value, list):
                    metadata[key] = [value]
            db_manifest.metadata = metadata

        # if manifest has any seeAlso links, store the urls;
        # if format is JSON, fetch it and store in the extra data
        # NOTE: primary reason for this is to store the ARK identifier
        # if there is one, since that will be more permanent than
        # the manifest id; extra data may also include important
        # rights information
        if hasattr(manifest, 'seeAlso'):
            links = []
            db_manifest.extra_data = OrderedDict()
            # collect seeAlso links and formats, whether they
            # appear as a single element or a list

            # single link, not in a list
            if isinstance(manifest.seeAlso, str):
                # link with no format
                links.append((manifest.seeAlso, ''))
            elif hasattr(manifest.seeAlso, 'format'):
                links.append((manifest.seeAlso.id, manifest.seeAlso.format))
            # list of seeAlso links
            else:
                for see_also in manifest.seeAlso:
                    links.append((see_also.id, see_also.format))

            # process all the seeAlso links and add to extra data
            for url, fmt in links:
                db_manifest.extra_data[url] = {}
                if fmt == 'application/ld+json':
                    # TODO: error handling on the request?
                    response = get_iiif_url(url)
                    db_manifest.extra_data[url] = response.json()

        # also check for logo and license and add to extra data
        for field in ['logo', 'license']:
            if hasattr(manifest, field):
                db_manifest.extra_data[field] = getattr(manifest, field)

        db_manifest.save()

        thumbnail_id = None
        if hasattr(manifest, 'thumbnail'):
            # if available as IIIF image, use that
            if hasattr(manifest.thumbnail, 'service'):
                thumbnail_id = manifest.thumbnail.service.id
            # otherwise, id is a path to an image
            else:
                thumbnail_id = manifest.thumbnail.id

        # for now, only worry about the first sequence
        # create a db canvas element for each canvas
        for order, canvas in enumerate(manifest.sequences[0].canvases):
            # when updating an existing manifest, look for existing canvas
            if update_existing:
                db_canvas = db_manifest.canvases.filter(uri=canvas.id).first()
            if not update_existing or not db_canvas:
                # otherwise, create a new canvas (new import or updating
                # a manifest where this canvas did not previously exist)
                db_canvas = Canvas(manifest=db_manifest)

            # set order and label
            db_canvas.order = order
            db_canvas.label = canvas.label

            # keep canvas id to obscure image id if necessary for security
            db_canvas.uri = canvas.id
            # get short id (extensible for subclasses)
            db_canvas.short_id = self.canvas_short_id(canvas)
            # only support single image per canvas for now
            db_canvas.iiif_image_id = canvas.images[0].resource.service.id
            # check if this page is the thumbnail image
            if thumbnail_id is not None and db_canvas.iiif_image_id == thumbnail_id:
                db_canvas.thumbnail = True

            # include other fields as extra_data for now
            for field in ['rendering', 'width', 'height']:
                if hasattr(canvas, field):
                    db_canvas.extra_data[field] = getattr(canvas, field)
            db_canvas.save()

        # if updating, check for previously imported canvases that are no
        # longer preseent
        if update_existing:
            # get a list of all ids in the db
            all_ids = db_manifest.canvases.all().values_list('uri', flat=True)
            # get all ids in the current manifest
            current_ids = [canvas.id for canvas in manifest.sequences[0].canvases]
            # identify outdated ids in the database but not the manifest
            outdated_ids = set(all_ids).difference(set(current_ids))
            if outdated_ids:
                outdated_canvases = db_manifest.canvases.filter(uri__in=outdated_ids)
                if outdated_canvases:
                    self.output('Updating %s; removing %d canvases no longer included' % \
                        (manifest.id, len(outdated_canvases)))
                    outdated_canvases.delete()

        # return the manifest db object that was created
        return db_manifest

    def import_collection(self, manifest):
        '''Process a single IIIF collection and import
        all supported manifests referenced in the collection.

        :gedram manifest: :class:`~djiffy.models.IIIFPresentation`
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

    def canvas_short_id(self, canvas):
        '''Method for generating short id from canvas; default is
        :meth:`djiffy.models.IIIFPresentation.short_id`.
        '''
        return IIIFPresentation.short_id(canvas.id)
