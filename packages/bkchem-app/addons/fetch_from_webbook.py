import builtins
import random
import re
import time
from urllib.parse import urlparse

try:
	from urllib.request import urlopen
except ImportError:
	from urllib.request import urlopen

import Pmw
import dialogs
import oasa_bridge

_ = getattr( builtins, "_", None)
if not _:
	def _( text):
		return text
	builtins._ = _


molfile_link = re.compile('(<a href=")(.*)(">2d Mol file</a>)')
cas_re = re.compile('(<strong>CAS Registry Number:</strong>)(.*)(</li>)')
#link_re = re.compile('(<a href=")(/cgi/cbook.cgi?ID=.*">)(.*)(</a>)')


def _safe_urlopen(url):
	parsed = urlparse(url)
	if parsed.scheme not in ('http', 'https'):
		raise ValueError("Unsupported URL scheme: %s" % parsed.scheme)
	if parsed.netloc and parsed.netloc.lower() != "webbook.nist.gov":
		raise ValueError("Unsupported URL host: %s" % parsed.netloc)
	time.sleep(random.random())
	return urlopen(url)  # nosec B310 - scheme/host validated


def get_mol_from_web_molfile(app, name):
	dialog = dialogs.progress_dialog(app, title=_("Fetching progress"))
	url = "http://webbook.nist.gov/cgi/cbook.cgi?Name=%s&Units=SI" % (
		"+".join(name.split()),
	)
	dialog.update(0, top_text=_("Connecting to WebBook..."), bottom_text=url)
	try:
		stream = _safe_urlopen(url)
	except IOError:
		dialog.close()
		return None
	dialog.update(
		0.4,
		top_text=_("Searching for the compound..."),
		bottom_text=url,
	)
	cas = ''
	for line in stream.readlines():
		line = line.decode('utf-8')
		casm = cas_re.search(line)
		if casm:
			cas = casm.group(2)
		m = molfile_link.search(line)
		if m:
			s = m.group(2)
			dialog.update(
				0.8,
				top_text=_("Reading the molfile..."),
				bottom_text=s,
			)
			molfile = _safe_urlopen("http://webbook.nist.gov" + s)
			stream.close()
			ret = molfile.read().decode('utf-8')
			molfile.close()
			dialog.close()
			return ret, cas
	dialog.close()
	return None


def main(app):
	# ask for the name to fetch
	dial = Pmw.PromptDialog(
		app.paper,
		title=_('Name'),
		label_text=_('Give the name of a molecule to fetch:'),
		entryfield_labelpos='n',
		buttons=(_('OK'), _('Cancel')),
	)
	res = dial.activate()
	if res != _('OK'):
		return
	name = dial.get()

	try:
		from io import StringIO
	except ImportError:
		from io import StringIO

	molcas = get_mol_from_web_molfile(app, name)
	if molcas:
		mol, cas = molcas
		mol = StringIO(mol)
		molec = oasa_bridge.read_molfile(mol, app.paper)[0]
		mol.close()
		app.paper.stack.append(molec)
		molec.draw()
		if cas:
			t = app.paper.new_text(280, 300, text="CAS: " + cas.strip())
			t.draw()
		app.paper.add_bindings()
		app.paper.start_new_undo_record()
	else:
		app.update_status(
			_("Sorry, molecule with name %s was not found") % name
		)
