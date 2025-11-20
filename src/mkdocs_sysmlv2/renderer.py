"""Rendering utilities to convert SysMLModel objects into SVG/HTML."""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .model import SysMLElement, SysMLModel, SysMLRelation

GLOBAL_PACKAGE = "__global__"


@dataclass
class NodePosition:
    x: float
    y: float


class SysMLRenderer:
    """Render SysML models as lightweight SVG cards."""

    def __init__(self) -> None:
        self.node_width = 220
        self.node_height = 88
        self.margin_x = 36
        self.margin_y = 64
        self.gap_x = 48
        self.gap_y = 32

    def render(
        self, model: SysMLModel, *, fmt: str, title: str, inline: bool = False
    ) -> str:
        if fmt == "svg":
            return self.render_svg(model, title=title, inline=inline)
        if fmt == "html":
            svg = self.render_svg(model, title=title, inline=True)
            return f"<figure class=\"sysmlv2-diagram\">{svg}</figure>"
        raise ValueError(f"Unsupported format '{fmt}'")

    def render_svg(self, model: SysMLModel, *, title: str, inline: bool = False) -> str:
        nodes = [node for node in model.nodes if node.kind != "package"]
        if not nodes:
            return self._render_empty_svg(title or "SysML model", model, inline=inline)

        package_names = self._package_columns(nodes, model)
        placements = self._layout_nodes(nodes, package_names)
        row_counts = self._row_counts(nodes, package_names)
        width = self._canvas_width(len(package_names))
        height = self._canvas_height(max(row_counts.values()) if row_counts else 1)
        edges = self._render_edges(model.relations, placements)
        packages_svg = self._render_package_labels(package_names)
        nodes_svg = self._render_nodes(nodes, placements)

        svg_elements: List[str] = []
        if not inline:
            svg_elements.append('<?xml version="1.0" encoding="UTF-8"?>')
        svg_elements.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" role="img">'
        )
        svg_elements.extend(
            [
                f"<title>{html.escape(title)}</title>",
                self._style_block(),
                '<defs><marker id="sysmlv2-arrow" viewBox="0 0 10 10" refX="10" refY="5" '
                'markerUnits="strokeWidth" markerWidth="10" markerHeight="7" orient="auto">'
                '<path d="M 0 0 L 10 5 L 0 10 z"></path></marker></defs>',
                '<rect class="sysmlv2-canvas" x="0" y="0" '
                f'width="{width}" height="{height}" rx="8" ry="8"></rect>',
                packages_svg,
                edges,
                nodes_svg,
            ]
        )

        if model.source_path:
            svg_elements.append(
                f'<desc>Source: {html.escape(str(model.source_path))}</desc>'
            )

        svg_elements.append("</svg>")
        return "\n".join(svg_elements)

    def _render_empty_svg(
        self, title: str, model: SysMLModel, inline: bool = False
    ) -> str:
        width, height = 480, 200
        desc = (
            html.escape(model.source_path) if model.source_path else "No elements found"
        )
        elements: List[str] = []
        if not inline:
            elements.append('<?xml version="1.0" encoding="UTF-8"?>')
        elements.extend(
            [
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
                f'height="{height}" viewBox="0 0 {width} {height}" role="img">',
                f"<title>{html.escape(title)}</title>",
                self._style_block(),
                '<rect class="sysmlv2-canvas" x="0" y="0" '
                f'width="{width}" height="{height}" rx="8" ry="8"></rect>',
                f'<text class="sysmlv2-empty" x="{width/2}" y="{height/2}">'
                "No SysML elements detected</text>",
                f"<desc>{desc}</desc>",
                "</svg>",
            ]
        )
        return "\n".join(elements)

    def _package_columns(self, nodes: List[SysMLElement], model: SysMLModel) -> List[str]:
        declared = [pkg.name for pkg in model.packages]
        package_names: List[str] = []

        def normalize(value: Optional[str]) -> str:
            return value if value else GLOBAL_PACKAGE

        for pkg in declared:
            if any(normalize(node.package) == pkg for node in nodes):
                package_names.append(pkg)

        for node in nodes:
            normalized = normalize(node.package)
            if normalized not in package_names:
                package_names.append(normalized)

        if not package_names:
            package_names = [GLOBAL_PACKAGE]
        return package_names

    def _layout_nodes(
        self, nodes: List[SysMLElement], package_names: List[str]
    ) -> Dict[str, NodePosition]:
        placements: Dict[str, NodePosition] = {}
        columns: Dict[str, List[SysMLElement]] = {
            pkg: [] for pkg in package_names
        }

        def normalize(value: Optional[str]) -> str:
            return value if value else GLOBAL_PACKAGE

        for node in nodes:
            pkg = normalize(node.package)
            if pkg not in columns:
                columns[pkg] = []
            columns[pkg].append(node)

        for column_index, pkg in enumerate(package_names):
            y = self.margin_y
            for node in columns.get(pkg, []):
                placements[node.name] = NodePosition(
                    x=self.margin_x + column_index * (self.node_width + self.gap_x),
                    y=y,
                )
                y += self.node_height + self.gap_y

        return placements

    def _row_counts(
        self, nodes: List[SysMLElement], package_names: List[str]
    ) -> Dict[str, int]:
        counts: Dict[str, int] = {pkg: 0 for pkg in package_names}
        for node in nodes:
            pkg = node.package or GLOBAL_PACKAGE
            counts[pkg] = counts.get(pkg, 0) + 1
        return counts

    def _canvas_width(self, columns: int) -> float:
        if columns <= 0:
            columns = 1
        return (
            self.margin_x * 2
            + columns * self.node_width
            + (columns - 1) * self.gap_x
        )

    def _canvas_height(self, rows: int) -> float:
        if rows <= 0:
            rows = 1
        return (
            self.margin_y * 2
            + rows * self.node_height
            + (rows - 1) * self.gap_y
        )

    def _render_nodes(
        self, nodes: List[SysMLElement], placements: Dict[str, NodePosition]
    ) -> str:
        parts: List[str] = []
        for node in nodes:
            if node.name not in placements:
                continue
            position = placements[node.name]
            classes = ["sysmlv2-node"]
            if node.external:
                classes.append("sysmlv2-node--external")
            class_attr = " ".join(classes)

            headline = html.escape(node.name)
            meta_bits: List[str] = [node.kind]
            if node.flavor:
                meta_bits.append(node.flavor)
            if node.modifiers:
                meta_bits.extend(node.modifiers)
            meta_text = " · ".join(meta_bits)

            details: List[str] = []
            if node.specializes:
                details.append("⇢ " + ", ".join(node.specializes))
            if node.type_of:
                details.append("↦ " + ", ".join(node.type_of))

            detail_spans = "".join(
                f'<tspan x="{position.x + 16}" dy="1.2em">{html.escape(detail)}</tspan>'
                for detail in details
            )

            parts.append(
                f'<g class="{class_attr}" transform="translate({position.x},{position.y})">'
                f'<rect width="{self.node_width}" height="{self.node_height}" rx="8" ry="8"></rect>'
                f'<text class="sysmlv2-node__title" x="16" y="28">{headline}</text>'
                f'<text class="sysmlv2-node__meta" x="16" y="48">{html.escape(meta_text)}</text>'
                f'<text class="sysmlv2-node__detail" x="16" y="64">{detail_spans or ""}</text>'
                "</g>"
            )
        return "".join(parts)

    def _render_edges(
        self, relations: Iterable[SysMLRelation], placements: Dict[str, NodePosition]
    ) -> str:
        paths: List[str] = []
        for relation in relations:
            if relation.source not in placements or relation.target not in placements:
                continue
            src = placements[relation.source]
            dst = placements[relation.target]
            x1 = src.x + self.node_width / 2
            y1 = src.y + self.node_height / 2
            x2 = dst.x + self.node_width / 2
            y2 = dst.y + self.node_height / 2
            label = relation.label or relation.relation
            mx = (x1 + x2) / 2
            my = (y1 + y2) / 2

            paths.append(
                f'<path class="sysmlv2-edge" d="M {x1} {y1} L {x2} {y2}" '
                'marker-end="url(#sysmlv2-arrow)"></path>'
                f'<text class="sysmlv2-edge-label" x="{mx}" y="{my}">{html.escape(label)}</text>'
            )
        return "".join(paths)

    def _render_package_labels(self, package_names: List[str]) -> str:
        parts: List[str] = []
        for column_index, pkg in enumerate(package_names):
            label = "Global" if pkg == GLOBAL_PACKAGE else pkg
            x = (
                self.margin_x
                + column_index * (self.node_width + self.gap_x)
                + self.node_width / 2
            )
            y = self.margin_y / 2
            parts.append(
                f'<text class="sysmlv2-package" x="{x}" y="{y}">{html.escape(label)}</text>'
            )
        return "".join(parts)

    def _style_block(self) -> str:
        return """
<style>
.sysmlv2-canvas {
  fill: #0f111a;
  stroke: #1f2334;
  stroke-width: 1;
}
.sysmlv2-package {
  font: 700 14px "SFMono-Regular", Consolas, monospace;
  fill: #cdd9ff;
  text-anchor: middle;
}
.sysmlv2-node rect {
  fill: #1f2334;
  stroke: #5c6bc0;
  stroke-width: 1.4;
}
.sysmlv2-node--external rect {
  stroke-dasharray: 6 4;
  stroke: #999fbf;
}
.sysmlv2-node__title {
  font: 600 16px "Inter", "Segoe UI", sans-serif;
  fill: #f4f6ff;
}
.sysmlv2-node__meta, .sysmlv2-node__detail tspan, .sysmlv2-node__detail {
  font: 500 12px "Inter", "Segoe UI", sans-serif;
  fill: #aeb8d9;
}
.sysmlv2-edge {
  stroke: #7f91ff;
  stroke-width: 1.5;
  fill: none;
}
.sysmlv2-edge-label {
  font: 600 12px "Inter", sans-serif;
  fill: #9fb0ff;
  text-anchor: middle;
}
.sysmlv2-empty {
  font: 600 16px "Inter", sans-serif;
  fill: #aeb8d9;
  text-anchor: middle;
}
</style>
        """.strip()
