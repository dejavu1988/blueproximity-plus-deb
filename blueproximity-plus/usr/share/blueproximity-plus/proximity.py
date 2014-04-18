#!/usr/bin/env python
# coding: utf-8

# blueproximity ++
SW_VERSION = '0.1.5'
# Add security to your desktop by automatically locking and unlocking 
# the screen when you and your phone leave/enter the desk. 
# Think of a proximity detector for your mobile phone via bluetooth.
# requires external bluetooth util hcitool to run
# (which makes it unix only at this time)
# Needed python extensions:
#  ConfigObj (python-configobj)
#  PyGTK (python-gtk2, python-glade2)
#  Bluetooth (python-bluez)

# Copyright by Xiang Gao <xzgao@cs.helsinki.fi>
# and Secure Systems Group <http://se-sy.org/projects/coco/>
# from University of Helsinki.
# This source is licensed under the GPL v2.

APP_NAME = "blueproximity-plus"

# Check if there's already existing instance
from singleton import check_singleton
check_singleton()

## This value gives us the base directory for language files and icons.
import inspect, os
dist_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) + os.sep

# system includes
import sys
import time
import threading
import Queue
import signal
import syslog
import locale

#Modified imports
import json
import hashlib
import hmac
import inspect
from uuid_helper import get_uuid
from decision import *
from scan import Scan
from connection import *
from sensor import *
from lock_helper import lock_command, lock_command_sim
from calculate import Calculate
from log import *
from dbhelper import DBHelper


#Translation stuff
import gettext

#Get the local directory since we are not installing anything
local_path = dist_path + 'LANG/'
# Init the list of languages to support
langs = []
#Check the default locale
lc, encoding = locale.getdefaultlocale()
if (lc):
    #If we have a default, it's the first in the list
    langs = [lc]
    # Now lets get all of the supported languages on the system
language = os.environ.get('LANGUAGE', None)
if (language):
    """langage comes back something like en_CA:en_US:en_GB:en
    on linuxy systems, on Win32 it's nothing, so we need to
    split it up into a list"""
    langs += language.split(":")
"""Now add on to the back of the list the translations that we
know that we have, our defaults"""
langs += ["en"]

"""Now langs is a list of all of the languages that we are going
to try to use.  First we check the default, then what the system
told us, and finally the 'known' list"""

gettext.bindtextdomain(APP_NAME, local_path)
gettext.textdomain(APP_NAME)
# Get the language to use
lang = gettext.translation(APP_NAME, local_path, languages=langs, fallback = True)
"""Install the language, map _() (which we marked our
strings to translate with) to self.lang.gettext() which will
translate them."""
_ = lang.gettext    


# now the imports from external packages
try:
    import gobject
except:
    print _("The program cannot import the module gobject.")
    print _("Please make sure the GObject bindings for python are installed.")
    print _("e.g. with Ubuntu Linux, type")
    print _(" sudo apt-get install python-gobject")
    sys.exit(1)
try:
    from configobj import ConfigObj
    from validate import Validator
except:
    print _("The program cannot import the module ConfigObj or Validator.")
    print _("Please make sure the ConfigObject package for python is installed.")
    print _("e.g. with Ubuntu Linux, type")
    print _(" sudo apt-get install python-configobj")
    sys.exit(1)
IMPORT_BT=0
try:
    import bluetooth
    IMPORT_BT = IMPORT_BT+1
except:
    pass
try:
    import _bluetooth as bluez
    IMPORT_BT = IMPORT_BT+1
except:
    pass
try:
    import bluetooth._bluetooth as bluez
    IMPORT_BT = IMPORT_BT+1
except:
    pass
if (IMPORT_BT!=2):
    print _("The program cannot import the module bluetooth.")
    print _("Please make sure the bluetooth bindings for python as well as bluez are installed.")
    print _("e.g. with Ubuntu Linux, type")
    print _(" sudo apt-get install python-bluez")
    sys.exit(1)
try:
    import pygtk
    pygtk.require("2.0")
    import gtk
except:
    print _("The program cannot import the module pygtk.")
    print _("Please make sure the GTK2 bindings for python are installed.")
    print _("e.g. with Ubuntu Linux, type")
    print _(" sudo apt-get install python-gtk2")
    sys.exit(1)
try:
    import gtk.glade
except:
    print _("The program cannot import the module glade.")
    print _("Please make sure the Glade2 bindings for python are installed.")
    print _("e.g. with Ubuntu Linux, type")
    print _(" sudo apt-get install python-glade2")
    sys.exit(1)


## Setup config file specs and defaults
# This is the ConfigObj's syntax
conf_specs = [
    'device_mac=string(max=17,default="")',
    'device_channel=integer(1,30,default=7)',
    'device_uuid=string(max=40,default="")',
    'enable_context=boolean(default=False)',
    'lock_distance=integer(0,127,default=8)',
    'lock_duration=integer(0,120,default=7)',
    'unlock_distance=integer(0,127,default=4)',
    'unlock_duration=integer(0,120,default=1)',
    'lock_command=string(default=''gnome-screensaver-command -l'')',
    'unlock_command=string(default=''gnome-screensaver-command -d'')',
    'proximity_command=string(default=''gnome-screensaver-command -p'')',
    'proximity_interval=integer(5,600,default=60)',
    'buffer_size=integer(1,255,default=1)',
    'log_to_syslog=boolean(default=True)',
    'log_syslog_facility=string(default=''local7'')',
    'log_to_file=boolean(default=False)',
    'log_filelog_filename=string(default=''' + os.getenv('HOME') + '/blueproximity.log'')'
    ]
    

## The icon used at normal operation and in the info dialog.
icon_base = 'blueproximity_base.svg'
## The icon used at distances greater than the unlock distance.
icon_att = 'blueproximity_attention.svg'
## The icon used if no proximity is detected.
icon_away = 'blueproximity_nocon.svg'
## The icon used during connection processes and with connection errors.
icon_con = 'blueproximity_error.svg'
## The icon shown if we are in pause mode.
icon_pause = 'blueproximity_pause.svg'


