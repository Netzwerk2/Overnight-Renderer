import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from typing import List, Optional, Union  # noqa: E402


def create_label(text: str) -> Gtk.Label:
    label = Gtk.Label(label=text)
    label.set_halign(Gtk.Align.START)
    return label


def create_entry(text: Optional[str] = None) -> Gtk.Entry:
    entry = Gtk.Entry()
    if text is not None:
        entry.set_text(text)
    entry.set_width_chars(42)
    return entry


def create_file_chooser_button(
    self, dialog_title: str, action: Gtk.FileChooserAction,
    button: Gtk.ButtonsType, filter_blend: bool
) -> Gtk.FileChooserButton:
    file_chooser_dialog = create_file_chooser_dialog(
        self, dialog_title, action, button
    )
    if filter_blend:
        add_blend_filters(file_chooser_dialog)
    return Gtk.FileChooserButton(dialog=file_chooser_dialog)


def create_file_chooser_dialog(
    self, title: str, action: Gtk.FileChooserAction, button: Gtk.ButtonsType
) -> Gtk.FileChooserDialog:
    file_chooser_dialog = Gtk.FileChooserDialog(
        title,
        self,
        action,
        (
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            button,
            Gtk.ResponseType.OK
        )
    )
    return file_chooser_dialog


def add_blend_filters(dialog: Gtk.FileChooserDialog) -> None:
    filter_blend = Gtk.FileFilter()
    filter_blend.set_name(".blend files")
    filter_blend.add_pattern("*.blend")
    filter_blend.add_pattern("*.blend1")
    dialog.add_filter(filter_blend)


def create_combo_box(
    store: Optional[Gtk.ListStore] = None, labels: Optional[List[str]] = None
) -> Gtk.ComboBox:
    if store is None:
        store = Gtk.ListStore(str)
    if labels is not None:
        for i in range(len(labels)):
            store.append([labels[i]])
    combo_box = Gtk.ComboBox.new_with_model(store)
    renderer_text = Gtk.CellRendererText()
    combo_box.pack_start(renderer_text, True)
    combo_box.add_attribute(renderer_text, "text", 0)
    combo_box.set_active(0)
    return combo_box


def create_tree_view(
    store: Union[Gtk.ListStore, Gtk.TreeStore], columns: List[str]
) -> Gtk.TreeView:
    tree_view = Gtk.TreeView(model=store)
    for i, column in enumerate(columns):
        renderer_text = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn(column, renderer_text, text=i)
        tree_view.append_column(column_text)
    return tree_view


def create_spin_button(value: int, min: int, max: int) -> Gtk.SpinButton:
    adjustment = Gtk.Adjustment(
        lower=min, upper=max, step_increment=1, page_increment=10
    )
    spin = Gtk.SpinButton()
    spin.set_adjustment(adjustment)
    spin.set_value(value)
    return spin
