import toml
import subprocess

from typing import Any, Dict

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
            "load_render_settings": True
        }

        return Config(settings)

    def create_from_file(path: str) -> "Config":
        file = open(path, "r")
        data = file.read()
        settings = toml.loads(data)
        return Config(settings)

