"""MkDocs plugin entry point that renders SysML v2 diagrams."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from mkdocs.config import base, config_options
from mkdocs.plugins import BasePlugin

from .parser import SysMLParser
from .renderer import SysMLRenderer

log = logging.getLogger(f"mkdocs.plugins.{__name__}")


@dataclass
class DiagramRoot:
    root_dir: Path
    src_dir: Path


@dataclass
class ModelArtifact:
    source_path: Path
    output_path: Path

    def needs_render(self, force: bool) -> bool:
        if force:
            return True
        if not self.output_path.exists():
            return True

        try:
            source_time = self.source_path.stat().st_mtime
            out_time = self.output_path.stat().st_mtime
            return source_time > out_time
        except OSError:
            return True


class SysMLv2PluginConfig(base.Config):
    allow_multiple_roots = config_options.Type(bool, default=False)
    diagram_root = config_options.Type(str, default="docs/diagrams")
    input_folder = config_options.Type(str, default="src")
    output_folder = config_options.Type(str, default="out")
    output_in_dir = config_options.Type(bool, default=False)
    input_extensions = config_options.Type(str, default=".sysml,.sysmlv2")
    output_format = config_options.Choice(["svg", "html"], default="svg")
    always_render = config_options.Type(bool, default=False)
    title_mode = config_options.Choice(
        ["filename", "package", "filename+package"], default="filename"
    )


class SysMLv2Plugin(BasePlugin[SysMLv2PluginConfig]):
    def __init__(self) -> None:
        self.parser = SysMLParser()
        self.renderer = SysMLRenderer()

    def on_pre_build(self, config):
        created = 0
        skipped = 0
        diagram_roots = self._discover_roots()

        for root in diagram_roots:
            if not root.src_dir.exists():
                log.warning(
                    "SysMLv2 plugin: source directory '%s' does not exist", root.src_dir
                )
                continue

            for artifact in self._iter_artifacts(root):
                force = self.config["always_render"]
                if not artifact.needs_render(force):
                    skipped += 1
                    continue

                try:
                    text = artifact.source_path.read_text(encoding="utf-8")
                except OSError as exc:
                    log.error(
                        "SysMLv2 plugin: failed to read %s (%s)",
                        artifact.source_path,
                        exc,
                    )
                    continue

                model = self.parser.parse(text, source_path=str(artifact.source_path))
                title = self._resolve_title(artifact, model)

                try:
                    rendered = self.renderer.render(
                        model, fmt=self.config["output_format"], title=title
                    )
                except Exception as exc:  # pragma: no cover - guard rail
                    log.error(
                        "SysMLv2 plugin: rendering failed for %s (%s)",
                        artifact.source_path,
                        exc,
                    )
                    continue

                artifact.output_path.parent.mkdir(parents=True, exist_ok=True)
                artifact.output_path.write_text(rendered, encoding="utf-8")
                created += 1
                log.debug(
                    "SysMLv2 plugin: rendered %s -> %s",
                    artifact.source_path,
                    artifact.output_path,
                )

        log.info(
            "SysMLv2 plugin: %s rendered, %s skipped",
            created,
            skipped,
        )
        return config

    def _discover_roots(self) -> List[DiagramRoot]:
        if self.config["allow_multiple_roots"]:
            roots: List[DiagramRoot] = []
            cwd = Path.cwd()
            for dirpath, dirnames, _ in os.walk(cwd):
                for dirname in dirnames:
                    candidate = Path(dirpath) / dirname
                    if str(candidate).endswith(self.config["diagram_root"]):
                        roots.append(self._make_root(candidate))
            return roots
        return [self._make_root(Path.cwd() / self.config["diagram_root"])]

    def _make_root(self, base_path: Path) -> DiagramRoot:
        return DiagramRoot(
            root_dir=base_path,
            src_dir=base_path / self.config["input_folder"],
        )

    def _iter_artifacts(self, root: DiagramRoot) -> Iterable[ModelArtifact]:
        for dirpath, _, files in os.walk(root.src_dir):
            for filename in files:
                if not self._file_matches(filename):
                    continue
                source_path = Path(dirpath) / filename
                output_dir = self._get_output_directory(root, Path(dirpath))
                extension = self.config["output_format"]
                output_path = output_dir / f"{source_path.stem}.{extension}"
                yield ModelArtifact(source_path=source_path, output_path=output_path)

    def _file_matches(self, filename: str) -> bool:
        extensions = [
            ext.strip().lower()
            for ext in self.config["input_extensions"].split(",")
            if ext.strip()
        ]
        if not extensions:
            return True
        file_ext = Path(filename).suffix.lower()
        return file_ext in extensions

    def _get_output_directory(self, root: DiagramRoot, subdir: Path) -> Path:
        try:
            relative = subdir.relative_to(root.src_dir)
        except ValueError:
            relative = Path()

        if self.config["output_in_dir"]:
            return root.root_dir / relative / self.config["output_folder"]
        return root.root_dir / self.config["output_folder"] / relative

    def _resolve_title(self, artifact: ModelArtifact, model) -> str:
        mode = self.config["title_mode"]
        filename_title = artifact.source_path.stem
        package_title = model.packages[0].name if model.packages else ""

        if mode == "package" and package_title:
            return package_title
        if mode == "filename+package" and package_title:
            return f"{filename_title} · {package_title}"
        return filename_title

