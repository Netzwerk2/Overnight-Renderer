#!/bin/python3

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Notify", "0.7")

from gi.repository import Gtk, Notify, Gdk, Gio  # noqa: E402

import os   # noqa: E402
import glob  # noqa: E402
import trio  # noqa: E402
import trio_gtk  # noqa: E402
import subprocess  # noqa: E402
import re  # noqa: E402
from typing import List, Optional, Tuple  # noqa: E402

from widgets import create_label, create_entry, create_combo_box, \
    create_tree_view, create_file_chooser_button, \
    create_spin_button  # noqa: E402

from render_task import RenderTask  # noqa: E402

from convert_input_to_argument import convert_output_format, \
    convert_animation, convert_render_device, convert_render_samples, \
    convert_resolution_x, convert_resolution_y, \
    convert_resolution_percentage, convert_single_frame  # noqa: E402

from config import Config, ConfigDialog  # noqa: E402

from render_info import RenderInfo  # noqa: E402


os.chdir(os.path.dirname(os.path.abspath(__file__)))

config: Optional[Config] = None


class MainWindow(Gtk.Window):
    stack: Gtk.Stack = None
    info_bar: Gtk.InfoBar = None
    info_bar_label: Gtk.Label = None
    blend_files_tree_view: Gtk.TreeView = None
    blend_files_store: Gtk.TreeStore = None
    blend_file_chooser_button: Gtk.FileChooserButton = None
    render_engine_combo_box: Gtk.ComboBox = None
    render_device_combo_box: Gtk.ComboBox = None
    render_samples_spin: Gtk.SpinButton = None
    resolution_x_spin: Gtk.SpinButton = None
    resolution_y_spin: Gtk.SpinButton = None
    resolution_percentage_spin: Gtk.SpinButton = None
    output_type_combo_box: Gtk.ComboBox = None
    start_frame_spin: Gtk.SpinButton = None
    end_frame_spin: Gtk.SpinButton = None
    output_format_combo_box: Gtk.ComboBox = None
    output_name_entry: Gtk.Entry = None
    output_path_chooser_button: Gtk.FileChooserButton = None
    python_expressions_entry: Gtk.Entry = None
    post_rendering_combo_box: Gtk.ComboBox = None
    render_button: Gtk.Button = None
    queue_button: Gtk.Button = None
    render_tasks_store: Gtk.ListStore = None

    layers: List[str] = []
    render_queue: List[RenderTask] = []
    current_render_task: Optional[RenderTask] = None
    process: Optional[trio.Process] = None

    def __init__(self, nursery: trio.Nursery) -> None:
        super(MainWindow, self).__init__()
        self.set_title("Overnight Renderer")
        self.set_border_width(20)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.do_post_rendering = True

        self.nursery = nursery

        self.create_content()

    def create_content(self) -> None:
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(
            Gtk.StackTransitionType.SLIDE_LEFT_RIGHT
        )
        self.stack.set_transition_duration(150)

        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_halign(Gtk.Align.CENTER)
        stack_switcher.set_stack(self.stack)

        settings_button = Gtk.Button()
        settings_button.set_tooltip_text("Settings")
        settings_button.connect("clicked", self.on_settings_clicked)
        settings_icon = Gio.ThemedIcon(name="emblem-system-symbolic")
        settings_image = Gtk.Image.new_from_gicon(
            settings_icon, Gtk.IconSize.BUTTON
        )
        settings_button.add(settings_image)

        reload_button = Gtk.Button()
        reload_button.set_tooltip_text("Reload .blend files")
        reload_button.connect("clicked", self.on_reload_clicked)
        reload_icon = Gio.ThemedIcon(name="view-refresh-symbolic")
        reload_image = Gtk.Image.new_from_gicon(
            reload_icon, Gtk.IconSize.BUTTON
        )
        reload_button.add(reload_image)

        self.info_bar = Gtk.InfoBar()
        self.info_bar.set_revealed(False)
        self.info_bar_label = create_label("")
        self.info_bar_label.set_line_wrap(True)
        self.info_bar.get_content_area().pack_start(
            self.info_bar_label, True, False, 0
        )

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_halign(Gtk.Align.CENTER)
        vbox.pack_start(self.info_bar, True, False, 0)
        vbox.pack_start(stack_switcher, True, False, 0)
        vbox.pack_start(self.stack, True, False, 0)

        header_bar = Gtk.HeaderBar(title="Overnight Renderer")
        header_bar.set_show_close_button(True)
        header_bar.pack_start(reload_button)
        header_bar.pack_end(settings_button)

        self.blend_files_store = Gtk.TreeStore(str)
        self.blend_files_tree_view = create_tree_view(
            self.blend_files_store, ["File"]
        )
        self.blend_files_tree_view.set_enable_tree_lines(True)
        self.blend_files_tree_view.connect(
            "button-press-event", self.on_blend_cell_clicked
        )

        blend_files_scrolled = Gtk.ScrolledWindow()
        blend_files_scrolled.set_policy(
            Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC
        )
        blend_files_scrolled.add(self.blend_files_tree_view)

        blend_file_label = create_label("Path to .blend file")
        self.blend_file_chooser_button = create_file_chooser_button(
            self, "Select .blend file", Gtk.FileChooserAction.OPEN,
            Gtk.STOCK_OPEN, True
        )
        self.blend_file_chooser_button.connect(
            "file-set", self.on_blend_file_clicked
        )

        render_engine_label = create_label("Render Engine")
        engine_store = Gtk.ListStore(str, str)
        engine_store.append(["Eevee", "BLENDER_EEVEE"])
        engine_store.append(["Workbench", "BLENDER_WORKBENCH"])
        engine_store.append(["Cycles", "CYCLES"])

        self.render_engine_combo_box = create_combo_box(store=engine_store)

        render_device_label = create_label("Cycles Render Device")
        render_devices = ["CPU", "GPU"]
        self.render_device_combo_box = create_combo_box(labels=render_devices)

        render_samples_label = create_label("Samples")
        self.render_samples_spin = create_spin_button(128, 1, 16777216)

        resolution_x_label = create_label("Resolution X")
        self.resolution_x_spin = create_spin_button(1920, 4, 65536)
        self.resolution_x_spin.connect("output", self.on_resolution_x_y_output)

        resolution_y_label = create_label("Resolution Y")
        self.resolution_y_spin = create_spin_button(1080, 4, 65536)
        self.resolution_y_spin.connect("output", self.on_resolution_x_y_output)

        resolution_percentage_label = create_label("Resolution Percentage")
        self.resolution_percentage_spin = create_spin_button(100, 1, 32767)
        self.resolution_percentage_spin.connect(
            "output", self.on_resolution_percentage_output
        )

        output_type_label = create_label("Output Type")
        output_types = ["Single Frame", "Animation"]
        self.output_type_combo_box = create_combo_box(labels=output_types)
        self.output_type_combo_box.connect(
            "changed", self.on_output_type_changed
        )

        start_frame_label = create_label("Start Frame")
        self.start_frame_spin = create_spin_button(1, 0, 1048574)

        end_frame_label = create_label("End Frame")
        self.end_frame_spin = create_spin_button(250, 0, 1048574)
        self.end_frame_spin.set_sensitive(False)

        output_format_label = create_label("Output Format")
        format_store = Gtk.ListStore(str, str)
        format_store.append([".blend file", ".blend file"])
        format_store.append(["BMP", "BMP"])
        format_store.append(["Iris", "IRIS"])
        format_store.append(["PNG", "PNG"])
        format_store.append(["JPEG", "JPEG"])
        format_store.append(["Targa", "TGA"])
        format_store.append(["Targe Raw", "RAWTGA"])
        format_store.append(["Cineon", "CINEON"])
        format_store.append(["DPX", "DPX"])
        format_store.append(["OpenEXR Multilayer", "OPEN_EXR_MULTILAYER"])
        format_store.append(["OpenEXR", "OPEN_EXR"])
        format_store.append(["Radiance HDR", "HDR"])
        format_store.append(["TIFF", "TIFF"])
        format_store.append(["AVI JPEG", "AVIJPEG"])
        format_store.append(["AVI Raw", "AVIRAW"])
        format_store.append(["FFmpeg video", "MPEG"])
        self.output_format_combo_box = create_combo_box(store=format_store)

        output_name_label = create_label("Output Name")
        self.output_name_entry = create_entry("Render")

        output_path_label = create_label("Output Path")
        self.output_path_chooser_button = create_file_chooser_button(
            self, "Select output file directory",
            Gtk.FileChooserAction.SELECT_FOLDER, Gtk.STOCK_OPEN, False
        )

        python_expressions_label = create_label("Python Expressions")
        self.python_expressions_entry = create_entry()

        post_rendering_label = create_label("After rendering is finished")
        post_rendering_options = ["Do nothing", "Suspend", "Shutdown"]
        self.post_rendering_combo_box = create_combo_box(
            labels=post_rendering_options
        )

        self.queue_button = Gtk.Button(label="Queue")
        self.queue_button.get_style_context().add_class("suggested-action")
        self.queue_button.connect("clicked", self.on_queue_clicked)

        self.render_tasks_store = Gtk.ListStore(str, str, str, str, int)
        columns = ["File", "Engine", "Type", "Output"]
        queue_tree_view = create_tree_view(self.render_tasks_store, columns)
        queue_tree_view.connect(
            "key-press-event", self.on_queue_tree_view_key_pressed
        )
        queue_tree_view.set_grid_lines(Gtk.TreeViewGridLines.VERTICAL)
        finished_progress_renderer = Gtk.CellRendererProgress()
        finished_progress_column = Gtk.TreeViewColumn(
            "Progress", finished_progress_renderer, value=4
        )
        finished_progress_column.set_min_width(200)
        queue_tree_view.append_column(finished_progress_column)

        self.render_button = Gtk.Button(label="Render")
        self.render_button.set_sensitive(False)
        self.render_button.set_size_request(0, 0)
        self.render_button.get_style_context().add_class("suggested-action")
        self.render_button.connect("clicked", self.on_render_clicked)

        queue_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        queue_vbox.set_halign(Gtk.Align.CENTER)
        queue_vbox.pack_start(queue_tree_view, True, True, 6)
        queue_vbox.pack_start(self.render_button, False, False, 6)

        grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.CENTER)
        grid.attach(blend_file_label, 0, 0, 1, 1)
        grid.attach(self.blend_file_chooser_button, 1, 0, 1, 1)
        grid.attach(render_engine_label, 0, 1, 1, 1)
        grid.attach(self.render_engine_combo_box, 1, 1, 1, 1)
        grid.attach(render_device_label, 0, 2, 1, 1)
        grid.attach(self.render_device_combo_box, 1, 2, 1, 1)
        grid.attach(render_samples_label, 0, 3, 1, 1)
        grid.attach(self.render_samples_spin, 1, 3, 1, 1)
        grid.attach(resolution_x_label, 0, 4, 1, 1)
        grid.attach(self.resolution_x_spin, 1, 4, 1, 1)
        grid.attach(resolution_y_label, 0, 5, 1, 1)
        grid.attach(self.resolution_y_spin, 1, 5, 1, 1)
        grid.attach(resolution_percentage_label, 0, 6, 1, 1)
        grid.attach(self.resolution_percentage_spin, 1, 6, 1, 1)
        grid.attach(output_type_label, 0, 7, 1, 1)
        grid.attach(self.output_type_combo_box, 1, 7, 1, 1)
        grid.attach(start_frame_label, 0, 8, 1, 1)
        grid.attach(self.start_frame_spin, 1, 8, 1, 1)
        grid.attach(end_frame_label, 0, 9, 1, 1)
        grid.attach(self.end_frame_spin, 1, 9, 1, 1)
        grid.attach(output_format_label, 0, 10, 1, 1)
        grid.attach(self.output_format_combo_box, 1, 10, 1, 1)
        grid.attach(output_name_label, 0, 11, 1, 1)
        grid.attach(self.output_name_entry, 1, 11, 1, 1)
        grid.attach(output_path_label, 0, 12, 1, 1)
        grid.attach(self.output_path_chooser_button, 1, 12, 1, 1)
        grid.attach(python_expressions_label, 0, 13, 1, 1)
        grid.attach(self.python_expressions_entry, 1, 13, 1, 1)
        grid.attach(post_rendering_label, 0, 14, 1, 1)
        grid.attach(self.post_rendering_combo_box, 1, 14, 1, 1)
        grid.attach(self.queue_button, 1, 15, 1, 1)

        self.stack.add_titled(
            blend_files_scrolled, "blend_files", "Blend Files"
        )
        self.stack.add_titled(grid, "render_settings", "Render Settings")
        self.stack.add_titled(queue_vbox, "queue", "Queue")

        self.set_titlebar(header_bar)
        self.add(vbox)

    def on_settings_clicked(self, button: Gtk.Button) -> None:
        config_dialog = ConfigDialog(config)
        response = config_dialog.run()

        if response == Gtk.ResponseType.APPLY:
            settings = config.settings
            settings["blender_config"] = config_dialog \
                .blender_config_chooser_button.get_filename()
            settings["default_output_dir"] = config_dialog \
                .output_dir_chooser_button.get_filename()
            settings["default_blender_dir"] = config_dialog \
                .default_dir_chooser_button.get_filename()
            settings["post_rendering_timer"] = config_dialog \
                .post_rendering_spin.get_value_as_int()
            for i in range(6):
                render_info_iter = config_dialog.render_info_store.get_iter(i)
                settings["render_info"][i]["display_name"] = config_dialog \
                    .render_info_store[render_info_iter][0]
                settings["render_info"][i]["visible"] = config_dialog \
                    .render_info_store[render_info_iter][1]
                settings["render_info"][i]["name"] = config_dialog \
                    .render_info_store[render_info_iter][2]
            config.modify(settings)
        elif response == Gtk.ResponseType.CANCEL:
            pass

        config_dialog.destroy()

    def on_reload_clicked(self, button: Gtk.Button) -> None:
        self.load_blend_files()

    def load_blend_files(self) -> None:
        self.blend_files_store.clear()

        try:
            file = open(
                f"{config.settings['blender_config']}/recent-files.txt", "r"
            )
            lines = file.readlines()
            file.close()

            recent_files_row = self.blend_files_store.append(None, ["Recent"])

            for line in lines:
                path = line.strip()
                self.blend_files_store.append(recent_files_row, [path])
        except IOError:
            pass

        default_dir_files_row = self.blend_files_store.append(
            None, ["Default Directory"]
        )

        for dir, _, _ in os.walk(config.settings["default_blender_dir"]):
            files = glob.glob(os.path.join(dir, "*.blend"))
            if files:
                for file in files:
                    self.blend_files_store.append(
                        default_dir_files_row, [file]
                    )

        self.blend_files_tree_view.expand_all()

    def on_blend_cell_clicked(
        self, tree_view: Gtk.TreeView, event: Gdk.EventButton
    ) -> None:
        if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
            selection = tree_view.get_selection()
            model, tree_iter = selection.get_selected()
            path = model[tree_iter][0]
            self.blend_file_chooser_button.set_filename(path)
            self.update_render_settings(path)
            self.stack.set_visible_child_name("render_settings")

    def on_blend_file_clicked(self, button: Gtk.FileChooserButton) -> None:
        self.update_render_settings(button.get_filename())

    def update_render_settings(self, path: str) -> None:
        self.load_file_info(path)
        if self.output_path_chooser_button.get_filename() == "/tmp" \
                or self.output_path_chooser_button.get_filename() is None:
            self.output_path_chooser_button \
                .set_filename(f"{config.settings['default_output_dir']}")

    def load_file_info(self, file_path: str) -> None:
        with subprocess.Popen(
            [
                "blender",
                "-b", file_path,
                "-P", os.path.abspath("blend_file_information.py"),
            ],
            stdout=subprocess.PIPE
        ) as process:
            output = process.stdout
            file_info = []
            ready = False
            for raw_line in output:
                line = raw_line.strip().decode("utf-8")
                if line == "READY":
                    ready = True
                    continue
                if ready:
                    file_info.append(line)

            if file_info[0] == "BLENDER_EEVEE":
                self.render_engine_combo_box.set_active(0)
                self.render_samples_spin.set_value(int(file_info[3]))
            elif file_info[0] == "BLENDER_WORKBENCH":
                self.render_engine_combo_box.set_active(1)
            elif file_info[0] == "CYCLES":
                self.render_engine_combo_box.set_active(2)
                self.render_samples_spin.set_value(int(file_info[2]))
            if file_info[1] == "CPU":
                self.render_device_combo_box.set_active(0)
            elif file_info[1] == "GPU":
                self.render_device_combo_box.set_active(1)
            self.resolution_x_spin.set_value(int(file_info[4]))
            self.resolution_y_spin.set_value(int(file_info[5]))
            self.resolution_percentage_spin.set_value(int(file_info[6]))
            self.start_frame_spin.set_value(int(file_info[7]))
            self.end_frame_spin.set_value(int(file_info[8]))
            self.output_path_chooser_button.set_filename(
                os.path.dirname(file_info[10])
            )
            layers = file_info[11].split(", ")
            self.layers = layers

    def on_resolution_x_y_output(self, spin_button: Gtk.SpinButton) -> bool:
        spin_button.set_text(f"{spin_button.get_value_as_int()} px")
        return True

    def on_resolution_percentage_output(
        self, spin_button: Gtk.SpinButton
    ) -> bool:
        spin_button.set_text(f"{spin_button.get_value_as_int()} %")
        return True

    def on_output_type_changed(self, combo_box: Gtk.ComboBox) -> None:
        output_type_iter = combo_box.get_active_iter()
        output_type_model = combo_box.get_model()
        output_type = output_type_model[output_type_iter][0]

        if output_type == "Animation":
            self.end_frame_spin.set_sensitive(True)
        elif output_type == "Single Frame":
            self.end_frame_spin.set_sensitive(False)

    def on_render_clicked(self, button: Gtk.Button) -> None:
        for render_task in self.render_queue:
            if not render_task.finished:
                self.current_render_task = render_task
                break

        self.render_button.set_sensitive(False)

        self.stack.set_visible_child_name("queue")

        self.nursery.start_soon(self.render)

    def on_queue_clicked(self, button: Gtk.Button) -> None:
        render_task, render_engine_display = self.create_render_task()
        if render_task.blend_file == "" or render_task.output_file == "":
            return
        self.add_render_task_to_tree_view(render_engine_display, render_task)
        if self.process is None:
            self.render_button.set_sensitive(True)
        self.stack.set_visible_child_name("queue")

    def create_render_task(self) -> Tuple[RenderTask, str]:
        blend_file = self.blend_file_chooser_button.get_filename()

        render_engine_iter = self.render_engine_combo_box.get_active_iter()
        render_engine_model = self.render_engine_combo_box.get_model()
        render_engine = render_engine_model[render_engine_iter][1]
        render_engine_display = render_engine_model[render_engine_iter][0]

        render_device_iter = self.render_device_combo_box.get_active_iter()
        render_device_model = self.render_device_combo_box.get_model()
        render_device = render_device_model[render_device_iter][0]

        render_samples = self.render_samples_spin.get_value_as_int()

        resolution_x = self.resolution_x_spin.get_value_as_int()

        resolution_y = self.resolution_y_spin.get_value_as_int()

        resolution_percentage = self.resolution_percentage_spin \
            .get_value_as_int()

        output_type_iter = self.output_type_combo_box.get_active_iter()
        output_type_model = self.output_type_combo_box.get_model()
        output_type = output_type_model[output_type_iter][0]

        start_frame = self.start_frame_spin.get_value_as_int()

        end_frame = self.end_frame_spin.get_value_as_int()

        output_format_iter = self.output_format_combo_box.get_active_iter()
        output_format_model = self.output_format_combo_box.get_model()
        output_format = output_format_model[output_format_iter][1]

        output_file = os.path.join(
            self.output_path_chooser_button.get_filename(),
            self.output_name_entry.get_text()
        )

        python_expressions = self.python_expressions_entry.get_text()

        layers = self.layers

        return RenderTask(
            blend_file, render_engine, render_device, render_samples,
            resolution_x, resolution_y, resolution_percentage, output_type,
            start_frame, end_frame, output_format, output_file,
            python_expressions, layers, False
        ), render_engine_display

    def add_render_task_to_tree_view(
        self, render_engine_display: str, render_task: RenderTask
    ) -> None:
        def frames_argument() -> str:
            output_type = render_task.output_type
            if output_type == "Animation":
                return f"{output_type}" \
                       f"({render_task.start_frame} - {render_task.end_frame})"
            elif output_type == "Single Frame":
                return f"{output_type} ({render_task.start_frame})"

        self.render_tasks_store.append([
            os.path.basename(render_task.blend_file),
            render_engine_display,
            frames_argument(),
            render_task.output_file,
            0
        ])
        self.render_queue.append(render_task)

    async def render(self) -> None:
        image_path = None
        cmd_line = [
            "blender",
            "-b", self.current_render_task.blend_file,
            "-E", self.current_render_task.render_engine,
            "-o", self.current_render_task.output_file,
        ] + convert_output_format(self.current_render_task.output_format) \
            + convert_animation(
                self.current_render_task.output_type,
                self.current_render_task.start_frame,
                self.current_render_task.end_frame
           ) \
            + [
                "--python-expr",
                "import bpy; "
                + convert_render_device(self.current_render_task.render_device)
                + convert_render_samples(
                    self.current_render_task.render_samples,
                    self.current_render_task.render_engine
                )
                + convert_resolution_x(self.current_render_task.resolution_x)
                + convert_resolution_y(self.current_render_task.resolution_y)
                + convert_resolution_percentage(
                    self.current_render_task.resolution_percentage
                )
                + f"{self.current_render_task.python_expressions}"
            ] \
            + convert_single_frame(
                self.current_render_task.output_type,
                self.current_render_task.start_frame
            )
        async with await trio.open_process(
            cmd_line,
            stdout=subprocess.PIPE
        ) as process:
            self.process = process
            self.info_bar.set_revealed(True)
            async for raw_line in process.stdout:
                line = raw_line.strip().decode("utf-8")
                parts = line.split("\n")

                if self.current_render_task.output_type == "Animation":
                    start_frame = self.current_render_task.start_frame
                    end_frame = self.current_render_task.end_frame
                else:
                    start_frame = self.current_render_task.start_frame
                    end_frame = self.current_render_task.start_frame
                info, progress = self.parse_blender_logs(
                    parts[-1], start_frame, end_frame
                )

                if info is not None:
                    self.info_bar_label.set_text(str(info))
                if progress is not None:
                    self.update_progress(progress)

                m = re.search(
                    r"^Saved: \s '(?P<path>.*)'",
                    line,
                    flags=re.VERBOSE
                )
                if m:
                    image_path = m.group("path")

        await self.post_rendering(image_path)

    def update_progress(self, progress: float) -> None:
        self.render_tasks_store[
            self.render_queue.index(self.current_render_task)
        ][4] = progress

    def parse_blender_logs(
        self, line: str, start_frame: int, end_frame: int
    ) -> Tuple[Optional[RenderInfo], Optional[int]]:
        m = re.search(
            r"""
            ^
            (?P<frame> [^|]*)
            \s \| \s
            (?P<time> Time: [^|]*)
            \s \| \s
            (?P<payload> .*?)
            \s*
            $
            """,
            line,
            flags=re.VERBOSE
        )

        if not m:
            return None, None

        frame = m.group("frame")
        time = m.group("time")
        payload = m.group("payload")
        remaining = None
        mem = None
        layer = None
        status = None
        progress = None

        if payload.startswith("Remaining:"):
            remaining, payload = payload.split(" | ", maxsplit=1)
        if payload.startswith("Mem:"):
            mem, layer, status = payload.split(" | ", maxsplit=2)
        elif payload.startswith("Compositing"):
            status = payload

        if self.current_render_task.render_engine == "CYCLES":
            if status is not None and status.startswith("Rendered "):
                progress = self.parse_status(
                    status, frame, start_frame, end_frame, layer
                )
        else:
            i_frame = int(re.search(
                "^ Fra: (?P<frame> [0-9]+)", frame, flags=re.VERBOSE
            ).group("frame"))
            progress = (i_frame - start_frame) \
                / (end_frame - start_frame + 1) * 100

        render_info = RenderInfo(
            frame, time, remaining, mem, layer, status, config
        )
        return render_info, progress

    def parse_status(
        self, status: str, frame: str, start_frame: int, end_frame: int,
        layer: str
    ) -> float:
        m = re.search(
            r"""
            ^
            Rendered \s+
            (?P<tiles> [0-9]+) / (?P<total_tiles> [0-9]+) \s+
            Tiles, \s+
            (
                Sample \s+
                (?P<samples> [0-9]+) / (?P<total_samples> [0-9]+)
            )?
            \b
            """,
            status,
            flags=re.VERBOSE
        )

        tiles = int(m.group("tiles"))
        total_tiles = int(m.group("total_tiles"))
        try:
            samples = int(m.group("samples"))
            total_samples = int(m.group("total_samples"))
        except TypeError:
            samples = 1
            total_samples = 1

        frame = int(re.search(
            "^ Fra: (?P<frame> [0-9]+)", frame, flags=re.VERBOSE
        ).group("frame"))

        if samples == total_samples:
            samples = 0

        layer = layer.split(", ")[1]
        layer_index = self.current_render_task.layers.index(layer)

        f_tiles = tiles + samples / total_samples
        f_layers = layer_index + f_tiles / total_tiles
        f_frames = frame + f_layers / len(self.current_render_task.layers)
        return (f_frames - start_frame) / (end_frame - start_frame + 1) * 100

    async def post_rendering(self, image_path: Optional[str]) -> None:
        print("Rendering complete!")
        Notify.init("Overnight Renderer")
        if image_path is not None:
            notification = Notify.Notification.new(
                "Rendering complete",
                "Rendering "
                f"{os.path.basename(self.current_render_task.blend_file)} "
                "finished",
                image_path
            )
        else:
            notification = Notify.Notification.new(
                "Rendering complete",
                "Rendering "
                f"{os.path.basename(self.current_render_task.blend_file)} "
                "finished"
            )
        notification.show()

        self.update_progress(100)

        self.process = None
        self.current_render_task.finished = True

        for render_task in self.render_queue:
            if not render_task.finished:
                self.current_render_task = render_task
                self.nursery.start_soon(self.render, self.current_render_task)
                return

        self.current_render_task = None

        self.info_bar.set_revealed(False)

        post_rendering_iter = self.post_rendering_combo_box.get_active_iter()
        post_rendering_model = self.post_rendering_combo_box.get_model()
        post_rendering_action = post_rendering_model[post_rendering_iter][0]

        timer = config.settings["post_rendering_timer"]

        if post_rendering_action == "Suspend":
            self.info_bar.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
            self.info_bar.set_message_type(Gtk.MessageType.WARNING)
            self.info_bar.connect("response", self.on_info_bar_cancel_pressed)
            self.info_bar.set_revealed(True)
            for i in range(timer):
                self.info_bar_label.set_text(f"Suspending in {timer - i} s")
                await trio.sleep(1)
            if self.do_post_rendering:
                print("Suspending...")
                subprocess.run(["systemctl", "suspend"])
        elif post_rendering_action == "Shutdown":
            self.info_bar.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
            self.info_bar.set_message_type(Gtk.MessageType.WARNING)
            self.info_bar.connect("response", self.on_info_bar_cancel_pressed)
            self.info_bar.set_revealed(True)
            for i in range(timer):
                self.info_bar_label.set_text(f"Shutting down in {timer - i} s")
                await trio.sleep(1)
            if self.do_post_rendering:
                print("Shutting down...")
                subprocess.run(["poweroff"])

    def on_info_bar_cancel_pressed(
        self, info_bar: Gtk.InfoBar, response: Gtk.ResponseType
    ) -> None:
        self.do_post_rendering = False
        self.info_bar.set_revealed(False)
        self.info_bar.set_message_type(Gtk.MessageType.INFO)

    def on_queue_tree_view_key_pressed(
        self, tree_view: Gtk.TreeView, event: Gdk.EventKey
    ) -> None:
        keyname = Gdk.keyval_name(event.keyval)
        render_task_index = tree_view.get_selection() \
            .get_selected_rows()[1][0][0]
        current_render_task_index = self.render_queue.index(
            self.current_render_task
        )
        if keyname == "Delete" \
                and render_task_index != current_render_task_index:
            del self.render_queue[render_task_index]
            model, iter = tree_view.get_selection().get_selected()
            model.remove(iter)


def main_quit(window: MainWindow, event: Gdk.Event) -> None:
    Gtk.main_quit()
    if window.process is not None:
        window.process.terminate()


async def main() -> None:
    async with trio.open_nursery() as nursery:
        global config
        try:
            config = Config.create_from_file("settings.toml")
        except IOError:
            config = Config.create_new()
            config.write()

        main_window = MainWindow(nursery)
        main_window.connect("delete-event", main_quit)
        main_window.show_all()
        main_window.load_blend_files()

        await trio.sleep_forever()


if __name__ == "__main__":
    trio_gtk.run(main)