## This class represents the main configuration window and
# updates the config file after changes made are saved
class ProximityGUI (object):

    ## Constructor sets up the GUI and reads the current config
    # @param configs A list of lists of name, ConfigObj object, proximity object
    # @param show_window_on_start Set to True to show the config screen immediately after the start.
    # This is true if no prior config file has been detected (initial start).
    def __init__(self,configs,show_window_on_start):
        
        #This is to block events from firing a config write because we initialy set a value
        self.gone_live = False
        
        #Set the Glade file
        self.gladefile = dist_path + "proximity.glade"  
        self.wTree = gtk.glade.XML(self.gladefile) 

        #Create our dictionary and connect it
        dic = { "on_btnInfo_clicked" : self.aboutPressed,
            "on_btnClose_clicked" : self.btnClose_clicked,
            "on_btnNew_clicked" : self.btnNew_clicked,
            "on_btnDelete_clicked" : self.btnDelete_clicked,
            "on_btnRename_clicked" : self.btnRename_clicked,
            "on_comboConfig_changed" : self.comboConfig_changed,
            "on_btnScan_clicked" : self.btnScan_clicked,
            "on_btnSelect_clicked" : self.btnSelect_clicked,
            "on_btnResetMinMax_clicked" : self.btnResetMinMax_clicked,
            "on_settings_changed" : self.event_settings_changed,
            "on_settings_changed_reconnect" : self.event_settings_changed_reconnect,
            "on_btnDlgNewDo_clicked" : self.dlgNewDo_clicked,
            "on_btnDlgNewCancel_clicked" : self.dlgNewCancel_clicked,
            "on_btnDlgRenameDo_clicked" : self.dlgRenameDo_clicked,
            "on_btnDlgRenameCancel_clicked" : self.dlgRenameCancel_clicked,
            "on_MainWindow_destroy" : self.btnClose_clicked }
        self.wTree.signal_autoconnect(dic)

        #Get the Main Window, and connect the "destroy" event
        self.window = self.wTree.get_widget("MainWindow")
        if (self.window):
            self.window.connect("delete_event", self.btnClose_clicked)
        self.window.set_icon(gtk.gdk.pixbuf_new_from_file(dist_path + icon_base))
        self.proxi = configs[0][2]
        self.minDist = -255
        self.maxDist = 0
        self.pauseMode = False
        self.lastMAC = ''
        self.scanningChannels = False

        #Get the New Config Window, and connect the "destroy" event
        self.windowNew = self.wTree.get_widget("createNewWindow")
        if (self.windowNew):
            self.windowNew.connect("delete_event", self.dlgNewCancel_clicked)

        #Get the Rename Config Window, and connect the "destroy" event
        self.windowRename = self.wTree.get_widget("renameWindow")
        if (self.windowRename):
            self.windowRename.connect("delete_event", self.dlgRenameCancel_clicked)


        #Prepare the mac/name table
        self.model = gtk.ListStore(gobject.TYPE_STRING,gobject.TYPE_STRING)
        self.tree = self.wTree.get_widget("treeScanResult")
        self.tree.set_model(self.model)
        self.tree.get_selection().set_mode(gtk.SELECTION_SINGLE)
        colLabel=gtk.TreeViewColumn(_('MAC'), gtk.CellRendererText(), text=0)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(0)
        self.tree.append_column(colLabel)
        colLabel=gtk.TreeViewColumn(_('Name'), gtk.CellRendererText(), text=1)
        colLabel.set_resizable(True)
        colLabel.set_sort_column_id(1)
        self.tree.append_column(colLabel)

        #Show the current settings
        self.configs = configs
        self.configname = configs[0][0]
        self.config = configs[0][1]
        self.fillConfigCombo()
        self.readSettings()
        #this is the gui timer
        self.timer = gobject.timeout_add(1000,self.updateState)
        #fixme: this will execute the proximity command at the given interval - is now not working 
        self.timer2 = gobject.timeout_add(1000*self.config['proximity_interval'],self.proximityCommand)
        
        
        #Only show if we started unconfigured
        if show_window_on_start:
            self.window.show()

        #Prepare icon
        self.icon = gtk.StatusIcon()
        self.icon.set_tooltip(_("BlueProximity starting..."))
        self.icon.set_from_file(dist_path + icon_con)
        
        #Setup the popup menu and associated callbacks
        self.popupmenu = gtk.Menu()
        menuItem = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        menuItem.connect('activate', self.showWindow)
        self.popupmenu.append(menuItem)
        menuItem = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PAUSE)
        menuItem.connect('activate', self.pausePressed)
        self.popupmenu.append(menuItem)
        menuItem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        menuItem.connect('activate', self.aboutPressed)
        self.popupmenu.append(menuItem)
        menuItem = gtk.MenuItem()
        self.popupmenu.append(menuItem)
        menuItem = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        menuItem.connect('activate', self.quit)
        self.popupmenu.append(menuItem)

        self.icon.connect('activate', self.showWindow)
        self.icon.connect('popup-menu', self.popupMenu, self.popupmenu)
        
        self.icon.set_visible(True)
        
        #now the control may fire change events
        self.gone_live = True
        #log start in all config files
        for config in self.configs:
            config[2].logger.log_line(_('started.'))

    ## Callback to just close and not destroy the rename config window 
    def dlgRenameCancel_clicked(self,widget, data = None):
        self.windowRename.hide()
        return 1

    ## Callback to rename a config file.
    def dlgRenameDo_clicked(self, widget, data = None):
        newconfig = self.wTree.get_widget("entryRenameName").get_text()
        # check if something has been entered
        if (newconfig==''):
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("You must enter a name for the configuration."))
            dlg.run()
            dlg.destroy()
            return 0
        # now check if that config already exists
        newname = os.path.join(os.getenv('HOME'),'.blueproximity',newconfig + ".conf")
        try:
            os.stat(newname)
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("A configuration file with the name '%s' already exists.") % newname)
            dlg.run()
            dlg.destroy()
            return 0
        except:
            pass
        config = None
        for conf in self.configs:
            if (conf[0]==self.configname):
                config = conf
        # change the path of the config file
        oldfile = self.config.filename
        self.config.filename = newname
        # save it under the new name
        self.config.write()
        # delete the old file
        try:
            os.remove(oldfile)
        except:
            print _("The configfile '%s' could not be deleted.") % oldfile
        # change the gui name
        self.configname = newconfig
        # update the configs array
        config[0] = newconfig
        # show changes
        self.fillConfigCombo()
        self.windowRename.hide()

    ## Callback to just close and not destroy the new config window 
    def dlgNewCancel_clicked(self,widget, data = None):
        self.windowNew.hide()
        return 1

    ## Callback to create a config file.
    def dlgNewDo_clicked(self, widget, data = None):
        newconfig = self.wTree.get_widget("entryNewName").get_text()
        # check if something has been entered
        if (newconfig==''):
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("You must enter a name for the new configuration."))
            dlg.run()
            dlg.destroy()
            return 0
        # now check if that config already exists
        newname = os.path.join(os.getenv('HOME'),'.blueproximity',newconfig + ".conf")
        try:
            os.stat(newname)
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("A configuration file with the name '%s' already exists.") % newname)
            dlg.run()
            dlg.destroy()
            return 0
        except:
            pass
        # then let's get it on...
        # create the new config
        newconf = ConfigObj(self.config.dict())
        newconf.filename = newname
        # and save it to the new name
        newconf.write()
        # create the according Proximity object
        p = Proximity(newconf)
        p.Simulate = True
        p.start()
        # fill that into our list of active configs
        self.configs.append([newconfig,newconf,p])
        # now refresh the gui to take account of our new config
        self.config = newconf
        self.configname = newconfig
        self.proxi = p
        self.readSettings()
        self.configs.sort()
        self.fillConfigCombo()
        # close the new config dialog
        self.windowNew.hide()

    ## Helper function to enable or disable the change or creation of the config files
    # This is called during non blockable functions that rely on the config not
    # being changed over the process like scanning for devices or channels
    # @param activate set to True to activate buttons, False to disable
    def setSensitiveConfigManagement(self,activate):
        # get the widget
        combo = self.wTree.get_widget("comboConfig")
        combo.set_sensitive(activate)
        button = self.wTree.get_widget("btnNew")
        button.set_sensitive(activate)
        button = self.wTree.get_widget("btnRename")
        button.set_sensitive(activate)
        button = self.wTree.get_widget("btnDelete")
        button.set_sensitive(activate)

    ## Helper function to populate the list of configurations.
    def fillConfigCombo(self):
        # get the widget
        combo = self.wTree.get_widget("comboConfig")
        model = combo.get_model()
        combo.set_model(None)
        # delete the list
        model.clear()
        pos = 0
        activePos = -1
        # add all configurations we have, remember the index of the active one
        for conf in self.configs:
            model.append([conf[0]])
            if (conf[0]==self.configname):
                activePos = pos
            pos = pos + 1
        combo.set_model(model)
        # let the comboBox show the active config entry
        if (activePos != -1):
            combo.set_active(activePos)

    ## Callback to select a different config file for editing.
    def comboConfig_changed(self, widget, data = None):
        # get the widget
        combo = self.wTree.get_widget("comboConfig")
        model = combo.get_model()
        name = combo.get_active_text()
        # only continue if this is different to the former config
        if (name != self.configname):
            newconf = None
            # let's find the new ConfigObj
            for conf in self.configs:
                if (name == conf[0]):
                    newconf = conf
            # if found set it as our active one and show it's settings in the GUI
            if (newconf != None):
                self.config = newconf[1]
                self.configname = newconf[0]
                self.proxi = newconf[2]
                self.readSettings()

    ## Callback to create a new config file for editing.
    def btnNew_clicked(self, widget, data = None):
        # reset the entry widget
        self.wTree.get_widget("entryNewName").set_text('')
        self.windowNew.show()

    ## Callback to delete a config file.
    def btnDelete_clicked(self, widget, data = None):
        # never delete the last config
        if (len(self.configs)==1):
            dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, _("The last configuration file cannot be deleted."))
            dlg.run()
            dlg.destroy()
            return 0
        # security question
        dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_YES_NO, _("Do you really want to delete the configuration '%s'.") % self.configname)
        retval = dlg.run()
        dlg.destroy()
        if (retval == gtk.RESPONSE_YES):
            # ok, now stop the detection for that config
            self.proxi.Stop = True
            # save the filename
            configfile = self.config.filename
            # rip it out of our configs array
            self.configs.remove([self.configname, self.config, self.proxi])
            # change active config to the next one
            self.configs.sort()
            self.configname = configs[0][0]
            self.config = configs[0][1]
            self.proxi = configs[0][2]
            # update gui
            self.readSettings()
            self.fillConfigCombo()
            # now delete the file on the disk
            try:
                os.remove(configfile)
            except:
                # should this be a GUI message?
                print _("The configfile '%s' could not be deleted.") % configfile

    ## Callback to rename a config file.
    def btnRename_clicked(self, widget, data = None):
        # set the entry widget
        self.wTree.get_widget("entryRenameName").set_text(self.configname)
        self.windowRename.show()

    ## Callback to show the pop-up menu if icon is right-clicked.
    def popupMenu(self, widget, button, time, data = None):
        if button == 3:
            if data:
                data.show_all()
                data.popup(None, None, None, 3, time)
        pass

    ## Callback to show and hide the config dialog.
    def showWindow(self, widget, data = None):
        if self.window.get_property("visible"):
            self.Close()
        else:
            self.window.show()
            for config in self.configs:
                config[2].Simulate = True

    ## Callback to create and show the info dialog.
    def aboutPressed(self, widget, data = None):
        logo = gtk.gdk.pixbuf_new_from_file(dist_path + icon_base)
        description = _("Leave it - it's locked, come back - it's back too...")
        copyright = u"""Copyright (c) 2014 Xiang Gao, Secure Systems Group"""
        people = [
            u"Xiang Gao <rekygx@gmail.com>",
            u"Lars Friedrichs <LarsFriedrichs@gmx.de>"
        ]
        license = _("""
        BlueProximity-plus is free software; you can redistribute it and/or modify it
        under the terms of the GNU General Public License as published by the 
        Free Software Foundation; either version 2 of the License, or 
        (at your option) any later version.

        BlueProximity-plus is distributed in the hope that it will be useful, but
        WITHOUT ANY WARRANTY; without even the implied warranty of 
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
        See the GNU General Public License for more details.

        You should have received a copy of the GNU General Public License 
        along with BlueProximity-plus; if not, write to the

        Free Software Foundation, Inc., 
        59 Temple Place, Suite 330, 
        Boston, MA  02111-1307  USA
        """)
        about = gtk.AboutDialog()
        about.set_icon(logo)
        about.set_name("BlueProximity-plus")
        about.set_version(SW_VERSION)
        about.set_copyright(copyright)
        about.set_comments(description)
        about.set_authors(people)
        about.set_logo(logo)
        about.set_license(license)
        about.set_website("http://goo.gl/jQcY09")
        about.connect('response', lambda widget, response: widget.destroy())
        about.show()

    ## Callback to activate and deactivate pause mode.
    # This is actually done by removing the proximity object's mac address.
    def pausePressed(self, widget, data = None):
        if self.pauseMode:
            self.pauseMode = False
            for config in configs:
                config[2].dev_mac = config[2].lastMAC
                config[2].Simulate = False
            self.icon.set_from_file(dist_path + icon_con)
        else:
            self.pauseMode = True
            for config in configs:
                config[2].lastMAC = config[2].dev_mac
                config[2].dev_mac = ''
                config[2].Simulate = True
                config[2].kill_connection()


    ## helper function to set a ComboBox's value to value if that exists in the Combo's list
    # The value is not changed if the new value is not member of the list.
    # @param widget a gtkComboBox object
    # @param value the value the gtkComboBox should be set to.    
    def setComboValue(self, widget, value):
        model = widget.get_model()
        for row in model:
            if row[0] == value:
                widget.set_active_iter(row.iter)
                break
        

    ## helper function to get a ComboBox's value
    def getComboValue(self, widget):
        model = widget.get_model()
        iter = widget.get_active_iter()
        return model.get_value(iter, 0)

    ## Reads the config settings and sets all GUI components accordingly.
    def readSettings(self):
        #Updates the controls to show the actual configuration of the running proximity
        was_live = self.gone_live
        self.gone_live = False
        self.wTree.get_widget("entryMAC").set_text(self.config['device_mac'])
        self.wTree.get_widget("entryChannel").set_value(int(self.config['device_channel']))
        self.wTree.get_widget("entryUUID").set_text(self.config['device_uuid'])
        self.wTree.get_widget("enableContext").set_active(self.config['enable_context'])
        self.wTree.get_widget("hscaleLockDist").set_value(int(self.config['lock_distance']))
        self.wTree.get_widget("hscaleLockDur").set_value(int(self.config['lock_duration']))
        self.wTree.get_widget("hscaleUnlockDist").set_value(int(self.config['unlock_distance']))
        self.wTree.get_widget("hscaleUnlockDur").set_value(int(self.config['unlock_duration']))
        self.wTree.get_widget("comboLock").child.set_text(self.config['lock_command'])
        self.wTree.get_widget("comboUnlock").child.set_text(self.config['unlock_command'])
        self.wTree.get_widget("comboProxi").child.set_text(self.config['proximity_command'])
        self.wTree.get_widget("hscaleProxi").set_value(self.config['proximity_interval'])
        self.wTree.get_widget("checkSyslog").set_active(self.config['log_to_syslog'])
        self.setComboValue(self.wTree.get_widget("comboFacility"), self.config['log_syslog_facility'])
        self.wTree.get_widget("checkFile").set_active(self.config['log_to_file'])
        self.wTree.get_widget("entryFile").set_text(self.config['log_filelog_filename'])
        self.gone_live = was_live

    ## Reads the current settings from the GUI and stores them in the configobj object.
    def writeSettings(self):
        #Updates the running proximity and the config file with the new settings from the controls
        was_live = self.gone_live
        self.gone_live = False
        self.proxi.dev_mac = self.wTree.get_widget("entryMAC").get_text()
        self.proxi.dev_channel = int(self.wTree.get_widget("entryChannel").get_value())
        self.proxi.dev_uuid = self.wTree.get_widget("entryUUID").get_text()
        self.proxi.enable_context = self.wTree.get_widget("enableContext").get_active()
        self.proxi.gone_limit = -self.wTree.get_widget("hscaleLockDist").get_value()
        self.proxi.gone_duration = self.wTree.get_widget("hscaleLockDur").get_value()
        self.proxi.active_limit = -self.wTree.get_widget("hscaleUnlockDist").get_value()
        self.proxi.active_duration = self.wTree.get_widget("hscaleUnlockDur").get_value()
        self.config['device_mac'] = str(self.proxi.dev_mac)
        self.config['device_channel'] = str(self.proxi.dev_channel)
        self.config['device_uuid'] = str(self.proxi.dev_uuid)
        self.config['enable_context'] = self.wTree.get_widget("enableContext").get_active()
        self.config['lock_distance'] = int(-self.proxi.gone_limit)
        self.config['lock_duration'] = int(self.proxi.gone_duration)
        self.config['unlock_distance'] = int(-self.proxi.active_limit)
        self.config['unlock_duration'] = int(self.proxi.active_duration)
        self.config['lock_command'] = self.wTree.get_widget('comboLock').child.get_text()
        self.config['unlock_command'] = str(self.wTree.get_widget('comboUnlock').child.get_text())
        self.config['proximity_command'] = str(self.wTree.get_widget('comboProxi').child.get_text())
        self.config['proximity_interval'] = int(self.wTree.get_widget('hscaleProxi').get_value())
        self.config['log_to_syslog'] = self.wTree.get_widget("checkSyslog").get_active()
        self.config['log_syslog_facility'] = str(self.getComboValue(self.wTree.get_widget("comboFacility")))
        self.config['log_to_file'] = self.wTree.get_widget("checkFile").get_active()
        self.config['log_filelog_filename'] = str(self.wTree.get_widget("entryFile").get_text())
        self.proxi.logger.configureFromConfig(self.config)
        self.config.write()
        self.gone_live = was_live

    ## Callback for resetting the values for the min/max viewer.
    def btnResetMinMax_clicked(self,widget, data = None):
        self.minDist = -255
        self.maxDist = 0

    ## Callback called by almost all GUI elements if their values are changed.
    # We don't react if we are still initializing (self.gone_live==False)
    # because setting the values of the elements would already fire their change events.
    # @see gone_live
    def event_settings_changed(self,widget, data = None):
        if self.gone_live:
            self.writeSettings()
        pass

    ## Callback called by certain GUI elements if their values are changed.
    # We don't react if we are still initializing (self.gone_live==False)
    # because setting the values of the elements would already fire their change events.
    # But in any case we kill a possibly existing connection. 
    # Changing the rfcomm channel e.g. fires this event instead of event_settings_changed.
    # @see event_settings_changed
    def event_settings_changed_reconnect(self,widget, data = None):
        self.proxi.kill_connection()
        if self.gone_live:
            self.writeSettings()
        pass

    ## Callback to just close and not destroy the main window 
    def btnClose_clicked(self,widget, data = None):
        self.Close()
        return 1

    ## Callback called when one clicks on the 'use selected address' button
    # it copies the MAC address of the selected device into the mac address field.
    def btnSelect_clicked(self,widget, data = None):
        #Takes the selected entry in the mac/name table and enters its mac in the MAC field
        selection = self.tree.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)
        model, selection_iter = selection.get_selected()
        if (selection_iter):
            mac = self.model.get_value(selection_iter, 0)
            self.wTree.get_widget("entryMAC").set_text(mac)
            self.writeSettings()
            self.proxi.kill_connection()
            Bind(mac, self.proxi.local_uuid, self.bind_done).start()

    ## Callback when Bind is done
    def bind_done(self, port, dev_uuid):
        self.wTree.get_widget("entryUUID").set_text(dev_uuid)
        self.wTree.get_widget("entryChannel").set_value(port)
        self.proxi.client.set_queues(dev_uuid)
        self.writeSettings()
        
    ## Callback that is executed when the scan for devices button is clicked
    # actually it starts the scanning asynchronously to have the gui redraw nicely before hanging :-)
    def btnScan_clicked(self,widget, data = None):
        # scan the area for bluetooth devices and show the results
        watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
        self.window.window.set_cursor(watch)
        self.model.clear()
        self.model.append(['...', _('Now scanning...')])
        self.setSensitiveConfigManagement(False)
        #gobject.idle_add(self.cb_btnScan_clicked)
        tmpMac = self.proxi.dev_mac
        self.proxi.dev_mac = ''
        self.proxi.kill_connection()
        ScanDevice(tmpMac, self.scan_done).start()

    ## Callback when ScanDevice is done
    def scan_done(self, tmp_mac, macs):
        self.proxi.dev_mac = tmp_mac
        self.model.clear()
        for mac in macs:
            self.model.append([mac[0], mac[1]])
        self.window.window.set_cursor(None)
        self.setSensitiveConfigManagement(True)

    def Close(self):
        #Hide the settings window
        self.window.hide()
        #Disable simulation mode for all configs
        for config in configs:
            config[2].Simulate = False

    def quit(self, widget, data = None):
        #try to close everything correctly
        self.icon.set_from_file(dist_path + icon_att)
        for config in configs:
           config[2].logger.log_line(_('stopped.'))
           config[2].Stop = 1
        time.sleep(2)
        gtk.main_quit()

    ## Updates the GUI (values, icon, tooltip) with the latest values
    # is always called via gobject.timeout_add call to run asynchronously without a seperate thread.
    def updateState(self):
        # update the display with newest measurement values (once per second)
        newVal = int(self.proxi.Dist) # Values are negative!
        if newVal > self.minDist:
            self.minDist = newVal
        if newVal < self.maxDist:
            self.maxDist = newVal
        self.wTree.get_widget("labState").set_text(_("min: ") + 
            str(-self.minDist) + _(" max: ") + str(-self.maxDist) + _(" state: ") + self.proxi.State)
        self.wTree.get_widget("hscaleAct").set_value(-newVal)
        
        #Update icon too
        if self.pauseMode:
            self.icon.set_from_file(dist_path + icon_pause)
            self.icon.set_tooltip(_('Pause Mode - not connected'))
        else:
            # we have to show the 'worst case' since we only have one icon but many configs...
            connection_state = 0
            con_info = ''
            con_icons = [icon_base, icon_att, icon_away, icon_con ]
            for config in configs:
                if config[2].ErrorMsg == "No connection found, trying to establish one...":
                    connection_state = 3
                else:
                    if config[2].State != _('active'):
                        if (connection_state < 2):
                            connection_state = 2
                    else:
                        if newVal < config[2].active_limit:
                            if (connection_state < 1):
                                connection_state = 1
                if (con_info != ''):
                    con_info = con_info + '\n\n'
                con_info = con_info + config[0] + ': ' + _('Detected Distance: ') + str(-config[2].Dist) + '; ' + _("Current State: ") + config[2].State + '; ' + _("Status: ") + config[2].ErrorMsg
            if self.proxi.Simulate:
                simu = _('\nSimulation Mode (locking disabled)')
            else:
                simu = ''
            self.icon.set_from_file(dist_path + con_icons[connection_state])
            self.icon.set_tooltip(con_info + '\n' + simu)
        self.timer = gobject.timeout_add(1000,self.updateState)
        
    def proximityCommand(self):
        #This is the proximity command callback called asynchronously as the updateState above
        if self.proxi.State == _('active') and not self.proxi.Simulate:
            #ret_val = os.popen(self.config['proximity_command']).readlines()
            lock_command_sim(self.config['proximity_command'])
        self.timer2 = gobject.timeout_add(1000*self.config['proximity_interval'],self.proximityCommand)


