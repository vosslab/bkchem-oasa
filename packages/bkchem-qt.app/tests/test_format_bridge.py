"""Behavior coverage for frontend-neutral codec capability queries."""

# local repo modules
import oasa.codec_registry

import bkchem_qt.io.format_bridge


#============================================
def test_export_formats_initialize_the_public_codec_registry() -> None:
	"""A fresh registry still reports native document and molecule writers."""
	oasa.codec_registry.reset_registry()
	formats = bkchem_qt.io.format_bridge.get_supported_export_formats()
	assert ".cdml" in formats and ".mol" in formats
