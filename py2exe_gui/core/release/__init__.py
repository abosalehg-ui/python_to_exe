"""The release pipeline: from a version bump to a published GitHub release.

Each step lives in its own module and can be run, tested and repeated on its
own (``versioning``, ``changelog``, ``artifacts``, ``checksums``,
``github``, ``winget``); ``pipeline`` composes them, with a dry-run mode that
reports every action without performing any. UI-free, like the rest of core.
"""
