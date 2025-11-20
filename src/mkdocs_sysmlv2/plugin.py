"""MkDocs plugin entry point that renders SysML v2 diagrams inline."""

from __future__ import annotations

import logging
import re
from typing import Dict, Tuple

from mkdocs.config import base, config_options
from mkdocs.plugins import BasePlugin

from .parser import SysMLParser
from .renderer import SysMLRenderer

log = logging.getLogger(f"mkdocs.plugins.{__name__}")

BLOCK_PATTERN = re.compile(r"```(?P<header>[^\n]*)\n(?P<body>.*?)```", re.DOTALL)
ATTR_PATTERN = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


class SysMLv2PluginConfig(base.Config):
    code_fences = config_options.Type(str, default="sysml,sysmlv2")
    output_format = config_options.Choice(["svg", "html"], default="html")
    strict = config_options.Type(bool, default=False)
    title_source = config_options.Choice(["page", "file", "none"], default="page")


class SysMLv2Plugin(BasePlugin[SysMLv2PluginConfig]):
    """Intercepts fenced code blocks and replaces them with rendered diagrams."""

    def __init__(self) -> None:
        self.parser = SysMLParser()
        self.renderer = SysMLRenderer()
        self._languages = {"sysml", "sysmlv2"}

    def on_config(self, config):
        fences = {
            name.strip().lower()
            for name in self.config["code_fences"].split(",")
            if name.strip()
        }
        self._languages = fences or {"sysml"}
        return config

    def on_page_markdown(self, markdown, page, config, files):
        def replace(match):
            lang, attr_text = self._parse_header(match.group("header"))
            if lang not in self._languages:
                return match.group(0)

            attrs = self._parse_attrs(attr_text)
            title = attrs.get("title") or self._default_title(page)
            caret = page and page.file and page.file.src_path or "<inline>"

            try:
                model = self.parser.parse(match.group("body"), source_path=caret)
                html = self.renderer.render(
                    model,
                    fmt=self.config["output_format"],
                    title=title,
                    inline=True,
                )
                return f"\n\n{html}\n\n"
            except Exception as exc:  # pragma: no cover - guard rail
                log.error(
                    "SysMLv2 plugin: failed to render block in %s (%s)", caret, exc
                )
                if self.config["strict"]:
                    raise
                return (
                    f"<pre class=\"sysmlv2-error\">SysML rendering failed: {exc}</pre>"
                )

        return BLOCK_PATTERN.sub(replace, markdown)

    def _parse_header(self, header: str) -> Tuple[str, str]:
        header = (header or "").strip()
        if not header:
            return "", ""
        parts = header.split(None, 1)
        lang = parts[0].lower()
        attrs = parts[1] if len(parts) > 1 else ""
        return lang, attrs

    def _parse_attrs(self, attr_text: str) -> Dict[str, str]:
        return {key.lower(): value for key, value in ATTR_PATTERN.findall(attr_text)}

    def _default_title(self, page) -> str:
        source = self.config["title_source"]
        if source == "page" and page and page.title:
            return page.title
        if page and page.file and page.file.src_path:
            if source == "file":
                return page.file.src_path
            if source == "page":
                return page.file.src_path
        return "SysML diagram"
