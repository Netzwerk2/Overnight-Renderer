import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Notify", "0.7")
from gi.repository import Gtk, Notify, GLib, Gdk

import os
import time
import threading
import subprocess
from typing import Tuple

from widgets import create_label, create_entry, create_button, \
    create_file_chooser_dialog, create_combo_box, create_check_button, \
    create_tree_view

from render_task import RenderTask

from convert_input_to_argument import convert_output_format, convert_animation, \
    convert_render_device, convert_render_samples, convert_resolution_x, convert_resolution_y, \
    convert_resolution_percentage, convert_single_frame

class MainWindow(Gtk.Window):
    grid = Gtk.Grid(column_spacing=12, row_spacing=12)

    blend_file_entry = None
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
    output_file_entry = None
    python_expressions_entry = None
    post_rendering_combo_box = None
    render_button = None
    queue_button = None
    render_tasks_model = Gtk.ListStore(str, str, str, str, bool)

    render_queue = []
    current_render_task = None
    render_thread = None

    def __init__(self) -> None:
        super(MainWindow, self).__init__()
        self.set_title("Blender Overnight Renderer")
        self.set_border_width(20)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.create_content()

    def create_content(self) -> None:
        number_entries_tooltip = "0 = Use from .blend file"

        blend_file_label = create_label("Path to .blend file")
        self.blend_file_entry = create_entry(False)
        blend_file_button = create_button("Browse")
        blend_file_button.connect("clicked", self.on_blend_file_clicked)

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
        self.output_type_combo_box.connect("changed", self.on_output_type_changed)

        start_frame_label = create_label("Start Frame")
        self.start_frame_entry = create_entry(True)
        self.start_frame_entry.set_text("1")

        end_frame_label = create_label("End Frame")
        self.end_frame_entry = create_entry(True)
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

        output_file_label = create_label("Output Path")
        self.output_file_entry = create_entry(False)
        output_file_button = create_button("Browse")
        output_file_button.connect("clicked", self.on_output_file_clicked)

        python_expressions_label = create_label("Python Expressions")
        self.python_expressions_entry = create_entry(False)

        post_rendering_label = create_label("After rendering is finished")
        post_rendering_options = ["Do nothing", "Suspend", "Shutdown"]
        self.post_rendering_combo_box = create_combo_box(
            labels=post_rendering_options
        )

        self.render_button = create_button("Render")
        self.render_button.connect("clicked", self.on_render_clicked)

        self.queue_button = create_button("Queue")
        self.queue_button.connect("clicked", self.on_queue_clicked)

        columns = [
            "File", "Engine", "Type", "Output", "Finished"
        ]
        render_tasks_tree_view = create_tree_view(
            self.render_tasks_model, columns
        )
        render_tasks_tree_view.connect("key-press-event", self.on_tree_view_key_pressed)

        self.add(self.grid)
        self.grid.set_halign(Gtk.Align.CENTER)
        self.grid.set_valign(Gtk.Align.CENTER)
        self.grid.attach(blend_file_label, 0, 0, 1, 1)
        self.grid.attach(self.blend_file_entry, 1, 0, 1, 1)
        self.grid.attach(blend_file_button, 2, 0, 1, 1)
        self.grid.attach(render_engine_label, 0, 1, 1, 1)
        self.grid.attach(self.render_engine_combo_box, 1, 1, 1, 1)
        self.grid.attach(render_device_label, 0, 2, 1, 1)
        self.grid.attach(self.render_device_combo_box, 1, 2, 1, 1)
        self.grid.attach(render_samples_label, 0, 3, 1, 1)
        self.grid.attach(self.render_samples_entry, 1, 3, 1, 1)
        self.grid.attach(resolution_x_label, 0, 4, 1, 1)
        self.grid.attach(self.resolution_x_entry, 1, 4, 1, 1)
        self.grid.attach(resolution_y_label, 0, 5, 1, 1)
        self.grid.attach(self.resolution_y_entry, 1, 5, 1, 1)
        self.grid.attach(resolution_percentage_label, 0, 6, 1, 1)
        self.grid.attach(self.resolution_percentage_entry, 1, 6, 1, 1)
        self.grid.attach(output_type_label, 0, 7, 1, 1)
        self.grid.attach(self.output_type_combo_box, 1, 7, 1, 1)
        self.grid.attach(start_frame_label, 0, 8, 1, 1)
        self.grid.attach(self.start_frame_entry, 1, 8, 1, 1)
        self.grid.attach(end_frame_label, 0, 9, 1, 1)
        self.grid.attach(self.end_frame_entry, 1, 9, 1, 1)
        self.grid.attach(output_format_label, 0, 10, 1, 1)
        self.grid.attach(self.output_format_combo_box, 1, 10, 1, 1)
        self.grid.attach(output_file_label, 0, 11, 1, 1)
        self.grid.attach(self.output_file_entry, 1, 11, 1, 1)
        self.grid.attach(output_file_button, 2, 11, 1, 1)
        self.grid.attach(python_expressions_label, 0, 12, 1, 1)
        self.grid.attach(self.python_expressions_entry, 1, 12, 1, 1)
        self.grid.attach(post_rendering_label, 0, 13, 1, 1)
        self.grid.attach(self.post_rendering_combo_box, 1, 13, 1, 1)
        self.grid.attach(self.render_button, 1, 14, 1, 1)
        self.grid.attach(self.queue_button, 1, 15, 1, 1)
        self.grid.attach(render_tasks_tree_view, 0, 16, 3, 1)

    def on_blend_file_clicked(self, button: Gtk.Button) -> None:
        file_chooser_dialog = create_file_chooser_dialog(
            self, Gtk.FileChooserAction.OPEN, Gtk.STOCK_OPEN
        )
        self.add_blend_filters(file_chooser_dialog)

        response = file_chooser_dialog.run()

        if response == Gtk.ResponseType.OK:
            self.blend_file_entry.set_text(file_chooser_dialog.get_filename())
            render_task = self.set_properties_from_blend_file(
                file_chooser_dialog.get_filename()
            )
        elif response == Gtk.ResponseType.CANCEL:
            pass

        file_chooser_dialog.destroy()

    def set_properties_from_blend_file(self, file_path: str) -> None:
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
            properties = []
            ready = False
            for raw_line in output:
                line = raw_line.strip().decode("utf-8")
                if line == "READY":
                    ready = True
                    continue
                if ready:
                    properties.append(line)

            if properties[0] == "BLENDER_EEVEE":
                self.render_engine_combo_box.set_active(0)
                self.render_samples_entry.set_text(properties[3])
            elif properties[0] == "CYCLES":
                self.render_engine_combo_box.set_active(2)
                self.render_samples_entry.set_text(properties[2])
            if properties[1] == "CPU":
                self.render_device_combo_box.set_active(1)
            elif properties[1] == "GPU":
                self.render_device_combo_box.set_active(2)
            self.resolution_x_entry.set_text(properties[4])
            self.resolution_y_entry.set_text(properties[5])
            self.resolution_percentage_entry.set_text(properties[6])
            self.start_frame_entry.set_text(properties[7])
            self.end_frame_entry.set_text(properties[8])
            self.output_file_entry.set_text(properties[10])

    def on_output_type_changed(self, combo_box: Gtk.ComboBox) -> None:
        output_type_iter = combo_box.get_active_iter()
        output_type_model = combo_box.get_model()
        output_type = output_type_model[output_type_iter][0]

        if output_type == "Animation":
            self.end_frame_entry.set_sensitive(True)
        elif output_type == "Single Frame":
            self.end_frame_entry.set_sensitive(False)

    def on_output_file_clicked(self, button: Gtk.Button) -> None:
        file_chooser_dialog = create_file_chooser_dialog(
            self, Gtk.FileChooserAction.SAVE, Gtk.STOCK_SAVE
        )
        file_chooser_dialog.set_current_name("Render")

        response = file_chooser_dialog.run()

        if response == Gtk.ResponseType.OK:
            self.output_file_entry.set_text(file_chooser_dialog.get_filename())

        file_chooser_dialog.destroy()

    def add_blend_filters(self, dialog: Gtk.FileChooserDialog) -> None:
        filter_blend = Gtk.FileFilter()
        filter_blend.set_name(".blend files")
        filter_blend.add_pattern("*.blend")
        filter_blend.add_pattern("*.blend1")
        dialog.add_filter(filter_blend)

    def on_render_clicked(self, button: Gtk.Button) -> None:
        if len(self.render_queue) == 0:
            render_task, render_engine_display = self.create_render_task()
            if render_task.blend_file == "" or render_task.output_file == "":
                return
            self.add_render_task_to_tree_view(render_engine_display, render_task)
            self.current_render_task = self.render_queue[0]
        else:
            for render_task in self.render_queue:
                if not render_task.finished:
                    self.current_render_task = render_task

        self.render_button.set_sensitive(False)

        render_lambda = lambda: self.render(self.current_render_task)
        self.render_thread = threading.Thread(target=render_lambda)
        self.render_thread.start()

    def on_queue_clicked(self, button: Gtk.Button) -> None:
        render_task, render_engine_display = self.create_render_task()
        if render_task.blend_file == "" or render_task.output_file == "":
            return
        self.add_render_task_to_tree_view(render_engine_display, render_task)

    def create_render_task(self) -> Tuple[RenderTask, str]:
        blend_file = self.blend_file_entry.get_text()

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

        output_file = self.output_file_entry.get_text()

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
                return "{} ({}-{})".format(output_type, render_task.start_frame, render_task.end_frame)
            elif output_type == "Single Frame":
                return "{} ({})".format(output_type, render_task.start_frame)

        self.render_tasks_model.append([
            os.path.basename(render_task.blend_file),
            render_engine_display,
            frames_argument(),
            render_task.output_file,
            False
        ])
        self.render_queue.append(render_task)

    def render(self, render_task: RenderTask) -> None:
        subprocess.run(
            [
                "blender",
                "-b", render_task.blend_file,
                "-E", render_task.render_engine
            ]
            + [
                "-o", render_task.output_file,
            ]
            + convert_output_format(render_task.output_format)
            + convert_animation(render_task.output_type, render_task.start_frame, render_task.end_frame)
            + [
                "--python-expr",
                "import bpy; "
                + convert_render_device(render_task.render_device)
                + convert_render_samples(render_task.render_samples, render_task.render_engine)
                + convert_resolution_x(render_task.resolution_x)
                + convert_resolution_y(render_task.resolution_y)
                + convert_resolution_percentage(render_task.resolution_percentage)
                + f"{render_task.python_expressions}"
            ]
            + convert_single_frame(render_task.output_type, render_task.start_frame)
        )

        GLib.idle_add(self.post_rendering)

    def post_rendering(self) -> None:
        print("Rendering complete!")
        Notify.init("Overnight Renderer")
        notification = Notify.Notification.new(
            "Rendering {} finished"
            .format(os.path.basename(self.current_render_task.blend_file))
        )
        notification.show()

        self.current_render_task.finished = True
        self.render_tasks_model[self.render_queue.index(self.current_render_task)][4] = True
        self.render_thread.join()

        for render_task in self.render_queue:
            if not render_task.finished:
                self.current_render_task = render_task
                render_lambda = lambda: self.render(self.current_render_task)
                self.render_thread = threading.Thread(target=render_lambda)
                self.render_thread.start()
                return

        self.render_button.set_sensitive(True)

        post_rendering_iter = self.post_rendering_combo_box.get_active_iter()
        post_rendering_model = self.post_rendering_combo_box.get_model()
        post_rendering = post_rendering_model[post_rendering_iter][0]

        if post_rendering == "Suspend":
            time.sleep(30)
            print("Suspending...")
            subprocess.run(["systemctl suspend"])
        elif post_rendering == "Shutdown":
            time.sleep(30)
            print("Shutting down...")
            subprocess.run(["poweroff"])

    def on_tree_view_key_pressed(self, tree_view: Gtk.TreeView, event: Gdk.EventKey) -> None:
        keyname = Gdk.keyval_name(event.keyval)
        if keyname == "Delete":
            del self.render_queue[tree_view.get_selection().get_selected_rows()[1][0][0]]
            model, iter = tree_view.get_selection().get_selected()
            model.remove(iter)


main_window = MainWindow()
main_window.connect("delete-event", Gtk.main_quit)
main_window.show_all()
Gtk.main()

