#!/usr/bin/env python
"""
    obstartup
    ~~~~~~~~~

    A user-friendly Openbox autostart.sh configurator.

    :copyright: Copyright 2010 David Gidwani.
    :license: BSD style, see LICENSE
"""
import pygtk
pygtk.require("2.0")
import gtk
import gobject
import os
import sys


__version__ = "0.0.1"


class StartupEntry(list):
    """Represents a startup (shell) command."""

    def __init__(self, command, enabled=True):
        super(StartupEntry, self).__init__()
        self.extend([enabled, command])

    @property
    def command(self):
        return self[1]

    @property
    def enabled(self):
        return self[0]

    @staticmethod
    def from_string(string):
        command = string.strip()
        assert command, "Empty string"
        enabled = True
        if command.startswith("#"):
            enabled = False
            command = command[1:].strip()
        if command.endswith("&"):
            command = command[:-1].strip()
        return StartupEntry(command, enabled)

    def to_string(self):
        command = self.command
        if not self.enabled:
            command = "# {0}".format(command)
        return "{0} &".format(command)

    def enable(self):
        if not self.enabled:
            self[1] = True
            return True

    def disable(self):
        if self.enabled:
            self[1] = True
            return True

    def set_command(self, string):
        string = string.strip()
        if not string.endswith("&"):
            string = string + " &"
        self[0] = string

    def __repr__(self):
        return "<{0}(command='{1}', enabled={2})>".format(
            self.__class__.__name__, self.command, self.enabled)


class StartupList(list):
    """A collection of commands."""

    def write_to_file(self, filename="autostart.sh"):
        list_with_newlines = map(lambda e: e.to_string() + "\n", self)
        with open(filename, "w") as f:
            f.writelines(list_with_newlines)

    @staticmethod
    def load_from_file(filename):
        startup_list = StartupList()
        with open(filename, "r") as f:
            for line in f.readlines():
                try:
                    startup_list.append(StartupEntry.from_string(line))
                except AssertionError:
                    continue
        return startup_list


