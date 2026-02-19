#!/bin/bash

DOCBOOK_SOURCE="docs/legacy/doc.xml"

if [ -f "${DOCBOOK_SOURCE}" ]; then
	DOCBOOK_DIR="$(dirname "${DOCBOOK_SOURCE}")"
	mkdir -p "${DOCBOOK_DIR}/html"
	docbook2html "${DOCBOOK_SOURCE}" -o "${DOCBOOK_DIR}/html" 2>/dev/null
	docbook2pdf "${DOCBOOK_SOURCE}" 2>/dev/null
else
	echo "DocBook sources removed; use Markdown docs in docs/."
fi

cp -v locale/pot/BKChem.pot locale/

echo "Compiling *.po files..."
cd locale/pot
./compile_l10ns.sh
cd ../..

echo "convert the logo to ppm"
echo "release number in:"
echo "images/logo.xcf"
echo "bkchem/config.py"
echo "pyproject.toml"
echo "RELEASE"
echo
echo "set config.debug to 0"
