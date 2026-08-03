#!/usr/bin/env python3

"""Render one Qt-owned SVG application icon into one square PNG."""

# Standard Library
import argparse
import pathlib

# PIP3 modules
from PySide6.QtCore import QSize
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


#============================================
def parse_args() -> argparse.Namespace:
	"""Parse one explicit SVG-to-PNG render request.

	Returns:
		Parsed renderer arguments.
	"""
	parser = argparse.ArgumentParser(description="Render one Qt SVG application icon PNG.")
	parser.add_argument("--source", required=True, type=pathlib.Path, help="Qt-owned SVG source.")
	parser.add_argument("--size", required=True, type=int, help="Square PNG pixel size.")
	parser.add_argument("--output", required=True, type=pathlib.Path, help="New PNG output path.")
	args = parser.parse_args()
	if args.size <= 0:
		parser.error("--size must be positive")
	return args


#============================================
def render_icon(source: pathlib.Path, size: int, output: pathlib.Path) -> None:
	"""Render one valid SVG source into a transparent square PNG.

	Args:
		source: Existing Qt-owned SVG source.
		size: Requested square output size in pixels.
		output: PNG path written by this renderer.

	Raises:
		RuntimeError: If Qt cannot load the SVG or write the PNG.
	"""
	renderer = QSvgRenderer(str(source))
	if not renderer.isValid():
		raise RuntimeError(f"Qt could not load SVG icon: {source}")
	image = QImage(QSize(size, size), QImage.Format.Format_RGBA8888)
	image.fill(0)
	painter = QPainter(image)
	renderer.render(painter)
	painter.end()
	output.parent.mkdir(parents=True, exist_ok=True)
	if not image.save(str(output), "PNG"):
		raise RuntimeError(f"Qt could not write PNG icon: {output}")


#============================================
def main() -> None:
	"""Run one explicit Qt SVG-to-PNG request."""
	args = parse_args()
	render_icon(args.source, args.size, args.output)


#============================================

if __name__ == "__main__":
	main()
