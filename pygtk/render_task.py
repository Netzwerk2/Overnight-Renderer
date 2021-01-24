from typing import List

from convert_input_to_argument import convert_output_format, \
    convert_animation, convert_render_device, convert_render_samples, \
    convert_resolution_x, convert_resolution_y, \
    convert_resolution_percentage, convert_single_frame


class RenderTask:
    def __init__(
        self, blend_file: str, render_engine: str, render_device: str,
        render_samples: int, resolution_x: int, resolution_y: int,
        resolution_percentage: int, output_type: str, start_frame: int,
        end_frame: int, output_format: str, output_file: str,
        python_expressions: str, layers: List[str], finished: bool
    ) -> None:
        self.blend_file = blend_file
        self.render_engine = render_engine
        self.render_device = render_device
        self.render_samples = render_samples
        self.resolution_x = resolution_x
        self.resolution_y = resolution_y
        self.resolution_percentage = resolution_percentage
        self.output_type = output_type
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.output_format = output_format
        self.output_file = output_file
        self.python_expressions = python_expressions
        self.layers = layers
        self.finished = finished

    def to_cmd_line(self) -> List[str]:
        return [
            "blender",
            "-b", self.blend_file,
            "-E", self.render_engine,
            "-o", self.output_file,
        ] + convert_output_format(self.output_format) \
            + convert_animation(
                self.output_type,
                self.start_frame,
                self.end_frame
           ) \
            + [
                "--python-expr",
                "import bpy; "
                + convert_render_device(self.render_device)
                + convert_render_samples(
                    self.render_samples,
                    self.render_engine
                )
                + convert_resolution_x(self.resolution_x)
                + convert_resolution_y(self.resolution_y)
                + convert_resolution_percentage(self.resolution_percentage)
                + f"{self.python_expressions}"
            ] \
            + convert_single_frame(
                self.output_type,
                self.start_frame
            )