## This class creates all logging information in the desired form.
# We may log to syslog with a given syslog facility, while the severety is always info.
# We may also log a simple file.
class Logger(object):
    ## Constructor does nothing special.
    def __init__(self):
        self.disable_syslogging()
        self.disable_filelogging()
        
    ## helper function to convert a string (given by a ComboBox) to the corresponding
    # syslog module facility constant.
    # @param facility One of the 8 "localX" facilities or "user".
    def getFacilityFromString(self, facility):
        #Returns the correct constant value for the given facility
        dict = {
            "local0" : syslog.LOG_LOCAL0,
            "local1" : syslog.LOG_LOCAL1,
            "local2" : syslog.LOG_LOCAL2,
            "local3" : syslog.LOG_LOCAL3,
            "local4" : syslog.LOG_LOCAL4,
            "local5" : syslog.LOG_LOCAL5,
            "local6" : syslog.LOG_LOCAL6,
            "local7" : syslog.LOG_LOCAL7,
            "user" : syslog.LOG_USER
        }
        return dict[facility]

    ## Activates the logging to the syslog server.
    def enable_syslogging(self, facility):
        self.syslog_facility = self.getFacilityFromString(facility)
        syslog.openlog('blueproximity',syslog.LOG_PID)
        self.syslogging = True
        
    ## Deactivates the logging to the syslog server.
    def disable_syslogging(self):
        self.syslogging = False
        self.syslog_facility = None

    ## Activates the logging to the given file.
    # Actually tries to append to that file first, afterwards tries to write to it.
    # If both don't work it gives an error message on stdout and does not activate the logging.
    # @param filename The complete filename where to log to        
    def enable_filelogging(self, filename):
        self.filename = filename
        try:
            #let's append
            self.flog = file(filename,'a')
            self.filelogging = True
        except:
            try:
                #did not work, then try to create file (is this really needed or does python know another attribute to file()?
                self.flog = file(filename,'w')
                self.filelogging = True
            except:
                print _("Could not open logfile '%s' for writing." % filename)
                self.disable_filelogging

    ## Deactivates logging to a file.
    def disable_filelogging(self):
        try:
            self.flog.close()
        except:
            pass
        self.filelogging = False
        self.filename = ''

    ## Outputs a line to the logs. Takes care of where to put the line.
    # @param line A string that is printed in the logs. The string is unparsed and not sanatized by any means.
    def log_line(self, line):
        if self.syslogging:
            syslog.syslog(self.syslog_facility | syslog.LOG_NOTICE, line)
        if self.filelogging:
            try:
                self.flog.write( time.ctime() + " blueproximity: " + line + "\n")
                self.flog.flush()
            except:
                self.disable_filelogging()
    
    ## Activate the logging mechanism that are requested by the given configuration.
    # @param config A ConfigObj object containing the needed settings.
    def configureFromConfig(self, config):
        if config['log_to_syslog']:
            self.enable_syslogging(config['log_syslog_facility'])
        else:
            self.disable_syslogging()
        if config['log_to_file']:
            if self.filelogging and config['log_filelog_filename'] != self.filename:
                self.disable_filelogging()
                self.enable_filelogging(config['log_filelog_filename'])
            elif not self.filelogging:
                self.enable_filelogging(config['log_filelog_filename'])


