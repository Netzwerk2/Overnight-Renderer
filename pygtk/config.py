import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

import toml
import subprocess

from typing import Any, Dict
from widgets import create_label, create_file_chooser_button, create_tree_view


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
            "render_info": [
                {
                    "name": "frame",
                    "display_name": "Frame",
                    "visible": True
                },
                {
                    "name": "time",
                    "display_name": "Time",
                    "visible": True
                },
                {
                    "name": "remaining",
                    "display_name": "Remaining Time",
                    "visible": True
                },
                {
                    "name": "mem",
                    "display_name": "Memory",
                    "visible": True
                },
                {
                    "name": "layer",
                    "display_name": "Scene, Layer",
                    "visible": True
                },
                {
                    "name": "status",
                    "display_name": "Status",
                    "visible": True
                }
            ]
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
    blender_config_chooser_button = None
    default_dir_chooser_button = None
    output_dir_chooser_button = None
    render_info_model = None
    render_info_tree_view = None

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
        self.blender_config_chooser_button = create_file_chooser_button(
            self, "Select Blender config directory",
            Gtk.FileChooserAction.SELECT_FOLDER, Gtk.STOCK_OPEN, False
        )
        self.blender_config_chooser_button.set_filename(
            self.config.settings["blender_config"]
        )

        default_dir_label = create_label("Default Blender Directory")
        self.default_dir_chooser_button = create_file_chooser_button(
            self, "Select default Blender directory",
            Gtk.FileChooserAction.SELECT_FOLDER, Gtk.STOCK_OPEN, False
        )
        self.default_dir_chooser_button.set_filename(
            self.config.settings["default_blender_dir"]
        )

        output_dir_label = create_label("Default Output Directory")
        self.output_dir_chooser_button = create_file_chooser_button(
            self, "Select default output directory",
            Gtk.FileChooserAction.SELECT_FOLDER, Gtk.STOCK_OPEN, False
        )
        self.output_dir_chooser_button.set_filename(
            self.config.settings["default_output_dir"]
        )

        render_info_label = create_label("Render Information (Cycles only)")
        self.render_info_model = Gtk.ListStore(str, bool, str)
        for i in range(6):
            self.render_info_model.append(
                [
                    self.config.settings["render_info"][i]["display_name"],
                    self.config.settings["render_info"][i]["visible"],
                    self.config.settings["render_info"][i]["name"]
                ]
            )
        self.render_info_tree_view = create_tree_view(
            self.render_info_model, ["Category"]
        )
        self.render_info_tree_view.set_reorderable(True)
        visible_toggle_renderer = Gtk.CellRendererToggle()
        visible_toggle_renderer.connect("toggled", self.on_cell_toggled)
        visible_toggle_column = Gtk.TreeViewColumn(
            "Visible", visible_toggle_renderer, active=1
        )
        self.render_info_tree_view.append_column(visible_toggle_column)

        grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.CENTER)

        grid.attach(blender_config_label, 0, 0, 1, 1)
        grid.attach(self.blender_config_chooser_button, 1, 0, 1, 1)
        grid.attach(default_dir_label, 0, 1, 1, 1)
        grid.attach(self.default_dir_chooser_button, 1, 1, 1, 1)
        grid.attach(output_dir_label, 0, 2, 1, 1)
        grid.attach(self.output_dir_chooser_button, 1, 2, 1, 1)
        grid.attach(render_info_label, 0, 4, 1, 1)
        grid.attach(self.render_info_tree_view, 1, 4, 1, 1)

        self.set_titlebar(header_bar)
        self.get_content_area().add(grid)

        self.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_APPLY, Gtk.ResponseType.APPLY
        )

        self.show_all()

    def on_cell_toggled(
        self, cell_renderer_toggle: Gtk.CellRendererToggle, path: str
    ) -> None:
        self.render_info_model[path][1] = not self.render_info_model[path][1]

