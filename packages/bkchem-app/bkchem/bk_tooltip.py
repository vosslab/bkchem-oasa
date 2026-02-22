"""Lightweight tooltip (balloon) widget replacing Pmw.Balloon."""

# Standard Library
import tkinter

#============================================
class BkBalloon:
	"""Lightweight tooltip manager that replaces Pmw.Balloon.

	Shows a floating tooltip near the cursor after a short delay when
	the mouse enters a bound widget.  Optionally calls a status command
	callback with the tooltip text for status-bar integration.

	Args:
		parent: The root Tk window.
		statuscommand: Optional callback that receives tooltip text.
			Called with the text on enter and with an empty string on leave.
	"""

	# delay in milliseconds before showing the tooltip
	_DELAY_MS: int = 500

	def __init__(self, parent: tkinter.Tk, statuscommand=None):
		"""Initialize the balloon tooltip manager.

		Args:
			parent: The root Tk window.
			statuscommand: Optional callback receiving tooltip text strings.
		"""
		self._parent = parent
		self._statuscommand = statuscommand
		self._tipwindow: tkinter.Toplevel = None
		self._after_id: str = None

	#============================================
	def bind(self, widget: tkinter.Widget, text: str) -> None:
		"""Bind tooltip behaviour to a widget.

		Registers <Enter>, <Leave>, and <ButtonPress> handlers so that
		hovering over *widget* shows *text* in a floating tooltip.

		Args:
			widget: The Tk widget to attach the tooltip to.
			text: The tooltip text to display on hover.
		"""
		widget.bind("<Enter>", lambda event: self._schedule(widget, text), add="+")
		widget.bind("<Leave>", lambda event: self._cancel_and_hide(widget), add="+")
		widget.bind("<ButtonPress>", lambda event: self._cancel_and_hide(widget), add="+")

	#============================================
	def _schedule(self, widget: tkinter.Widget, text: str) -> None:
		"""Schedule the tooltip to appear after a delay.

		Args:
			widget: The widget that triggered the enter event.
			text: The tooltip text to display.
		"""
		# cancel any previously pending tooltip
		self._cancel(widget)
		# schedule tooltip display after delay
		self._after_id = widget.after(self._DELAY_MS, lambda: self._show_tip(widget, text))
		# update status bar immediately on enter
		if self._statuscommand is not None:
			self._statuscommand(text)

	#============================================
	def _cancel(self, widget: tkinter.Widget) -> None:
		"""Cancel a pending tooltip display timer.

		Args:
			widget: The widget whose after-timer should be cancelled.
		"""
		if self._after_id is not None:
			widget.after_cancel(self._after_id)
			self._after_id = None

	#============================================
	def _cancel_and_hide(self, widget: tkinter.Widget) -> None:
		"""Cancel any pending tooltip and hide the current one.

		Args:
			widget: The widget that triggered the leave or button event.
		"""
		self._cancel(widget)
		self._hide_tip()
		# clear status bar text
		if self._statuscommand is not None:
			self._statuscommand("")

	#============================================
	def _show_tip(self, widget: tkinter.Widget, text: str) -> None:
		"""Display the floating tooltip near the widget.

		Creates a borderless Toplevel window positioned just below and
		to the right of the current cursor location.

		Args:
			widget: The widget that the tooltip is attached to.
			text: The tooltip text to display.
		"""
		# hide any existing tooltip first
		self._hide_tip()
		# get cursor position relative to screen
		x = widget.winfo_pointerx() + 12
		y = widget.winfo_pointery() + 12
		# create the tooltip toplevel window
		tip = tkinter.Toplevel(self._parent)
		tip.wm_overrideredirect(True)
		tip.wm_geometry(f"+{x}+{y}")
		# configure the tooltip appearance
		tip.configure(background="#ffffe0", borderwidth=1, relief="solid")
		# add the text label
		label = tkinter.Label(
			tip,
			text=text,
			background="#ffffe0",
			foreground="#000000",
			font=("sans-serif", 9),
			justify="left",
			padx=4,
			pady=2,
		)
		label.pack()
		self._tipwindow = tip

	#============================================
	def _hide_tip(self) -> None:
		"""Destroy the floating tooltip window if it exists."""
		if self._tipwindow is not None:
			self._tipwindow.destroy()
			self._tipwindow = None
