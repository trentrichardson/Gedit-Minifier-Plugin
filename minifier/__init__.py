# Copyright 2010 Trent Richardson
#
# This file is part of Gedit Minifier Plugin.
#
# Gedit Minifier Plugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# Gedit Minifier Plugin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Gedit Minifier Plugin. If not, see <http://www.gnu.org/licenses/>.

from StringIO import StringIO
from jsmin import JavascriptMinify

import gtk
import gedit
import os
import re
import gzip

ui_str = """
<ui>
  <menubar name="MenuBar">
    <menu name="ToolsMenu" action="Tools">
      <placeholder name="ToolsOps_2">
        <menu name="MenifierMenu" action="MinifierMenuAction">
			<menuitem name="MinifierJS" action="MinifierJS"/>
			<menuitem name="MinifierCSS" action="MinifierCSS"/>
			<menuitem name="MinifierGzip" action="MinifierGzip"/>
        </menu>
      </placeholder>
    </menu>
  </menubar>
</ui>
"""

class MinifierWindowHelper:
	def __init__(self, plugin, window):
		self._window = window
		self._plugin = plugin
		
		self.clipboard = gtk.Clipboard(gtk.gdk.display_get_default(), "CLIPBOARD")
	
		self._insert_menu()

	def deactivate(self):
		self._remove_menu()
		
		self._window = None
		self._plugin = None
		self._action_group = None
		self.clipboard = None

	def _insert_menu(self):
		manager = self._window.get_ui_manager()
		
		# Create a new action group
		self._action_group = gtk.ActionGroup("MinifierPluginActions")
		self._action_group.add_actions([
		("MinifierMenuAction", None, _("Minifier"), None, _("Minifier Tools"), None),
		("MinifierJS", None, _("Minify JS"), "<Ctrl>U", _("Minify JS"), self.on_minifier_js_activate),
		("MinifierCSS", None, _("Minify CSS"), "<Ctrl><Shift>U", _("Minify CSS"), self.on_minifier_css_activate),
		("MinifierGzip", None, _("Gzip Current File"), "<Ctrl><Alt>U", _("Gzip Current File"), self.on_minifier_gzip_activate)
		])
		
		manager.insert_action_group(self._action_group, -1)
		self._ui_id = manager.add_ui_from_string(ui_str)

	def _remove_menu(self):        
		manager = self._window.get_ui_manager()
		manager.remove_ui(self._ui_id)
		manager.remove_action_group(self._action_group)
		manager.ensure_update()

	def update_ui(self):
		#not much to do here..
		return

	# js minify button click
	def on_minifier_js_activate(self, action):
		doc = self._window.get_active_document()
		if not doc:
			return
			
		doctxt = doc.get_text(doc.get_iter_at_line(0), doc.get_end_iter())
		min_js = self.get_minified_js_str(doctxt)
		self.clipboard.set_text(min_js)
		
		md = gtk.MessageDialog(type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CLOSE, flags=gtk.DIALOG_MODAL, message_format="Minified JS Copied to Clipboard.")
		md.run()
		md.destroy()


	# css minify button click
	def on_minifier_css_activate(self, action):
		doc = self._window.get_active_document()
		if not doc:
			return
			
		doctxt = doc.get_text(doc.get_iter_at_line(0), doc.get_end_iter())
		min_css = self.get_minified_css_str(doctxt)
		self.clipboard.set_text(min_css)

		md = gtk.MessageDialog(type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_CLOSE, flags=gtk.DIALOG_MODAL, message_format="Minified CSS Copied to Clipboard.")
		md.run()
		md.destroy()
	
	# gzip button click
	def on_minifier_gzip_activate(self, action):
		doc = self._window.get_active_document()
		if not doc:
			return
		
		docuri = doc.get_uri_for_display()
		docfilename = doc.get_short_name_for_display()
		doctxt = doc.get_text(doc.get_iter_at_line(0), doc.get_end_iter())
		docfilenamegz = docfilename + '.gz'
		
		dialog = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_SAVE,buttons=(gtk.STOCK_CANCEL,gtk.RESPONSE_CANCEL,gtk.STOCK_SAVE,gtk.RESPONSE_OK))
		dialog.set_do_overwrite_confirmation(True)
		dialog.set_current_folder(os.path.split(docuri)[0])
		dialog.set_current_name(docfilenamegz)
		dialog.set_default_response(gtk.RESPONSE_OK)
		
		response = dialog.run()
		
		if response == gtk.RESPONSE_OK:
			newgzuri = dialog.get_filename()
			
			f = gzip.open(newgzuri, 'wb')
			f.write(doctxt)
			f.close()
			f = None
		
		dialog.destroy()


	# the guts of how to minify js
	def get_minified_js_str(self, js):
		ins = StringIO(js)
		outs = StringIO()
		
		JavascriptMinify().minify(ins, outs)
		
		str = outs.getvalue()
		
		if len(str) > 0 and str[0] == '\n':
			str = str[1:]
		
		str = re.sub(r'(\n|\r)+','', str)
		
		return str
	
	# the guts of how to minify css: 
	# credit: http://stackoverflow.com/questions/222581/python-script-for-minifying-css
	def get_minified_css_str(self, css):
		
		# remove comments - this will break a lot of hacks :-P
		css = re.sub( r'\s*/\*\s*\*/', "$$HACK1$$", css ) # preserve IE<6 comment hack
		css = re.sub( r'/\*[\s\S]*?\*/', "", css )
		css = css.replace( "$$HACK1$$", '/**/' ) # preserve IE<6 comment hack
		
		# url() doesn't need quotes
		css = re.sub( r'url\((["\'])([^)]*)\1\)', r'url(\2)', css )
		
		# spaces may be safely collapsed as generated content will collapse them anyway
		css = re.sub( r'\s+', ' ', css )
		
		# shorten collapsable colors: #aabbcc to #abc
		css = re.sub( r'#([0-9a-f])\1([0-9a-f])\2([0-9a-f])\3(\s|;)', r'#\1\2\3\4', css )
		
		# fragment values can loose zeros
		css = re.sub( r':\s*0(\.\d+([cm]m|e[mx]|in|p[ctx]))\s*;', r':\1;', css )
		
		min_css = ""
		
		for rule in re.findall( r'([^{]+){([^}]*)}', css ):
		
			# we don't need spaces around operators
			selectors = [re.sub( r'(?<=[\[\(>+=])\s+|\s+(?=[=~^$*|>+\]\)])', r'', selector.strip() ) for selector in rule[0].split( ',' )]
			
			# order is important, but we still want to discard repetitions
			properties = {}
			porder = []
			for prop in re.findall( '(.*?):(.*?)(;|$)', rule[1] ):
				key = prop[0].strip().lower()
				if key not in porder:
					porder.append( key )
				properties[ key ] = prop[1].strip()
			
			# output rule if it contains any declarations
			if properties:
				min_css = min_css + "%s{%s}" % ( ','.join( selectors ), ''.join(['%s:%s;' % (key, properties[key]) for key in porder])[:-1] )
		
		return min_css



class MinifierPlugin(gedit.Plugin):
	def __init__(self):
		gedit.Plugin.__init__(self)
		self._instances = {}
	
	def activate(self, window):
		self._instances[window] = MinifierWindowHelper(self, window)
	
	def deactivate(self, window):
		self._instances[window].deactivate()
		del self._instances[window]
	
	def update_ui(self, window):
		self._instances[window].update_ui()

