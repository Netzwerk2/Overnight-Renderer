from typing import List


def convert_output_format(output_format: str) -> List[str]:
    if output_format != ".blend file":
        return ["-F", output_format]
    return []


def convert_animation(
    output_type: str, start_frame: int, end_frame: int
) -> List[str]:
    if output_type == "Animation":
        return ["-s", str(start_frame), "-e", str(end_frame)]
    return []


def convert_single_frame(output_type: str, start_frame: int) -> List[str]:
    if output_type == "Single Frame":
        return ["-f", str(start_frame)]
    return ["-a"]


def convert_render_device(render_device: str) -> str:
    return f"bpy.context.scene.cycles.device = '{render_device}'; "


def convert_render_samples(render_samples: int, render_engine: str) -> str:
    if render_engine == "CYCLES":
        return f"bpy.context.scene.cycles.samples = {render_samples}; "
    elif render_engine == "BLENDER_EEVEE":
        return f"bpy.context.scene.eevee.taa_render_samples " \
                f"= {render_samples}; "


def convert_resolution_x(resolution_x: int) -> str:
    return f"bpy.context.scene.render.resolution_x = {resolution_x}; "


def convert_resolution_y(resolution_y: int) -> str:
    return f"bpy.context.scene.render.resolution_y = {resolution_y}; "


def convert_resolution_percentage(resolution_percentage: int) -> str:
    return f"bpy.context.scene.render.resolution_percentage" \
           f" = {resolution_percentage}; "
