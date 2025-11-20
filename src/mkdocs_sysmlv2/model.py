"""Core data structures for SysML v2 parsing and rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SysMLPackage:
    """Represents a SysML package declaration."""

    name: str
    description: Optional[str] = None


@dataclass
class SysMLRelation:
    """Represents a relation between two SysML elements."""

    source: str
    target: str
    relation: str
    label: Optional[str] = None


@dataclass
class SysMLElement:
    """Represents a SysML element definition or usage."""

    name: str
    kind: str
    flavor: Optional[str] = None
    package: Optional[str] = None
    type_of: List[str] = field(default_factory=list)
    specializes: List[str] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    external: bool = False


class SysMLModel:
    """Container for nodes, packages and relations."""

    def __init__(self, source_path: Optional[str] = None):
        self.source_path = source_path
        self.nodes: List[SysMLElement] = []
        self.relations: List[SysMLRelation] = []
        self.packages: List[SysMLPackage] = []
        self._node_index: Dict[str, SysMLElement] = {}
        self._package_index: Dict[str, SysMLPackage] = {}

    def add_package(self, name: str) -> SysMLPackage:
        if name in self._package_index:
            return self._package_index[name]

        package = SysMLPackage(name=name)
        self.packages.append(package)
        self._package_index[name] = package
        return package

    def add_node(self, node: SysMLElement) -> SysMLElement:
        if node.name in self._node_index:
            existing = self._node_index[node.name]
            # Preserve whichever information is richer.
            if not existing.package and node.package:
                existing.package = node.package
            if node.specializes:
                existing.specializes = list(
                    dict.fromkeys(existing.specializes + node.specializes)
                )
            if node.type_of:
                existing.type_of = list(
                    dict.fromkeys(existing.type_of + node.type_of)
                )
            if node.modifiers:
                existing.modifiers = list(
                    dict.fromkeys(existing.modifiers + node.modifiers)
                )
            existing.external = existing.external and node.external
            return existing

        self.nodes.append(node)
        self._node_index[node.name] = node
        return node

    def add_relation(self, relation: SysMLRelation) -> None:
        self.relations.append(relation)

    def ensure_relation_nodes(self) -> None:
        for relation in self.relations:
            for endpoint in (relation.source, relation.target):
                if endpoint not in self._node_index:
                    self.add_node(
                        SysMLElement(
                            name=endpoint, kind="external", external=True
                        )
                    )

