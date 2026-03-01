"""Application bootstrap for BKChem-Qt."""

# Standard Library
import sys

# PIP3 modules
import PySide6.QtCore
import PySide6.QtWidgets

# local repo modules
import bkchem_qt.themes.theme_manager
import bkchem_qt.main_window

# application metadata
APP_NAME = "BKChem-Qt"
APP_ORG = "BKChem"
APP_VERSION = "26.02a1"


#============================================
def main(files: list = None) -> int:
	"""Create and run the BKChem-Qt application.

	Args:
		files: Optional list of file paths to open on launch.

	Returns:
		Application exit code from the Qt event loop.
	"""
	app = PySide6.QtWidgets.QApplication(sys.argv)

	# set application metadata
	app.setApplicationName(APP_NAME)
	app.setOrganizationName(APP_ORG)
	app.setApplicationVersion(APP_VERSION)

	# set up Qt built-in string translations
	translator = PySide6.QtCore.QTranslator(app)
	locale_name = PySide6.QtCore.QLocale.system().name()
	qt_translations_path = PySide6.QtCore.QLibraryInfo.path(
		PySide6.QtCore.QLibraryInfo.LibraryPath.TranslationsPath
	)
	# load Qt's own translations for the system locale
	if translator.load(f"qtbase_{locale_name}", qt_translations_path):
		app.installTranslator(translator)

	# create the theme manager, restore saved or system theme
	theme_mgr = bkchem_qt.themes.theme_manager.ThemeManager(app)
	theme_mgr.restore_theme()

	# create the main window
	window = bkchem_qt.main_window.MainWindow(theme_mgr)
	window.show()

	# restore saved geometry
	window.restore_geometry()

	# open command-line files (stub for Milestone 2)
	if files:
		for _filepath in files:
			# file opening will be implemented in Milestone 2
			pass

	# enter the event loop
	exit_code = app.exec()
	return exit_code
