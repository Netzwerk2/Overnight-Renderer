import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Notify", "0.7")
from gi.repository import Gtk, Notify, Gdk, Gio

import os
import glob
import trio
import trio_gtk
import subprocess
import re
from typing import Optional, Tuple

from widgets import create_label, create_entry, create_combo_box, create_tree_view, \
    create_file_chooser_button

from render_task import RenderTask

from convert_input_to_argument import convert_output_format, convert_animation, \
    convert_render_device, convert_render_samples, convert_resolution_x, \
    convert_resolution_y, convert_resolution_percentage, convert_single_frame

from config import Config, ConfigDialog

from render_info import RenderInfo

os.chdir(os.path.dirname(os.path.abspath(__file__)))

config: Optional[Config] = None


class MainWindow(Gtk.Window):
    stack = None
    info_bar = None
    info_bar_label = None
    blend_files_tree_view = None
    blend_files_model = Gtk.TreeStore(str)
    blend_file_chooser_button = None
    render_engine_combo_box = None
    render_device_combo_box = None
    render_samples_entry = None
    resolution_x_entry = None
    resolution_y_entry = None
    resolution_percentage_entry = None
    output_type_combo_box = None
    start_frame_entry = None
    end_frame_entry = None
    output_format_combo_box = None
    output_name_entry = None
    output_path_chooser_button = None
    python_expressions_entry = None
    post_rendering_combo_box = None
    render_button = None
    queue_button = None
    render_tasks_model = Gtk.ListStore(str, str, str, str, int)

    render_queue = []
    current_render_task = None
    process = None

    def __init__(self, nursery: trio.Nursery) -> None:
        super(MainWindow, self).__init__()
        self.set_title("Overnight Renderer")
        self.set_border_width(20)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.nursery = nursery

        self.create_content()

    def create_content(self) -> None:
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(150)

        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_halign(Gtk.Align.CENTER)
        stack_switcher.set_stack(self.stack)

        settings_button = Gtk.Button()
        settings_button.set_tooltip_text("Settings")
        settings_button.connect("clicked", self.on_settings_clicked)
        settings_icon = Gio.ThemedIcon(name="emblem-system-symbolic")
        settings_image = Gtk.Image.new_from_gicon(settings_icon, Gtk.IconSize.BUTTON)
        settings_button.add(settings_image)

        reload_button = Gtk.Button()
        reload_button.set_tooltip_text("Reload .blend files")
        reload_button.connect("clicked", self.on_reload_clicked)
        reload_icon = Gio.ThemedIcon(name="view-refresh-symbolic")
        reload_image = Gtk.Image.new_from_gicon(reload_icon, Gtk.IconSize.BUTTON)
        reload_button.add(reload_image)

        self.info_bar = Gtk.InfoBar()
        self.info_bar.set_revealed(False)
        self.info_bar_label = create_label("")
        self.info_bar.get_content_area().pack_start(self.info_bar_label, True, False, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_halign(Gtk.Align.CENTER)
        vbox.pack_start(self.info_bar, True, False, 0)
        vbox.pack_start(stack_switcher, True, False, 0)
        vbox.pack_start(self.stack, True, False, 0)

        header_bar = Gtk.HeaderBar(title="Overnight Renderer")
        header_bar.set_show_close_button(True)
        header_bar.pack_start(reload_button)
        header_bar.pack_end(settings_button)

        self.blend_files_tree_view = create_tree_view(self.blend_files_model, ["File"])
        self.blend_files_tree_view.set_grid_lines(Gtk.TreeViewGridLines.VERTICAL)
        self.blend_files_tree_view.connect("button-press-event", self.on_blend_cell_clicked)

        blend_files_scrolled = Gtk.ScrolledWindow()
        blend_files_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        blend_files_scrolled.add(self.blend_files_tree_view)

        number_entries_tooltip = "0 = Use from .blend file"

        blend_file_label = create_label("Path to .blend file")
        self.blend_file_chooser_button = create_file_chooser_button(
            self, "Select .blend file", Gtk.FileChooserAction.OPEN, Gtk.STOCK_OPEN, True
        )
        self.blend_file_chooser_button.connect("file-set", self.on_blend_file_clicked)

        render_engine_label = create_label("Render Engine")
        engine_store = Gtk.ListStore(str, str)
        engine_store.append(["Eevee", "BLENDER_EEVEE"])
        engine_store.append(["Workbench", "BLENDER_WORKBENCH"])
        engine_store.append(["Cycles", "CYCLES"])

        self.render_engine_combo_box = create_combo_box(model=engine_store)

        render_device_label = create_label("Cycles Render Device")
        render_devices = [".blend file", "CPU", "GPU"]
        self.render_device_combo_box = create_combo_box(labels=render_devices)

        render_samples_label = create_label("Samples")
        self.render_samples_entry = create_entry(True)
        self.render_samples_entry.set_text("0")
        self.render_samples_entry.set_tooltip_text(number_entries_tooltip)

        resolution_x_label = create_label("Resolution X")
        self.resolution_x_entry = create_entry(True)
        self.resolution_x_entry.set_text("0")
        self.resolution_x_entry.set_tooltip_text(number_entries_tooltip)

        resolution_y_label = create_label("Resolution Y")
        self.resolution_y_entry = create_entry(True)
        self.resolution_y_entry.set_text("0")
        self.resolution_y_entry.set_tooltip_text(number_entries_tooltip)

        resolution_percentage_label = create_label("Resolution %")
        self.resolution_percentage_entry = create_entry(True)
        self.resolution_percentage_entry.set_text("0")
        self.resolution_percentage_entry.set_tooltip_text(number_entries_tooltip)

        output_type_label = create_label("Output Type")
        output_types = ["Animation", "Single Frame"]
        self.output_type_combo_box = create_combo_box(labels=output_types)
        self.output_type_combo_box.set_active(1)
        self.output_type_combo_box.connect("changed", self.on_output_type_changed)

        start_frame_label = create_label("Start Frame")
        self.start_frame_entry = create_entry(True)
        self.start_frame_entry.set_text("1")

        end_frame_label = create_label("End Frame")
        self.end_frame_entry = create_entry(True)
        self.end_frame_entry.set_sensitive(False)
        self.end_frame_entry.set_text("250")

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
        self.output_format_combo_box = create_combo_box(model=format_store)

        output_name_label = create_label("Output Name")
        self.output_name_entry = create_entry(False)
        self.output_name_entry.set_text("Render")

        output_path_label = create_label("Output Path")
        self.output_path_chooser_button = create_file_chooser_button(
            self, "Select output file directory", Gtk.FileChooserAction.SELECT_FOLDER, Gtk.STOCK_OPEN, False
        )

        python_expressions_label = create_label("Python Expressions")
        self.python_expressions_entry = create_entry(False)

        post_rendering_label = create_label("After rendering is finished")
        post_rendering_options = ["Do nothing", "Suspend", "Shutdown"]
        self.post_rendering_combo_box = create_combo_box(
            labels=post_rendering_options
        )

        self.render_button = Gtk.Button(label="Render")
        self.render_button.connect("clicked", self.on_render_clicked)

        self.queue_button = Gtk.Button(label="Queue")
        self.queue_button.connect("clicked", self.on_queue_clicked)

        columns = ["File", "Engine", "Type", "Output"]
        queue_tree_view = create_tree_view(self.render_tasks_model, columns)
        queue_tree_view.connect("key-press-event", self.on_tree_view_key_pressed)
        queue_tree_view.set_grid_lines(Gtk.TreeViewGridLines.VERTICAL)
        finished_progress_renderer = Gtk.CellRendererProgress()
        finished_progress_column = Gtk.TreeViewColumn("Progress", finished_progress_renderer, value=4)
        queue_tree_view.append_column(finished_progress_column)

        grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        grid.set_halign(Gtk.Align.CENTER)
        grid.set_valign(Gtk.Align.CENTER)

        self.stack.add_titled(blend_files_scrolled, "blend_files", "Blend Files")
        self.stack.add_titled(grid, "render_settings", "Render Settings")
        self.stack.add_titled(queue_tree_view, "queue", "Queue")

        grid.attach(blend_file_label, 0, 0, 1, 1)
        grid.attach(self.blend_file_chooser_button, 1, 0, 1, 1)
        grid.attach(render_engine_label, 0, 1, 1, 1)
        grid.attach(self.render_engine_combo_box, 1, 1, 1, 1)
        grid.attach(render_device_label, 0, 2, 1, 1)
        grid.attach(self.render_device_combo_box, 1, 2, 1, 1)
        grid.attach(render_samples_label, 0, 3, 1, 1)
        grid.attach(self.render_samples_entry, 1, 3, 1, 1)
        grid.attach(resolution_x_label, 0, 4, 1, 1)
        grid.attach(self.resolution_x_entry, 1, 4, 1, 1)
        grid.attach(resolution_y_label, 0, 5, 1, 1)
        grid.attach(self.resolution_y_entry, 1, 5, 1, 1)
        grid.attach(resolution_percentage_label, 0, 6, 1, 1)
        grid.attach(self.resolution_percentage_entry, 1, 6, 1, 1)
        grid.attach(output_type_label, 0, 7, 1, 1)
        grid.attach(self.output_type_combo_box, 1, 7, 1, 1)
        grid.attach(start_frame_label, 0, 8, 1, 1)
        grid.attach(self.start_frame_entry, 1, 8, 1, 1)
        grid.attach(end_frame_label, 0, 9, 1, 1)
        grid.attach(self.end_frame_entry, 1, 9, 1, 1)
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
        grid.attach(self.render_button, 1, 15, 1, 1)
        grid.attach(self.queue_button, 1, 16, 1, 1)

        self.set_titlebar(header_bar)
        self.add(vbox)

    def on_settings_clicked(self, button: Gtk.Button) -> None:
        config_dialog = ConfigDialog(config)
        response = config_dialog.run()

        if response == Gtk.ResponseType.APPLY:
            settings = config.settings
            settings["blender_config"] = config_dialog.blender_config_chooser_button.get_filename()
            settings["default_output_dir"] = config_dialog.output_dir_chooser_button.get_filename()
            settings["default_blender_dir"] = config_dialog.default_dir_chooser_button.get_filename()
            settings["load_render_settings"] = config_dialog.load_render_settings_check_button.get_active()
            config.modify(settings)
        elif response == Gtk.ResponseType.CANCEL:
            pass

        config_dialog.destroy()

    def on_reload_clicked(self, button: Gtk.Button) -> None:
        self.load_blend_files()

    def load_blend_files(self) -> None:
        self.blend_files_model.clear()

        try:
            file = open(f"{config.settings['blender_config']}/recent-files.txt", "r")
            lines = file.readlines()
            file.close()

            recent_files_row = self.blend_files_model.append(None, ["Recent"])

            for line in lines:
                path = line.strip()
                self.blend_files_model.append(recent_files_row, [path])
        except IOError:
            pass

        default_dir_files_row = self.blend_files_model.append(None, ["Default Directory"])

        for dir, _, _ in os.walk(config.settings["default_blender_dir"]):
            files = glob.glob(os.path.join(dir, "*.blend"))
            if files:
                for file in files:
                    self.blend_files_model.append(default_dir_files_row, [file])

        self.blend_files_tree_view.expand_all()

    def on_blend_cell_clicked(self, tree_view: Gtk.TreeView, event: Gdk.EventButton) -> None:
        if event.button == 1 and event.type == Gdk.EventType._2BUTTON_PRESS:
            selection = tree_view.get_selection()
            model, tree_iter = selection.get_selected()
            path = model[tree_iter][0]
            self.blend_file_chooser_button.set_filename(path)
            self.set_output_dir(path)
            self.stack.set_visible_child_name("render_settings")

    def on_blend_file_clicked(self, button: Gtk.FileChooserButton) -> None:
        self.set_output_dir(button.get_filename())

    def set_output_dir(self, path: str) -> None:
        if config.settings["load_render_settings"]:
            self.load_render_settings(path)
        if self.output_path_chooser_button.get_filename() == "/tmp" or self.output_path_chooser_button.get_filename() is None:
            self.output_path_chooser_button.set_filename(f"{config.settings['default_output_dir']}")

    def load_render_settings(self, file_path: str) -> None:
        with subprocess.Popen(
            [
                "blender",
                "-b", file_path,
                "--python-expr",
                "import bpy; "
                + "print('\\nREADY'); "
                + "print(bpy.context.scene.render.engine); "
                + "print(bpy.context.scene.cycles.device); "
                + "print(bpy.context.scene.cycles.samples); "
                + "print(bpy.context.scene.eevee.taa_render_samples); "
                + "print(bpy.context.scene.render.resolution_x); "
                + "print(bpy.context.scene.render.resolution_y); "
                + "print(bpy.context.scene.render.resolution_percentage); "
                + "print(bpy.context.scene.frame_start); "
                + "print(bpy.context.scene.frame_end); "
                + "print(bpy.context.scene.render.image_settings.file_format); "
                + "print(bpy.context.scene.render.filepath); "
            ],
            stdout=subprocess.PIPE
        ) as process:
            output = process.stdout
            render_settings = []
            ready = False
            for raw_line in output:
                line = raw_line.strip().decode("utf-8")
                if line == "READY":
                    ready = True
                    continue
                if ready:
                    render_settings.append(line)

            if render_settings[0] == "BLENDER_EEVEE":
                self.render_engine_combo_box.set_active(0)
                self.render_samples_entry.set_text(render_settings[3])
            elif render_settings[0] == "CYCLES":
                self.render_engine_combo_box.set_active(2)
                self.render_samples_entry.set_text(render_settings[2])
            if render_settings[1] == "CPU":
                self.render_device_combo_box.set_active(1)
            elif render_settings[1] == "GPU":
                self.render_device_combo_box.set_active(2)
            self.resolution_x_entry.set_text(render_settings[4])
            self.resolution_y_entry.set_text(render_settings[5])
            self.resolution_percentage_entry.set_text(render_settings[6])
            self.start_frame_entry.set_text(render_settings[7])
            self.end_frame_entry.set_text(render_settings[8])
            self.output_path_chooser_button.set_filename(os.path.dirname(render_settings[10]))

    def on_output_type_changed(self, combo_box: Gtk.ComboBox) -> None:
        output_type_iter = combo_box.get_active_iter()
        output_type_model = combo_box.get_model()
        output_type = output_type_model[output_type_iter][0]

        if output_type == "Animation":
            self.end_frame_entry.set_sensitive(True)
        elif output_type == "Single Frame":
            self.end_frame_entry.set_sensitive(False)

    def on_render_clicked(self, button: Gtk.Button) -> None:
        if len(self.render_queue) == 0:
            render_task, render_engine_display = self.create_render_task()
            if render_task.blend_file == "" or render_task.output_file == "":
                return
            self.add_render_task_to_tree_view(render_engine_display, render_task)
            self.stack.set_visible_child_name("queue")
            self.current_render_task = self.render_queue[0]
        else:
            for render_task in self.render_queue:
                if not render_task.finished:
                    self.current_render_task = render_task

        self.render_button.set_sensitive(False)

        self.nursery.start_soon(self.render, self.current_render_task)

    def on_queue_clicked(self, button: Gtk.Button) -> None:
        render_task, render_engine_display = self.create_render_task()
        if render_task.blend_file == "" or render_task.output_file == "":
            return
        self.add_render_task_to_tree_view(render_engine_display, render_task)
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

        render_samples = int(self.render_samples_entry.get_text())

        resolution_x = int(self.resolution_x_entry.get_text())

        resolution_y = int(self.resolution_y_entry.get_text())

        resolution_percentage = int(self.resolution_percentage_entry.get_text())

        output_type_iter = self.output_type_combo_box.get_active_iter()
        output_type_model = self.output_type_combo_box.get_model()
        output_type = output_type_model[output_type_iter][0]

        start_frame = int(self.start_frame_entry.get_text())

        end_frame = int(self.end_frame_entry.get_text())

        output_format_iter = self.output_format_combo_box.get_active_iter()
        output_format_model = self.output_format_combo_box.get_model()
        output_format = output_format_model[output_format_iter][1]

        output_file = os.path.join(self.output_path_chooser_button.get_filename(), self.output_name_entry.get_text())

        python_expressions = self.python_expressions_entry.get_text()

        return RenderTask(
            blend_file, render_engine, render_device, render_samples,
            resolution_x, resolution_y, resolution_percentage, output_type,
            start_frame, end_frame, output_format, output_file,
            python_expressions, False
        ), render_engine_display

    def add_render_task_to_tree_view(self, render_engine_display: str, render_task: RenderTask) -> None:
        def frames_argument() -> str:
            output_type = render_task.output_type
            if output_type == "Animation":
                return f"{output_type} ({render_task.start_frame}-{render_task.end_frame})"
            elif output_type == "Single Frame":
                return f"{output_type} ({render_task.start_frame})"

        self.render_tasks_model.append([
            os.path.basename(render_task.blend_file),
            render_engine_display,
            frames_argument(),
            render_task.output_file,
            0
        ])
        self.render_queue.append(render_task)

    async def render(self, render_task: RenderTask) -> None:
        cmd_line = [
                       "blender",
                       "-b", render_task.blend_file,
                       "-E", render_task.render_engine,
                       "-o", render_task.output_file,
                   ] + convert_output_format(render_task.output_format) \
                   + convert_animation(render_task.output_type, render_task.start_frame, render_task.end_frame) \
                   + [
                       "--python-expr",
                       "import bpy; "
                       + convert_render_device(render_task.render_device)
                       + convert_render_samples(render_task.render_samples, render_task.render_engine)
                       + convert_resolution_x(render_task.resolution_x)
                       + convert_resolution_y(render_task.resolution_y)
                       + convert_resolution_percentage(render_task.resolution_percentage)
                       + f"{render_task.python_expressions}"
                   ] \
                   + convert_single_frame(render_task.output_type, render_task.start_frame)
        async with await trio.open_process(
            cmd_line,
            stdout=subprocess.PIPE
        ) as process:
            self.process = process
            self.info_bar.set_revealed(True)
            async for raw_line in process.stdout:
                line = raw_line.strip().decode("utf-8")
                parts = line.split("\n")
 
                if render_task.output_type == "Animation":
                    end_frame = self.current_render_task.end_frame
                else:
                    end_frame = self.current_render_task.start_frame
                info, progress = self.parse_blender_logs(parts[-1], end_frame)

                if info is not None:
                    self.info_bar_label.set_text(str(info))
                if progress is not None:
                    self.update_progress(progress)

        await self.post_rendering()

    def update_progress(self, progress: float) -> None:
        self.render_tasks_model[self.render_queue.index(self.current_render_task)][4] = progress

    def parse_blender_logs(self, line: str, end_frame: int) -> Tuple[Optional[RenderInfo], Optional[int]]:
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

        if status is not None and status.startswith("Rendered "):
            progress = self.parse_status(status, frame, end_frame)

        render_info = RenderInfo(frame, time, remaining, mem, layer, status)
        return render_info, progress

    def parse_status(self, status: str, frame: str, end_frame: int) -> float:
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

        frame = int(re.search("^ Fra: (?P<frame> [0-9]+)", frame, flags=re.VERBOSE).group("frame"))

        if samples == total_samples:
            samples = 0

        f_tiles = tiles + samples / total_samples
        f_frames = frame - 1 + f_tiles / total_tiles
        return (f_frames / end_frame) * 100

    async def post_rendering(self) -> None:
        print("Rendering complete!")
        Notify.init("Overnight Renderer")
        notification = Notify.Notification.new(
            f"Rendering {os.path.basename(self.current_render_task.blend_file)} finished"
        )
        notification.show()

        self.process = None
        self.current_render_task.finished = True

        for render_task in self.render_queue:
            if not render_task.finished:
                self.current_render_task = render_task
                self.nursery.start_soon(self.render, self.current_render_task)
                return

        self.render_button.set_sensitive(True)
        self.info_bar.set_revealed(False)

        post_rendering_iter = self.post_rendering_combo_box.get_active_iter()
        post_rendering_model = self.post_rendering_combo_box.get_model()
        post_rendering = post_rendering_model[post_rendering_iter][0]

        if post_rendering == "Suspend":
            await trio.sleep(30)
            print("Suspending...")
            subprocess.run(["systemctl", "suspend"])
        elif post_rendering == "Shutdown":
            await trio.sleep(30)
            print("Shutting down...")
            subprocess.run(["poweroff"])

    def on_tree_view_key_pressed(self, tree_view: Gtk.TreeView, event: Gdk.EventKey) -> None:
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == "Delete":
            del self.render_queue[tree_view.get_selection().get_selected_rows()[1][0][0]]
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
