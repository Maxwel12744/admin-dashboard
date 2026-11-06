"""Stores uploaded images (profile pictures) in Cloudinary instead of on disk.

Vercel has no permanent disk, so files saved to the media folder are lost.
Django asks this class to save, delete and build the web address of each file.

The name kept in your database looks like  avatars/3f9c...e1.jpg
(the Cloudinary public id, a dot, and the image format).
"""
import os
import uuid

import cloudinary
import cloudinary.uploader
import cloudinary.utils
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class CloudinaryMediaStorage(Storage):
    # Small square pictures are all the dashboard needs, so Cloudinary resizes them.
    transformation = {
        "width": 256,
        "height": 256,
        "crop": "fill",
        "gravity": "auto",
        "quality": "auto",
        "fetch_format": "auto",
    }

    def _save(self, name, content):
        # A random name, so two people uploading "me.jpg" never overwrite each other.
        folder = os.path.dirname(name)
        public_id = uuid.uuid4().hex
        if folder:
            public_id = f"{folder}/{public_id}"
        content.seek(0)
        result = cloudinary.uploader.upload(
            content,
            public_id=public_id,
            resource_type="image",
            overwrite=False,
        )
        return f"{result['public_id']}.{result['format']}"

    def _split(self, name):
        public_id, _, extension = name.rpartition(".")
        if not public_id:  # no dot in the name
            return name, None
        return public_id, extension

    def url(self, name):
        public_id, extension = self._split(name)
        options = dict(self.transformation, secure=True)
        if extension:
            options["format"] = extension
        return cloudinary.utils.cloudinary_url(public_id, **options)[0]

    def delete(self, name):
        if not name:
            return
        public_id, _ = self._split(name)
        cloudinary.uploader.destroy(public_id, resource_type="image", invalidate=True)

    def exists(self, name):
        # Names are random, so a clash is practically impossible. Returning False
        # saves a network call on every upload.
        return False

    def _open(self, name, mode="rb"):
        raise NotImplementedError("Pictures are shown from their Cloudinary web address.")

    def size(self, name):
        raise NotImplementedError("Cloudinary pictures have no local size.")

    def listdir(self, path):
        raise NotImplementedError("Listing Cloudinary folders is not supported.")