class Bind(threading.Thread):

    def __init__(self, mac, local_uuid, callback):
        threading.Thread.__init__(self)
        self.mac = mac
        self.port = 7   # port for binding
        #self.chosen_port = 7    # port for use
        self.service_uuid = "fa87c0d0-afac-11de-8a39-0800200c9a66"  # customized service for binding
        #self.chosen_uuid = "0000111f-0000-1000-8000-00805F9B34FB"  # Handsfree Audio Gateway service
        self.local_uuid = local_uuid
        self.bind_uuid = ''
        self.tmp_uuid = ''
        #self.timer = gobject.timeout_add(500, self.run)
        self.connected = False
        self.sock = bluetooth.BluetoothSocket( bluetooth.RFCOMM )
        self.callback = callback

    def run(self):
        service_matches = bluetooth.find_service(uuid=self.service_uuid, address=self.mac)
        #service_chosen = bluetooth.find_service(uuid=self.chosen_uuid, address=self.mac)
        if len(service_matches) == 0:
            print "couldn't find the Server service =("
            sys.exit(0)
        else:
            self.port = int(service_matches[0]['port'])
            #if len(service_chosen) == 0:
            #    self.chosen_port = self.port
            #else:
            #    self.chosen_port = int(service_chosen[0]['port'])
            print "MAC: %s, PORT: %d" % (self.mac, self.port)
            self.connect()
            if self.connected:  #in case connection successful
                print "Paired with %s... at %d" % (self.mac, self.port)
                self.exchange_bind()

    def connect(self):
        self.connected = False
        timeout = 3
        while timeout > 0:
            try:
                self.sock.connect((self.mac, self.port))
                self.connected = True
                timeout = 0
                break
            except IOError:
                msg = "Bluetooth error, check your Bluetooth settings."
                print 'Error: ' + msg
                timeout -= 1
                if timeout == 0:
                    sys.exit('Error:' + msg)
                #time.sleep(1)

    def exchange_bind(self):
        timeout = 3
        while timeout > 0:
            timeout -= 1
            try:
                tmp_hmac = hmac.new(self.service_uuid, self.local_uuid, hashlib.sha256).hexdigest()
                self.sock.send("ID:"+self.local_uuid+":"+tmp_hmac+":")
                timeout = -1
                break
            except IOError:
                print "Bind connection broken."
                if self.connected:
                    self.connect()
                    continue
        while timeout == -1:    #in case sendID is successful
            try:
                data = self.sock.recv(128)
            except IOError:
                timeout = -2
                break
            if len(data) == 0:
                continue
            else:
                print "bind received [%s]" % data
                tmp = data.split(':')
                if len(tmp) >= 3 and equals_ignore_case(tmp[0],'ID'):
                    tmp_hmac = hmac.new(self.service_uuid, tmp[1], hashlib.sha256).hexdigest()
                    if equals_ignore_case(tmp[2], tmp_hmac):
                        self.tmp_uuid = tmp[1]
                        self.sock.send("DONE:")
                    else:
                        self.sock.send("ERR:")
                elif equals_ignore_case(tmp[0], 'ERR'):
                    tmp_hmac = hmac.new(self.service_uuid, self.local_uuid, hashlib.sha256).hexdigest()
                    self.sock.send("ID:"+self.local_uuid+":"+tmp_hmac+":")
                elif equals_ignore_case(tmp[0], 'DONE'):
                    self.bind_uuid = self.tmp_uuid
                    self.tmp_uuid = ''
                    print "Bound to: " + self.bind_uuid
                    self.sock.close()
                    self.connected = False
                    gobject.idle_add(self.callback, self.port, self.bind_uuid)
                    break