class ObStartup(object):

    openbox_config_directory = os.path.expanduser("~/.config/openbox")
    autostart_file = os.path.join(openbox_config_directory, "autostart.sh")

    def __init__(self):
        self.builder = gtk.Builder()
        self.builder.add_from_file("obstartup.glade")
        self.window = self.builder.get_object("main_window")
        self.builder.connect_signals(self)
        self.currently_opened = self.original_list = None

        self.load_autostart_file()
        self.window.show()

        self.sorted = self.unsaved = False
        self.builder.get_object("about_dialog").set_version(__version__)

    @property
    def startup_list(self):
        return self.builder.get_object("startup_list")

    @property
    def startup_list_store(self):
        return self.builder.get_object("startup_list_store")

    @property
    def row_count(self):
        return self.startup_list_store.iter_n_children(None)

    def calculate_unsaved(self):
        """Expensive way of checking if the startup list is unsaved or not. """
        if not hasattr(self, "original_list"): return False
        startup_list = StartupList(self.iterate_items())
        self.unsaved = (startup_list != self.original_list and True or False)
        return self.unsaved

    def message(self, parent=None, flags=0, type_=gtk.MESSAGE_INFO,
        buttons=gtk.BUTTONS_NONE, message_format=None):
        dialog = gtk.MessageDialog(parent, flags, type_,
            buttons, message_format)
        result = dialog.run()
        dialog.destroy()
        return result

    def question(self, message):
        result = self.message(type_=gtk.MESSAGE_QUESTION,
            buttons=gtk.BUTTONS_YES_NO, message_format=message)
        if result == gtk.RESPONSE_YES:
            return True
        return False

    def load_autostart_file(self):
        if not os.path.exists(self.autostart_file):
            if question("No autostart.sh found. Create one?"):
                open(self.autostart_file, "w").close()
        self.load_from_file(self.autostart_file)

    def load_from_file(self, filename):
        self.startup_list_store.clear()
        startup_list = StartupList.load_from_file(self.autostart_file)
        map(lambda i: self.startup_list_store.append(i), startup_list)
        self.original_list = startup_list
        self.currently_opened = filename
        for menu in ("file_close", "file_save_as"):
            self.builder.get_object(menu).set_sensitive(True)
        self._set_unsaved()
        return startup_list

    def file_select(self, action=gtk.FILE_CHOOSER_ACTION_OPEN,
        initial_path=openbox_config_directory, suggested_file="autostart.sh"):
        if action == gtk.FILE_CHOOSER_ACTION_OPEN:
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OPEN, gtk.RESPONSE_OK)
            title = "Open"
        elif action == gtk.FILE_CHOOSER_ACTION_SAVE:
            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_SAVE, gtk.RESPONSE_OK)
            title = "Save as"
        else:
            raise ValueError("Invalid action")
        chooser = gtk.FileChooserDialog(title=title, action=action,
          buttons=buttons)

        sh_filter = gtk.FileFilter()
        sh_filter.set_name("Shell scripts")
        sh_filter.add_pattern("*.sh")

        all_files_filter = gtk.FileFilter()
        all_files_filter.set_name("All Files")
        all_files_filter.add_pattern("*")

        map(lambda f: chooser.add_filter(f), (sh_filter, all_files_filter))

        if os.path.exists(self.autostart_file):
            chooser.set_filename(self.autostart_file)
        elif os.path.exists(self.openbox_config_directory):
            chooser.set_current_folder(self.openbox_config_directory)

        result = ""
        if chooser.run() == gtk.RESPONSE_OK:
            result = chooser.get_filename()
        chooser.destroy()
        return result

    def iterate_items(self):
        iterator = self.startup_list_store.get_iter_root()
        while iterator:
            item = StartupEntry(*reversed([
                self.startup_list_store.get_value(iterator, i)
                for i in range(2)]))
            yield item
            iterator = self.startup_list_store.iter_next(iterator)

    def move_selected_up(self):
        selected_iter = self.startup_list.get_selection().get_selected()[1]
        selected_path = self.startup_list_store.get_path(selected_iter)
        position = selected_path[-1]
        if position == 0: return False
        previous_path = list(selected_path)[:-1]
        previous_path.append(position - 1)
        previous_iter = self.startup_list_store.get_iter(tuple(previous_path))
        # TODO: handle GtkWarning when sorted
        self.startup_list_store.swap(selected_iter, previous_iter)
        self._set_unsaved()
        self._check_sensitive()

    def move_selected_down(self):
        selected_iter = self.startup_list.get_selection().get_selected()[1]
        next_iter = self.startup_list_store.iter_next(selected_iter)
        # TODO: handle GtkWarning when sorted
        self.startup_list_store.swap(selected_iter, next_iter)
        selected_iter_path = self.startup_list_store.get_path(selected_iter)[0]
        self._set_unsaved()
        self._check_sensitive()

    def add_item(self):
        selected_iter = self.startup_list.get_selection().get_selected()[1]
        if selected_iter:
            path = self.startup_list_store.get_path(selected_iter)[0]
        else:
            path = self.row_count
        self.startup_list_store.insert(path, [True, "Enter a command"])
        self.startup_list.set_cursor(path, self.startup_list.get_column(1),
            True)
        if self.row_count > 1: return
        self._set_unsaved()
        self._check_sensitive()

    def remove_selected_item(self):
        selected_iter = self.startup_list.get_selection().get_selected()[1]
        if not selected_iter: return
        self.startup_list_store.remove(selected_iter)
        self._set_unsaved()
        self._check_sensitive()

    def save(self, show_dialog=False):
        if not self.calculate_unsaved():
            self.message(message_format="Data is identical. Skipping save.",
                buttons=gtk.BUTTONS_OK)
            return
        if self.sorted and not self.question("You have sorted one or more "\
                "columns which is why you will be unable to move any " \
                "entries up or down. File contents will be in the same " \
                "order as currently sorted. Are you sure you want to save?"):
            return
        if self.currently_opened and not show_dialog:
            filename = self.currently_opened
        else:
            filename = self.file_select(action=gtk.FILE_CHOOSER_ACTION_SAVE)
            if not filename: return
        startup_list = StartupList(self.iterate_items())
        startup_list.write_to_file(filename)
        self._set_unsaved(False)
        self.original_list = startup_list

    def save_and_quit(self):
        if (not self.unsaved or self.unsaved and self.question(
            "Startup list has been modified but not saved. Really quit?")):
            gtk.main_quit()
        return True

    def _check_sensitive(self, row=None):
        if not row:
            selected = self.startup_list.get_selection().get_selected_rows()[1]
            for item in ("remove_button", "edit_remove"):
                self.builder.get_object(item).set_sensitive(
                    selected and True or False)
            if not selected or self.sorted:
                for item in ("edit_up", "up_button", "edit_down",
                    "down_button"):
                    self.builder.get_object(item).set_sensitive(False)
                return
            row = selected[0][0]

        for item in ("up_button", "edit_up"):
            self.builder.get_object(item).set_sensitive(
                True if row > 0 else False)

        for item in ("down_button", "edit_down"):
            self.builder.get_object(item).set_sensitive(
                True if row < self.row_count - 1 else False)

        if self.row_count <= 1:
            for item in ("file_save", "file_save_as", "file_close",
                "edit_up", "edit_down", "up_button", "down_button"):
                self.builder.get_object(item).set_sensitive(False)

        self.builder.get_object("file_save").set_sensitive(
            True if self.unsaved else False)

    def _set_unsaved(self, value=True):
        if not hasattr(self, "unsaved"): return
        self.unsaved = value
        self.builder.get_object("file_save").set_sensitive(value)

    def on_file_open_activate(self, widget):
        filename = self.file_select(action=gtk.FILE_CHOOSER_ACTION_OPEN)
        if filename:
            self.load_from_file(filename)

    def on_file_save_activate(self, widget):
        self.save()

    def on_file_save_as_activate(self, widget):
        self.save(show_dialog=True)

    def on_file_close_activate(self, widget):
        self.startup_list_store.clear()
        self.original_list = StartupList()
        for menu in ("file_close", "file_save", "file_save_as",
            "edit_remove", "edit_up", "edit_down", "remove_button",
            "up_button", "down_button"):
            self.builder.get_object(menu).set_sensitive(False)

    def on_file_quit_activate(self, widget):
        self.save_and_quit()

    def on_edit_down_activate(self, widget):
        self.move_selected_down()

    def on_edit_up_activate(self, widget):
        self.move_selected_up()

    def on_edit_add_activate(self, widget):
        self.add_item()

    def on_edit_remove_activate(self, widget):
        self.remove_selected_item()

    def on_help_about_activate(self, widget):
        about_dialog = self.builder.get_object("about_dialog")
        about_dialog.show()

    def on_enabled_cell_toggled(self, widget, path, *user_data):
        iterator = self.startup_list_store.get_iter_from_string(path)
        enabled = not self.startup_list_store.get_value(iterator, 0)
        self.startup_list_store.set(iterator, 0, enabled)

    def on_command_cell_edited(self, widget, path, new_text, *user_data):
        iterator = self.startup_list_store.get_iter_from_string(path)
        command = self.startup_list_store.get_value(iterator, 1)
        if command != new_text and new_text != "":
            self.startup_list_store.set(iterator, 1, new_text)
        self._set_unsaved()

    def on_startup_list_cursor_changed(self, widget, *user_data):
        self._check_sensitive()

    def on_startup_list_store_row_inserted(self, model, path, iterator,
        *user_data):
        self._set_unsaved()

    def on_startup_list_store_row_deleted(self, model, path, *user_data):
        self._set_unsaved()

    def on_enabled_col_clicked(self, column, *user_data):
        # TODO: permanent fix for resorting columns for saving and further
        # reordering via Up/Down buttons or menu items.
        self.sorted = True

    def on_add_button_clicked(self, widget):
        self.add_item()

    def on_remove_button_clicked(self, widget):
        self.remove_selected_item()

    def on_down_button_clicked(self, widget):
        self.move_selected_down()

    def on_up_button_clicked(self, widget):
        self.move_selected_up()

    def on_save_button_clicked(self, widget):
        self.save()

    def on_main_window_delete_event(self, widget, event, *user_data):
        return self.save_and_quit()

    def on_main_window_destroy(self, widget):
        self.save_and_quit()

    def on_about_dialog_response(self, widget, response_id):
        if response_id in (gtk.RESPONSE_CANCEL, gtk.RESPONSE_CLOSE,
            gtk.RESPONSE_DELETE_EVENT):
            widget.hide()

    def on_about_dialog_delete_event(self, widget, event, *user_data):
        widget.hide()
        return True


if __name__ == "__main__":
    ObStartup()
    gtk.main()