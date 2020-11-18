import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

import os
import toml
import subprocess

from typing import Any, Dict
from widgets import create_entry, create_label

class Config:
    def __init__(self, settings: Dict[Any, Any]) -> None:
        self.settings = settings

    def create_new() -> "Config":
        config_dir = ""
        with subprocess.Popen(
            [
                "blender",
                "-b",
                "--python-expr",
                "import bpy; "
                + "print('config_dir'); "
                + "print(bpy.utils.user_resource('CONFIG'))"
            ],
            stdout=subprocess.PIPE
        ) as process:
            output = process.stdout
            finished = False
            for raw_line in output:
                line = raw_line.strip().decode("utf-8")
                if line == "config_dir":
                    finished = True
                elif finished:
                    config_dir = line
                    break

        settings = {
            "blender_config": config_dir,
            "default_blender_dir": "",
            "default_output_dir": "",
            "load_render_settings": True
        }

        return Config(settings)

    def create_from_file(path: str) -> "Config":
        file = open(path, "r")
        data = file.read()
        settings = toml.loads(data)
        return Config(settings)

    def modify(self, settings) -> "Config":
        self.settings.update(settings)
        self.write()

    def write(self) -> None:
        file = open("settings.toml", "w")
        file.write(toml.dumps(self.settings))
        file.close()


class ConfigDialog(Gtk.Dialog):
    blender_config_entry = None
    default_dir_entry = None
    output_dir_entry = None
    load_render_settings_check_button = None

    def __init__(self, config) -> None:
        super(ConfigDialog, self).__init__()
        self.set_title("Settings")
        self.set_border_width(20)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.config = config

        self.create_content()

    def create_content(self) -> None:
        header_bar = Gtk.HeaderBar(title="Settings")
        header_bar.set_show_close_button(True)
        header_bar.set_decoration_layout(":close")

        blender_config_label = create_label("Blender Config Directory")
        self.blender_config_entry = create_entry(False)
        self.blender_config_entry.set_text(self.config.settings["blender_config"])

        default_dir_label = create_label("Default Blender Directory")
        self.default_dir_entry = create_entry(False)
        self.default_dir_entry.set_text(self.config.settings["default_blender_dir"])

        output_dir_label = create_label("Default Output Directory")
        self.output_dir_entry = create_entry(False)
        self.output_dir_entry.set_text(self.config.settings["default_output_dir"])

        load_render_settings_label = create_label("Load render settings from selected .blend file")
        self.load_render_settings_check_button = Gtk.CheckButton()
        self.load_render_settings_check_button.set_active(self.config.settings["load_render_settings"])

        grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.CENTER)

        grid.attach(blender_config_label, 0, 0, 1, 1)
        grid.attach(self.blender_config_entry, 1, 0, 1, 1)
        grid.attach(default_dir_label, 0, 1, 1, 1)
        grid.attach(self.default_dir_entry, 1, 1, 1, 1)
        grid.attach(output_dir_label, 0, 2, 1, 1)
        grid.attach(self.output_dir_entry, 1, 2, 1, 1)
        grid.attach(load_render_settings_label, 0, 3, 1, 1)
        grid.attach(self.load_render_settings_check_button, 1, 3, 1, 1)

        self.set_titlebar(header_bar)
        self.get_content_area().add(grid)

        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_APPLY, Gtk.ResponseType.APPLY
        )

        self.show_all()

    def on_apply_clicked(self, button: Gtk.Button) -> None:
        pass