class ScanDevice(threading.Thread):

    def __init__(self, tmp_mac, callback):
        threading.Thread.__init__(self)
        self.tmp_mac = tmp_mac
        self.callback = callback
        #self.timer = gobject.timeout_add(1, self.run)

    def run(self):
        macs=[]
        try:
            macs = self.get_device_list()
        except:
            macs = [('', _('Sorry, the bluetooth device is busy connecting.\nPlease enter a correct mac address or no address at all\nfor the config that is not connecting and try again later.'))]
        gobject.idle_add(self.callback, self.tmp_mac, macs)

    ## Returns all active bluetooth devices found. This is a blocking call.
    def get_device_list(self):
        ret_tab = []
        nearby_devices = bluetooth.discover_devices(lookup_names=True)
        for bdaddr, name in nearby_devices:
            ret_tab.append((str(bdaddr),str(name)))
        return ret_tab


## This class does 'all the magic' like regular device detection and decision making
# whether a device is known as present or away. Here is where all the bluetooth specific
# part takes place. It is build to be run a a seperate thread and would run perfectly without any GUI.
# Please note that the present-command is issued by the GUI whereas the locking and unlocking
# is called by this class. This is inconsitent and to be changed in a future release.
class Proximity (threading.Thread):
    ## Constructor to setup our local variables and initialize threading.
    # @param config a ConfigObj object that stores all our settings
    def __init__(self,config, udir, log_queue, log_lock, uname, uuid, sample, client, dec_queue, dec_lock, calculate ):
        threading.Thread.__init__(self, name="WorkerThread")
        self.config = config
        self.Dist = -255
        self.State = _("gone")
        self.Simulate = False
        self.Stop = False
        self.procid = 0
        self.local_uuid = uuid  # Local UUID
        self.dev_mac = self.config['device_mac']
        self.dev_channel = self.config['device_channel']
        self.dev_uuid = self.config['device_uuid']  # Remote device UUID
        self.enable_context = self.config['enable_context'] # Switching between w/ or w/o contextual scan
        self.ringbuffer_size = self.config['buffer_size']
        self.ringbuffer = [-254] * self.ringbuffer_size
        self.ringbuffer_pos = 0
        self.gone_duration = self.config['lock_duration']
        self.gone_limit = -self.config['lock_distance']
        self.active_duration = self.config['unlock_duration']
        self.active_limit = -self.config['unlock_distance']
        self.ErrorMsg = _("Initialized...")
        self.sock = None
        self.ignoreFirstTransition = True
        self.logger = Logger()
        self.logger.configureFromConfig(self.config)
        self.timeAct = 0
        self.timeGone = 0
        self.timeProx = 0
        #Modified init start
        self.delay_start = 5    # delay after binding
        self.trigger_timeout = 30 # timeout of triggering scanning
        self.last_rssi = 0  # last valid raw rssi value
        self.sus_rssi = 0   # suspecious raw rssi value
        self.buf = []   # buffer of raw RSSIs for filter window
        self.path = udir
        self.log_queue = log_queue
        self.log_lock = log_lock
        self.uname = uname  # user login name
        self.sample = sample    # Sample object
        self.client = client    # Connection threading object
        self.client.set_queues(self.config['device_uuid'])
        self.dec_queue = dec_queue # decision queue
        self.dec_lock = dec_lock # decision lock
        self.calculate = calculate
        #self.calculate.start()
        #Modified init end

    ## Kills the rssi detection connection.
    def kill_connection(self):
        if self.sock != None:
            self.sock.close()
        self.sock = None
        return 0

    ## Returns the rssi value of a connection to the given mac address.
    # @param dev_mac mac address of the device to check.
    # This should also be removed but I still have to find a way to read the rssi value from python
    def get_proximity_once(self,dev_mac):
        ret_val = os.popen("hcitool rssi " + dev_mac + " 2>/dev/null").readlines()
        if ret_val == []:
            ret_val = -255
        else:
            ret_val = ret_val[0].split(':')[1].strip(' ')
        return self.prefilter(int(ret_val))

    ## Fire up an rfcomm connection to a certain device on the given channel.
    # Don't forget to set up your phone not to ask for a connection.
    # (at least for this computer.)
    # @param dev_mac mac address of the device to connect to.
    # @param dev_channel rfcomm channel we want to connect to.
    def get_connection(self,dev_mac,dev_channel):
        try:
            self.procid = 1
            _sock = bluez.btsocket()
            self.sock = bluetooth.BluetoothSocket( bluetooth.RFCOMM , _sock )
            self.sock.connect((dev_mac, dev_channel))
        except:
            self.procid = 0
            pass
        return self.procid

    def prefilter(self, rssi):
        """
        Eliminates single outlier (below -100)
        @param rssi: current scan result rssi
        @return: rssi without jumping outlier
        """
        if len(self.buf) == 0:    # First value
            self.last_rssi = rssi
            self.sus_rssi = 0
            return rssi
        elif rssi < -100 and rssi - self.last_rssi < -100:   # Suspecious value
            if self.sus_rssi == 0:   # No precedence
                self.sus_rssi = rssi
                return self.last_rssi
            else:   # Has precedence
                self.last_rssi = rssi
                self.sus_rssi = 0
                return rssi
        else:   # Normal case
            self.last_rssi = rssi
            self.sus_rssi = 0
            return rssi


    def filter(self, rssi):
        """
        Moving average filter (online)
        @param val: raw rssi value
        @return: filtered rssi value
        """
        val = self.prefilter(rssi)
        WINDOW = 5  # Window size
        if len(self.buf) < WINDOW:  # Returns average when buffer is not full
            self.buf.append(val)
            return sum(self.buf)/float(len(self.buf))
        else:   # Returns moving average when buffer is full
            self.buf.pop(0)
            self.buf.append(val)
            return sum(self.buf)/float(WINDOW)


    def run_cycle(self,dev_mac,dev_channel):
        # reads the distance and averages it over the ringbuffer
        self.ringbuffer_pos = (self.ringbuffer_pos + 1) % self.ringbuffer_size
        self.ringbuffer[self.ringbuffer_pos] = self.get_proximity_once(dev_mac)
        ret_val = 0
        for val in self.ringbuffer:
            ret_val = ret_val + val
        if self.ringbuffer[self.ringbuffer_pos] == -255:
            self.ErrorMsg = _("No connection found, trying to establish one...")
            self.kill_connection()
            self.get_connection(dev_mac,dev_channel)
        return int(ret_val / self.ringbuffer_size)

    def go_active(self):
        #The Doctor is in
        if self.ignoreFirstTransition:
            self.ignoreFirstTransition = False
        else:
            self.logger.log_line(_('screen is unlocked'))
            if (self.timeAct==0):
                self.timeAct = time.time()
                print 'Unlock triggered by '+ self.config['unlock_command']
                #ret_val = os.popen(self.config['unlock_command']).readlines()
                lock_command(self.uname, self.config['unlock_command'])
                ## send unlock event notification to server
                #if self.enable_context:
                #    self.client.sendResult('Y','T', self.sample.decisiontime)
                #else:
                #    self.client.sendResult('Y','T', int(self.timeAct))
                self.client.sendResult('Y','T', int(self.timeAct))
                #self.State = _("active")
                self.timeAct = 0
            else:
                self.logger.log_line(_('A command for %s has been skipped because the former command did not finish yet.') % _('unlocking'))
                self.ErrorMsg = _('A command for %s has been skipped because the former command did not finish yet.') % _('unlocking')

    def go_active_pure(self):
        #The Doctor is in
        if self.ignoreFirstTransition:
            self.ignoreFirstTransition = False
        else:
            self.logger.log_line(_('screen is unlocked'))
            if (self.timeAct==0):
                self.timeAct = time.time()
                print 'Unlock triggered by ' + self.config['unlock_command']
                #ret_val = os.popen(self.config['unlock_command']).readlines()
                lock_command(self.uname, self.config['unlock_command'])
                #self.State = _("active")
                self.timeAct = 0
            else:
                self.logger.log_line(_('A command for %s has been skipped because the former command did not finish yet.') % _('unlocking'))
                self.ErrorMsg = _('A command for %s has been skipped because the former command did not finish yet.') % _('unlocking')

    ## lock screen and do send notification
    def go_gone(self):
        #The Doctor is out
        if self.ignoreFirstTransition:
            self.ignoreFirstTransition = False
        else:
            self.logger.log_line(_('screen is locked'))
            if (self.timeGone==0):
                self.timeGone = time.time()
                print 'Lock triggered by '+ self.config['lock_command']
                #ret_val = os.popen(self.config['lock_command']).readlines()
                lock_command(self.uname, self.config['lock_command'])
                ## send lock event notification to server
                #    self.client.sendResult('N','F', self.sample.getTime())
                self.client.sendResult('N','F', int(self.timeGone))
                #self.State = _("gone")
                self.timeGone = 0
            else:
                self.logger.log_line(_('A command for %s has been skipped because the former command did not finish yet.') % _('locking'))
                self.ErrorMsg = _('A command for %s has been skipped because the former command did not finish yet.') % _('locking')

    ## lock screen and do not send notification
    def go_gone_pure(self):
        #The Doctor is out
        if self.ignoreFirstTransition:
            self.ignoreFirstTransition = False
        else:
            self.logger.log_line(_('screen is locked'))
            if (self.timeGone==0):
                self.timeGone = time.time()
                print 'Lock triggered by ' + self.config['lock_command']
                #ret_val = os.popen(self.config['lock_command']).readlines()
                lock_command(self.uname, self.config['lock_command'])
                #self.State = _("gone")
                self.timeGone = 0
            else:
                self.logger.log_line(_('A command for %s has been skipped because the former command did not finish yet.') % _('locking'))
                self.ErrorMsg = _('A command for %s has been skipped because the former command did not finish yet.') % _('locking')


    def go_proximity(self):
        #The Doctor is still in
        if (self.timeProx==0):
            self.timeProx = time.time()
            #ret_val = os.popen(self.config['proximity_command']).readlines()
            lock_command(self.uname, self.config['proximity_command'])
            #print "Go poke"
            self.timeProx = 0j
        else:
            self.logger.log_line(_('A command for %s has been skipped because the former command did not finish yet.') % _('proximity'))
            self.ErrorMsg = _('A command for %s has been skipped because the former command did not finish yet.') % _('proximity')

    ##context-test of 4 sensors and send trigger to server
    def go_context_scan(self):
        self.sample.clearSensors()
        self.sample.updateTime()
        self.client.sendScan(sample.getTime())
        sc = Scan(self.path, self.log_queue, log_lock, sample.local)
        sc.start()
        sc.join()


    ## This is the main loop of the proximity detection engine.
    # It checks the rssi value against limits and invokes all commands.
    def run(self):
        duration_count = 0
        context_timeout = 5
        state = _("gone")
        proxiCmdCounter = 0
        last_triggered_time = 0
        while not self.dev_uuid:
            time.sleep(1)
        time.sleep(self.delay_start)
        while not self.Stop:
            if self.enable_context:    # when context module is used
                #print "tick"
                try:
                    ## Start of Added response handler
                    stt = self.client.getResponseStatus()
                    #print 'Response status - '+ str(stt) + ' Time - ' + str(time.time())
                    if stt == 2:    #FP
                        state = _("gone")
                        proxiCmdCounter = 0
                        duration_count = 0
                        if not self.Simulate:
                            # start the process asynchronously so we are not hanging here...
                            timerGone = gobject.timeout_add(5,self.go_gone_pure)
                    elif stt == 4 or stt == 5:   #FN
                        state = _("active")
                        duration_count = 0
                        if not self.Simulate:
                            # start the process asynchronously so we are not hanging here...
                            timerAct = gobject.timeout_add(5,self.go_active_pure)
                    if stt != 0:
                        self.client.resetResponseStatus()
                    ## End of Added response handler
                    if self.dev_mac != "":
                        self.ErrorMsg = _("running...")
                        dist = self.run_cycle(self.dev_mac,self.dev_channel) #dist: average RSSI from get_proximity_once()
                    else:
                        dist = -255
                        self.ErrorMsg = "No bluetooth device configured..."
                    print 'Dist: ' + str(dist) + " State: " + state
                    if state == _("gone"):  #state: gone
                        ##  modified algo of trigger
                        if dist >= 2 * self.active_limit:   #inside 2*range of trigger scanning
                            #print "Inside scan range"
                            if self.sample.isDecisionOn() and (not self.sample.isExpired()): #result still valid
                                pass
                            else:   # decision expired or empty
                                if int(time.time()) - last_triggered_time > self.trigger_timeout:
                                    timerAct = gobject.timeout_add(5,self.go_context_scan)  #asynchromous call
                                    last_triggered_time = int(time.time())
                        if dist >= self.active_limit:
                            duration_count += 1
                            context_timeout -= 1
                            if context_timeout <= 0:
                                context_timeout = 5
                                state = _("active")
                                duration_count = 0
                                if not self.Simulate:
                                    # start the process asynchronously so we are not hanging here...
                                    timerAct = gobject.timeout_add(5,self.go_active)
                                    #self.go_active()
                            if duration_count >= self.active_duration:
                                if self.sample.isDecisionOn() and (not self.sample.isExpired()):
                                    if self.sample.decision:
                                        state = _("active")
                                        duration_count = 0
                                        if not self.Simulate:
                                            # start the process asynchronously so we are not hanging here...
                                            timerAct = gobject.timeout_add(5,self.go_active)
                                            #self.go_active()
                                else:   # decision expired or empty
                                    if int(time.time()) - last_triggered_time > self.trigger_timeout:
                                        timerAct = gobject.timeout_add(5,self.go_context_scan)  #asynchromous call
                                        last_triggered_time = int(time.time())
                        else:
                            duration_count = 0
                    else:
                        if dist <= self.gone_limit:
                            duration_count += 1
                            if duration_count >= self.gone_duration:
                                state = _("gone")
                                proxiCmdCounter = 0
                                duration_count = 0
                                if not self.Simulate:
                                    # start the process asynchronously so we are not hanging here...
                                    timerGone = gobject.timeout_add(5,self.go_gone)
                                    #self.go_gone()
                        else:
                            duration_count = 0
                            proxiCmdCounter = proxiCmdCounter + 1
                    #if dist != self.Dist or state != self.State:
                        #print "Detected distance atm: " + str(dist) + "; state is " + state
                       # pass
                    self.State = state
                    self.Dist = dist
                    # let's handle the proximity command
                    if (proxiCmdCounter >= self.config['proximity_interval']) and not self.Simulate and (self.config['proximity_command']!=''):
                        proxiCmdCounter = 0
                        # start the process asynchronously so we are not hanging here...
                        timerProx = gobject.timeout_add(5,self.go_proximity)
                    time.sleep(1)
                except KeyboardInterrupt:
                    break

            else:# pure blueproximity without context
                #print "tick"                
                try:
                    ## Start of Added response handler
                    stt = self.client.getResponseStatus()
                    #print 'Response status - '+ str(stt) + ' Time - ' + str(time.time())
                    if stt == 2:    #FP
                        state = _("gone")
                        proxiCmdCounter = 0
                        duration_count = 0
                        if not self.Simulate:
                            # start the process asynchronously so we are not hanging here...
                            timerGone = gobject.timeout_add(5,self.go_gone_pure)
                    elif stt == 4 or stt == 5:   #FN
                        state = _("active")
                        duration_count = 0
                        if not self.Simulate:
                            # start the process asynchronously so we are not hanging here...
                            timerAct = gobject.timeout_add(5,self.go_active_pure)
                    if stt != 0:
                        self.client.resetResponseStatus()
                    ## End of Added response handler
                    if self.dev_mac != "":
                        self.ErrorMsg = _("running...")
                        dist = self.run_cycle(self.dev_mac,self.dev_channel)
                    else:
                        dist = -255
                        self.ErrorMsg = "No bluetooth device configured..."
                    print 'Dist: ' + str(dist) + " State: " + state
                    if state == _("gone"):
                        if dist>=self.active_limit:
                            duration_count = duration_count + 1
                            if duration_count >= self.active_duration:
                                state = _("active")
                                duration_count = 0
                                if not self.Simulate:
                                    # start the process asynchronously so we are not hanging here...
                                    timerAct = gobject.timeout_add(5,self.go_active)
                                    #self.go_active()
                        else:
                            duration_count = 0
                    else:
                        if dist<=self.gone_limit:
                            duration_count = duration_count + 1
                            if duration_count >= self.gone_duration:
                                state = _("gone")
                                proxiCmdCounter = 0
                                duration_count = 0
                                if not self.Simulate:
                                    # start the process asynchronously so we are not hanging here...
                                    timerGone = gobject.timeout_add(5,self.go_gone)
                                    #self.go_gone()
                        else:
                            duration_count = 0
                            proxiCmdCounter = proxiCmdCounter + 1
                    #if dist != self.Dist or state != self.State:
                        #print "Detected distance atm: " + str(dist) + "; state is " + state
                        #pass
                    self.State = state
                    self.Dist = dist
                    # let's handle the proximity command
                    if (proxiCmdCounter >= self.config['proximity_interval']) and not self.Simulate and (self.config['proximity_command']!=''):
                        proxiCmdCounter = 0
                        # start the process asynchronously so we are not hanging here...
                        timerProx = gobject.timeout_add(5,self.go_proximity)
                    time.sleep(1)
                except KeyboardInterrupt:
                    break
        self.kill_connection()

