from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined


class TemplateRenderer:
    def __init__(self) -> None:
        template_dir = Path(__file__).resolve().parents[2] / "templates" / "systemverilog"
        self.environment = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            undefined=StrictUndefined,
        )

    def render(self, template_name: str, **context: Any) -> str:
        return self.environment.get_template(template_name).render(**context)
