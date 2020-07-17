class RenderTask():
    def __init__(
        self, blend_file: str, render_engine: str, render_device: str,
        render_samples: int, resolution_x: int, resolution_y: int,
        resolution_percentage: int, output_type: str, start_frame: int,
        end_frame: int, output_format: str, output_file: str,
        python_expressions: str, finished: bool
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
        self.finished = finished
