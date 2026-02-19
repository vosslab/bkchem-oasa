#--------------------------------------------------------------------------
#     This file is part of OASA - a free chemical python library
#--------------------------------------------------------------------------

"""CML 2.0 wrappers built on top of the shared CML helpers."""

# local repo modules
from oasa.codecs import cml


_VERSION = "2"


#============================================
def text_to_mol(text):
	return cml.text_to_mol(text, version=_VERSION)


#============================================
def file_to_mol(file_obj):
	return cml.file_to_mol(file_obj, version=_VERSION)
