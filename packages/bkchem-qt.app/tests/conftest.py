"""Shared pytest configuration for deterministic bkchem-qt tests."""

# Standard Library
import os

# Qt reads its platform choice when QApplication is initialized.  Set the
# headless test policy before importing any PySide6 module.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Suppress platform-plugin diagnostics during deterministic headless tests.
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")
