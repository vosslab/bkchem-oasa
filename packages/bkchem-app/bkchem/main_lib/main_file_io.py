"""File I/O mixin methods for BKChem main application."""

import os

import tkinter.messagebox
from tkinter.filedialog import asksaveasfilename, askopenfilename

from bkchem import bkchem_utils
from bkchem import export
from bkchem import format_loader
from bkchem import safe_xml
from bkchem import data
from bkchem.singleton_store import Store

# chemistry file extensions that the Open dialog should recognize
_CHEM_EXTENSIONS = {
	".mol": "molfile",
	".sdf": "sdf",
	".smi": "smiles",
	".smiles": "smiles",
	".inchi": "inchi",
	".cml": "cml",
	".cdxml": "cdxml",
	".sma": "smarts",
}

import builtins
# gettext i18n translation fallback
_ = builtins.__dict__.get( '_', lambda m: m)


class MainFileIOMixin:
	"""File save/load helpers extracted from main.py."""

	def save_CDML( self, name=None, update_default_dir=1):
		"""saves content of self.paper (recent paper) under its filename,
		if the filename was automaticaly given by bkchem it will call save_as_CDML
		in order to ask for the name"""
		if not name:
			if self.paper.file_name['auto']:
				self.save_as_CDML()
				return
			else:
				a = os.path.join( self.paper.file_name['dir'], self.paper.file_name['name'])
				return self._save_according_to_extension( a, update_default_dir=update_default_dir)
		else:
			return self._save_according_to_extension( name, update_default_dir=update_default_dir)


	def save_as_CDML( self):
		"""asks the user the name for a file and saves the current paper there,
		dir and name should be given as starting values"""
		d = self.paper.file_name['dir']
		name = self.paper.file_name['name']
		a = asksaveasfilename( defaultextension = ".svg", initialdir = d, initialfile = name,
													title = _("Save As..."), parent = self,
													filetypes=((_("CD-SVG file"),".svg"),
																			(_("Gzipped CD-SVG file"),".svgz"),
																			(_("CDML file"),".cdml"),
																			(_("Gzipped CDML file"),".cdgz")))
		if a != '' and a!=():
			if self._save_according_to_extension( a):
				name = self.get_name_dic( a)
				if self.check_if_the_file_is_opened( name['name'], check_current=0):
					tkinter.messagebox.showerror( _("File already opened!"), _("Sorry but you are already editing a file with this name (%s), please choose a different name or close the other file.") % name['name'])
					return None
				self.paper.file_name = self.get_name_dic( a)
				tab_name = self.get_paper_tab_name(self.paper)
				frame = self._tab_name_2_frame.get(tab_name)
				if frame:
					self.notebook.tab(frame, text=self.paper.file_name['name'])
				return self.paper.file_name
			else:
				return None
		else:
			return None


	def _save_according_to_extension( self, filename, update_default_dir=1):
		"""decides the format from the file extension and saves self.paper in it"""
		save_dir, save_file = os.path.split( filename)
		if update_default_dir:
			self.save_dir = save_dir
		ext = os.path.splitext( filename)[1]
		if ext == '.cdgz':
			type = _('gzipped CDML')
			success = export.export_CDML( self.paper, filename, gzipped=1)
		elif ext == '.cdml':
			type = _('CDML')
			success = export.export_CDML( self.paper, filename, gzipped=0)
		elif ext == '.svgz':
			type = _('gzipped CD-SVG')
			success = export.export_CD_SVG( self.paper, filename, gzipped=1)
		else:
			type = _('CD-SVG')
			success = export.export_CD_SVG( self.paper, filename, gzipped=0)
		if success:
			Store.log( _("saved to %s file: %s") % (type, os.path.abspath( os.path.join( save_dir, save_file))))
			self._record_recent_file( os.path.abspath( os.path.join( save_dir, save_file)))
			self.paper.changes_made = 0
			return 1
		else:
			Store.log( _("failed to save to %s file: %s") % (type, save_file))
			return 0


	def set_file_name( self, name, check_ext=0):
		"""if check_ext is true append a .svg extension if no is present"""
		if check_ext and not os.path.splitext( name)[1]:
			self.paper.file_name = self.get_name_dic( name + ".svg", local_file=1)
		else:
			self.paper.file_name = self.get_name_dic( name, local_file=1)
		tab_name = self.get_paper_tab_name(self.paper)
		frame = self._tab_name_2_frame.get(tab_name)
		if frame:
			self.notebook.tab(frame, text=self.paper.file_name['name'])


	def load_CDML( self, file=None, replace=0):
		"""loads a file into a new paper or the current one (depending on replace value),
		file is the name of the file to load (if not supplied dialog is fired),
		if replace == 0 the content of the file is added to the current content of the file"""
		if not file:
			if self.paper.changes_made and replace:
				if tkinter.messagebox.askokcancel( _("Forget changes?"),_("Forget changes in currently visiting file?"), default='ok', parent=self) == 0:
					return 0
			a = askopenfilename( defaultextension = "",
													initialdir = self.save_dir,
													title = _("Load"),
													parent = self,
													filetypes=((_("All native formats"), (".svg", ".svgz", ".cdml", ".cdgz")),
																			(_("CD-SVG file"), ".svg"),
																			(_("Gzipped CD-SVG file"), ".svgz"),
																			(_("CDML file"),".cdml"),
																			(_("CDGZ file"),".cdgz"),
																			(_("Molfile"), ".mol"),
																			(_("SDF file"), ".sdf"),
																			(_("SMILES file"), (".smi", ".smiles")),
																			(_("CML file"), ".cml"),
																			(_("CDXML file"), ".cdxml"),
																			(_("Gzipped files"), ".gz"),
																			(_("All files"),"*")))
		else:
			a = file
		if not a:
			return None
		# route chemistry file extensions through the import pipeline
		ext = os.path.splitext(a)[1].lower()
		codec_name = _CHEM_EXTENSIONS.get(ext)
		if codec_name:
			return self.format_import(codec_name, filename=a)
		if self.papers and (replace or (self.paper.file_name['auto'] and not self.paper.changes_made)):
			self.close_paper()
		p = self.add_new_paper( name=a)
		if p != 0:
			self.paper.mode = self.mode # somehow the raise event does not work here
			return self._load_CDML_file( a)
		return 0


	def _load_CDML_file( self, a, draw=True):
		if a != '':
			self.save_dir, save_file = os.path.split( a)
			## try if the file is gzipped
			# try to open the file
			try:
				import gzip
				inp = gzip.open( a, "rb")
			except IOError:
				# can't read the file
				Store.log( _("cannot open file ") + a)
				return None
			# is it a gzip file?
			it_is_gzip = 1
			try:
				s = inp.read()
			except IOError:
				# not a gzip file
				it_is_gzip = 0
			# if it's gzip file parse it
			if it_is_gzip:
				try:
					doc = safe_xml.parse_dom_from_string( s)
				except:
					Store.log( _("error reading file"))
					inp.close()
					return None
				inp.close()
				del gzip
				doc = [n for n in doc.childNodes if n.nodeType == doc.ELEMENT_NODE][0]
			else:
			## otherwise it should be normal xml file
				## try to parse it
				try:
					doc = safe_xml.parse_dom_from_file( a)
				except IndexError:
					Store.log( _("error reading file"))
					return None
				## if it works check if its CDML of CD-SVG file
				doc = [n for n in doc.childNodes if n.nodeType == doc.ELEMENT_NODE][0]
			## check if its CD-SVG or CDML
			if doc.nodeName != 'cdml':
				## first try if there is the right namespace
				if hasattr( doc, 'getElementsByTagNameNS'):
					docs = doc.getElementsByTagNameNS( data.cdml_namespace, 'cdml')
				else:
					Store.log( _("File was not loaded"), message_type="error")
					return None  # I don't know why this happens, but we simply ignore the document
				if docs:
					doc = docs[0]
				else:
					# if not, try it without it
					docs = doc.getElementsByTagName( 'cdml')
					if docs:
						# ask if we should proceed with incorrect namespace
						proceed = tkinter.messagebox.askokcancel(_("Proceed?"),
																							_("CDML data seem present in SVG but have wrong namespace. Proceed?"),
																							default='ok',
																							parent=self)
						if proceed:
							doc = docs[0]
						else:
							Store.log(_("file not loaded"))
							return None
					else:
						## sorry but there is no cdml in the svg file
						Store.log(_("cdml data are not present in SVG or are corrupted!"))
						return None
			self.paper.clean_paper()
			self.paper.read_package( doc, draw=draw)
			if not bkchem_utils.myisstr(self.mode):
				self.mode.startup()
			Store.log( _("loaded file: ")+self.paper.full_path)
			self._record_recent_file( os.path.abspath( self.paper.full_path))
			return 1


	def save_SVG( self, file_name=None):
		return self.format_export( "svg", filename=file_name)


	def format_import( self, codec_name, filename=None):
		entry = self.format_entries.get( codec_name)
		if not entry:
			return 0
		if not filename:
			if self.paper.changes_made:
				if tkinter.messagebox.askokcancel(
						_("Forget changes?"),
						_("Forget changes in currently visiting file?"),
						default='ok',
						parent=self) == 0:
					return 0
			types = self._format_filetypes( entry["display_name"], entry.get("extensions", []))
			a = askopenfilename( defaultextension = "",
													initialdir = self.save_dir,
													initialfile = self.save_file,
													title = _("Load")+" "+entry["display_name"],
													parent = self,
													filetypes=types)
			if a:
				filename = a
			else:
				return 0
		try:
			mols = format_loader.import_format( codec_name, self.paper, filename)
		except Exception as detail:
			tkinter.messagebox.showerror(
				_("Import error"),
				_("Format import failed with following error:\n %s") % detail)
			return 0
		self.paper.clean_paper()
		self.paper.create_background()
		for m in mols:
			self.paper.stack.append( m)
			m.draw()
		self.paper.add_bindings()
		self.paper.start_new_undo_record()
		# summarize what was imported
		total_atoms = sum(len(m.atoms) for m in mols)
		total_bonds = sum(len(m.bonds) for m in mols)
		summary = _("Imported %d molecule(s): %d atoms, %d bonds from %s") % (
			len(mols), total_atoms, total_bonds, os.path.basename(filename))
		Store.log(summary)
		tkinter.messagebox.showinfo(_("Import summary"), summary)
		return 1


	def format_export( self, codec_name, filename=None, interactive=True, on_begin_attrs=None):
		_ = interactive
		_ = on_begin_attrs
		entry = self.format_entries.get( codec_name)
		if not entry:
			return False
		if not filename:
			file_name = self.paper.get_base_name()
			extensions = entry.get("extensions", [])
			if extensions:
				file_name += extensions[0]
			types = self._format_filetypes( entry["display_name"], extensions)
			defaultextension = ""
			if len( types) > 1:
				defaultextension = types[0][1]
			a = asksaveasfilename( defaultextension = defaultextension,
														initialdir = self.save_dir,
														initialfile = file_name,
														title = _("Export")+" "+entry["display_name"],
														parent = self,
														filetypes=types)
		else:
			a = filename
		if not a:
			return False
		try:
			format_loader.export_format(
				codec_name,
				self.paper,
				a,
				entry.get("scope", "paper"),
				entry.get("gui_options", []),
			)
		except ValueError as error:
			text = str( error)
			if text == "No molecule selected.":
				tkinter.messagebox.showerror(
					_("No molecule selected."),
					_('You have to select exactly one molecule (any atom or bond will do).'))
			elif text.endswith("molecules selected."):
				tkinter.messagebox.showerror(
					text,
					_('You have to select exactly one molecule (any atom or bond will do).'))
			else:
				tkinter.messagebox.showerror(
					_("Export error"),
					_("Format export failed with following error:\n %s") % error)
			return False
		except Exception as error:
			tkinter.messagebox.showerror(
				_("Export error"),
				_("Format export failed with following error:\n %s") % error)
			return False
		Store.log( _("exported file: ")+a)
		return True


	def _format_filetypes( self, format_name, extensions):
		types = []
		for ext in extensions:
			types.append( (format_name+" "+_("file"), ext))
		types.append( (_("All files"), "*"))
		return types


	def _record_recent_file( self, name):
		if name in self._recent_files:
			self._recent_files.remove( name)
		self._recent_files.insert( 0, name)
		if len( self._recent_files) > 5:
			self._recent_files = self._recent_files[0:5]