if __name__=='__main__':
    # User name
    #uname = os.path.split(os.path.expanduser('~'))[-1]
    uname = os.path.split(os.getenv('HOME'))[-1]
    # Src directory path
    #sdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    sdir = os.getcwd()
    # Directories: config, data, log
    udir = os.path.join(os.getenv('HOME'), '.blueproximity-plus')
    conf_dir = os.path.join(udir, 'config')
    data_dir = os.path.join(udir, 'data')
    log_dir = os.path.join(udir, 'log')
    try:
        os.mkdir(udir)
        os.chmod(udir, 0775)
    except OSError:
        pass
    try:
        os.mkdir(conf_dir)
        os.chmod(conf_dir, 0775)
    except OSError:
        pass
    try:
        os.mkdir(data_dir)
        os.chmod(data_dir, 0775)
    except OSError:
        pass
    try:
        os.mkdir(log_dir)
        os.chmod(log_dir, 0775)
    except OSError:
        pass

    TAG = 'MAIN'
    # Start Logging thread
    log_queue = Queue.Queue()
    log_lock = threading.Lock()
    l = Logging(log_dir, log_queue, log_lock)
    l.start()
    log(log_queue, log_lock, TAG, 'Proximity started')
    
    # Initialize LocalUuid, Sample, Connection
    db_queue = Queue.Queue()
    db_lock = threading.Lock()
    db = DBHelper(data_dir, db_queue, db_lock)
    db.start()

    uuid = get_uuid()
    sample = Sample(data_dir)


    dec_queue = Queue.Queue()
    dec_lock = threading.Lock()
    calculate = Calculate(log_queue, log_lock, dec_queue, dec_lock, sample)
    calculate.start()

    client = Client(data_dir, db, db_queue, db_lock, log_queue, log_lock, uuid, sample, dec_queue, dec_lock)
    client.start()

    gtk.glade.bindtextdomain(APP_NAME, local_path)
    gtk.glade.textdomain(APP_NAME)

    
    # react on ^C
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    # read config if any
    configs = []
    new_config = True
    #conf_dir = os.path.join(os.getenv('HOME'),'.blueproximity')

    # now look for .conf files in there
    vdt = Validator()
    for filename in os.listdir(conf_dir):
        if filename.endswith('.conf'):
            try:
                # add every valid .conf file to the array of configs
                config = ConfigObj(os.path.join(conf_dir,filename),{'create_empty':False,'file_error':True,'configspec':conf_specs})
                # first validate it
                config.validate(vdt, copy=True)
                # rewrite it in a secure manner
                config.write()
                # if everything worked add this config as functioning
                configs.append ( [filename[:-5], config])
                new_config = False
                print(_("Using config file '%s'.") % filename)
            except:
                print(_("'%s' is not a valid config file.") % filename)

    # no previous configuration could be found so let's create a new one
    if new_config:
        config = ConfigObj(os.path.join(conf_dir, _('standard') + '.conf'),{'create_empty':True,'file_error':False,'configspec':conf_specs})
        # next line fixes a problem with creating empty strings in default values for configobj
        config['device_mac'] = ''
        config['device_uuid'] = ''
        config['proximity_command'] = 'dbus-send --session --type=method_call --dest=org.gnome.ScreenSaver /org/gnome/ScreenSaver org.gnome.ScreenSaver.SimulateUserActivity'
        config.validate(vdt, copy=True)
        # write it in a secure manner
        config.write()
        configs.append ( [_('standard'), config])
        # we can't log these messages since logging is not yet configured, so we just print it to stdout
        print(_("Creating new configuration."))
        print(_("Using config file '%s'.") % _('standard'))
    
    # now start the proximity detection for each configuration
    for config in configs:
        p = Proximity(config[1], data_dir, log_queue, log_lock, uname, uuid, sample, client, dec_queue, dec_lock,
                      calculate)
        p.start()
        config.append(p)
    
    configs.sort()
    # the idea behind 'configs' is an array containing the name, the configobj and the proximity object
    pGui = ProximityGUI(configs, new_config)

    # make GTK threadable 
    gtk.gdk.threads_init()

    # aaaaand action!
    gtk.main()
    
