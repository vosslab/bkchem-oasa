"""Shared ownership marker for BKChem-created clipboard MIME data."""

# Dynamic QObject property used to identify Python-wrapped MIME objects which
# must be released before interpreter shutdown.
BKCHEM_OWNED_MIME_PROPERTY = "bkchem_qt_owned_mime_data"
