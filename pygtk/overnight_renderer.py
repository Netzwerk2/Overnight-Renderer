import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Notify", "0.7")
from gi.repository import Gtk, Notify, GLib

import os
import time
import threading

from widgets import create_label, create_entry, create_button, \
    create_file_chooser_dialog, create_combo_box, create_check_button, \
    create_tree_view

from render_task import RenderTask

class MainWindow(Gtk.Window):
    grid = Gtk.Grid(column_spacing=12, row_spacing=12)

    blend_file_entry = None
    render_engine_combo_box = None
    render_device_combo_box = None
    render_samples_entry = None
    output_type_combo_box = None
    start_frame_entry = None
    end_frame_entry = None
    output_format_combo_box = None
    output_file_entry = None
    python_expressions_entry = None
    post_rendering_combo_box = None
    render_button = None
    render_tasks_model = Gtk.ListStore(str, str, str, str, bool)

    current_render_task = None

    def __init__(self):
        super(MainWindow, self).__init__()
        self.set_title("Blender Overnight Renderer")
        self.set_border_width(20)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.create_content()

    def create_content(self) -> None:
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
        render_devices = ["CPU", "GPU"]
        self.render_device_combo_box = create_combo_box(labels=render_devices)

        render_samples_label = create_label("Cycles Samples")
        self.render_samples_entry = create_entry(True)
        self.render_samples_entry.set_text("128")

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

        output_file_label = create_label("Output path")
        self.output_file_entry = create_entry(False)
        output_file_button = create_button("Browse")
        output_file_button.connect("clicked", self.on_output_file_clicked)

        python_expressions_label = create_label("Python expressions")
        self.python_expressions_entry = create_entry(False)

        post_rendering_label = create_label("After rendering is finished")
        post_rendering_options = ["Do nothing", "Suspend", "Shutdown"]
        self.post_rendering_combo_box = create_combo_box(
            labels=post_rendering_options
        )

        self.render_button = create_button("Render")
        self.render_button.connect("clicked", self.on_render_clicked)
        
        columns = [
            "File", "Engine", "Type", "Output", "Finished"
        ]
        render_tasks_tree_view = create_tree_view(
            self.render_tasks_model, columns
        )

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
        self.grid.attach(output_type_label, 0, 4, 1, 1)
        self.grid.attach(self.output_type_combo_box, 1, 4, 1, 1)
        self.grid.attach(start_frame_label, 0, 5, 1, 1)
        self.grid.attach(self.start_frame_entry, 1, 5, 1, 1)
        self.grid.attach(end_frame_label, 0, 6, 1, 1)
        self.grid.attach(self.end_frame_entry, 1, 6, 1, 1)
        self.grid.attach(output_format_label, 0, 7, 1, 1)
        self.grid.attach(self.output_format_combo_box, 1, 7, 1, 1)
        self.grid.attach(output_file_label, 0, 8, 1, 1)
        self.grid.attach(self.output_file_entry, 1, 8, 1, 1)
        self.grid.attach(output_file_button, 2, 8, 1, 1)
        self.grid.attach(python_expressions_label, 0, 9, 1, 1)
        self.grid.attach(self.python_expressions_entry, 1, 9, 1, 1)
        self.grid.attach(post_rendering_label, 0, 10, 1, 1)
        self.grid.attach(self.post_rendering_combo_box, 1, 10, 1, 1)
        self.grid.attach(self.render_button, 0, 11, 3, 1)
        self.grid.attach(render_tasks_tree_view, 0, 12, 3, 1)

    def on_blend_file_clicked(self, button: Gtk.Button) -> None:
        file_chooser_dialog = create_file_chooser_dialog(
            self, Gtk.FileChooserAction.OPEN, Gtk.STOCK_OPEN
        )
        self.add_blend_filters(file_chooser_dialog)

        response = file_chooser_dialog.run()

        if response == Gtk.ResponseType.OK:
            self.blend_file_entry.set_text(file_chooser_dialog.get_filename())
        elif response == Gtk.ResponseType.CANCEL:
            pass

        file_chooser_dialog.destroy()

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
        else:
            pass

        file_chooser_dialog.destroy()

    def add_blend_filters(self, dialog: Gtk.FileChooserDialog) -> None:
        filter_blend = Gtk.FileFilter()
        filter_blend.set_name(".blend files")
        filter_blend.add_pattern("*.blend")
        filter_blend.add_pattern("*.blend1")
        dialog.add_filter(filter_blend)

    def on_render_clicked(self, button: Gtk.Button) -> None:
        blend_file = self.blend_file_entry.get_text()

        render_engine_iter = self.render_engine_combo_box.get_active_iter()
        render_engine_model = self.render_engine_combo_box.get_model()
        render_engine = render_engine_model[render_engine_iter][1]

        render_device_iter = self.render_device_combo_box.get_active_iter()
        render_device_model = self.render_device_combo_box.get_model()
        render_device = render_device_model[render_device_iter][0]

        render_samples = int(self.render_samples_entry.get_text())

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

        post_rendering_iter = self.post_rendering_combo_box.get_active_iter()
        post_rendering_model = self.post_rendering_combo_box.get_model()
        post_rendering = post_rendering_model[post_rendering_iter][0]
    
        self.render_tasks_model.clear()
        if output_type == "Animation":
            self.render_tasks_model.append([
                os.path.basename(blend_file),
                render_engine_model[render_engine_iter][0],
                output_type + " ({}-{})".format(start_frame, end_frame),
                output_file, False
            ])
        elif output_type == "Single Frame":
            self.render_tasks_model.append([
                os.path.basename(blend_file),
                render_engine_model[render_engine_iter][0],
                output_type + " ({})".format(start_frame), output_file, False
            ])

        self.current_render_task = RenderTask(
            blend_file, render_engine, render_device, render_samples,
            output_type, start_frame, end_frame, output_format, output_file,
            python_expressions, post_rendering, False
        )

        self.render_button.set_sensitive(False)
        threading.Thread(target=self.render).start()

    def render(self) -> None:
        os.chdir(os.path.dirname(self.current_render_task.blend_file))
        if self.current_render_task.output_type == "Animation":
            os.system(
                "blender -b {} -E {} -o {} -F {} -s {} -e {} "
                "--python-expr 'import bpy; bpy.context.scene.cycles.device = \"{}\"; "
                "bpy.context.scene.cycles.samples = {}; {}' "
                "-a"
                .format(
                    os.path.basename(self.current_render_task.blend_file),
                    self.current_render_task.render_engine,
                    self.current_render_task.output_file,
                    self.current_render_task.output_format,
                    self.current_render_task.start_frame,
                    self.current_render_task.end_frame,
                    self.current_render_task.render_device,
                    self.current_render_task.render_samples,
                    self.current_render_task.python_expressions
                )
            )
        elif self.current_render_task.output_type == "Single Frame":
            os.system(
                "blender -b {} -E {} -o {} -F {} "
                "--python-expr 'import bpy; bpy.context.scene.cycles.device = \"{}\"; "
                "bpy.context.scene.cycles.samples = {}; {}' "
                "-f {}"
                .format(
                    os.path.basename(self.current_render_task.blend_file),
                    self.current_render_task.render_engine,
                    self.current_render_task.output_file,
                    self.current_render_task.output_format,
                    self.current_render_task.render_device,
                    self.current_render_task.render_samples,
                    self.current_render_task.python_expressions,
                    self.current_render_task.start_frame
                )
            )
        GLib.idle_add(self.post_rendering)

        
    def post_rendering(self) -> None:    
        print("Rendering complete!")
        self.render_tasks_model[0][4] = True
        self.render_button.set_sensitive(True)

        Notify.init("Overnight Renderer")

        if self.current_render_task.post_rendering == "Do nothing":
            notification = Notify.Notification.new(
                "Rendering {} finished"
                .format(os.path.basename(self.current_render_task.blend_file))
            )

            notification.show()
        elif self.current_render_task.post_rendering == "Suspend":
            notification = Notify.Notification.new(
                "Rendering {} finished"
                .format(os.path.basename(self.current_render_task.blend_file)),
                "Suspending in 30 seconds!"
            )

            notification.show()

            time.sleep(30)
            print("Suspending...")
            os.system("systemctl suspend")
        elif self.current_render_task.post_rendering == "Shutdown":
            notification = Notify.Notification.new(
                "Rendering {} finished"
                .format(os.path.basename(self.current_render_task.blend_file)),
                "Shutting down in 30 seconds!"
            )

            notification.show()

            time.sleep(30)
            print("Shutting down...")
            os.system("poweroff")



main_window = MainWindow()
main_window.connect("delete-event", Gtk.main_quit)
main_window.show_all()
Gtk.main()

