"""SysML v2 text parser producing a lightweight semantic model."""

from __future__ import annotations

import html
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .model import SysMLElement, SysMLModel, SysMLRelation

CONNECT_RE = re.compile(
    r"connect\s+(?P<src>[^\s]+)\s+(?:to|with)\s+(?P<dst>[^\s;]+)", re.IGNORECASE
)
FLOW_RE = re.compile(
    r"from\s+(?P<src>[^\s]+)\s+to\s+(?P<dst>[^\s;]+)", re.IGNORECASE
)
ROLE_RE = re.compile(
    r"(?:subject|actor|item|port)\s+(?P<name>[\w\.]+)\s*:\s*(?P<target>[^\s;]+)",
    re.IGNORECASE,
)


@dataclass
class PackageContext:
    name: str
    brace_balance: int = 0


class SysMLParser:
    """Parses a subset of the SysML v2 textual syntax."""

    def parse(self, text: str, *, source_path: Optional[str] = None) -> SysMLModel:
        cleaned = self._strip_block_comments(text)
        model = SysMLModel(source_path=source_path)
        package_stack: List[PackageContext] = []

        for raw_line in cleaned.splitlines():
            line = raw_line.strip()
            if not line:
                self._update_stack(package_stack, raw_line)
                continue

            if line.startswith("//"):
                self._update_stack(package_stack, raw_line)
                continue

            # remove inline comment
            if "//" in line:
                line = line.split("//", 1)[0].strip()
                if not line:
                    self._update_stack(package_stack, raw_line)
                    continue

            package_match = re.match(r"^package\s+([^ {]+)", line, re.IGNORECASE)
            if package_match:
                package_name = self._clean_identifier(package_match.group(1))
                package_stack.append(PackageContext(name=package_name))
                model.add_package(package_name)
                self._update_stack(package_stack, raw_line)
                continue

            current_package = package_stack[-1].name if package_stack else None
            tokens = self._tokenize(line)
            parsed = False

            if tokens:
                parsed = self._parse_definition(tokens, current_package, model)

            if not parsed:
                self._extract_relations(line, model)

            self._update_stack(package_stack, raw_line)

        model.ensure_relation_nodes()
        return model

    def _strip_block_comments(self, text: str) -> str:
        return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    def _tokenize(self, line: str) -> List[str]:
        try:
            return shlex.split(line, posix=True)
        except ValueError:
            return []

    def _parse_definition(
        self, tokens: List[str], package: Optional[str], model: SysMLModel
    ) -> bool:
        if not tokens:
            return False

        modifiers: List[str] = []
        kind_token = tokens.pop(0).lower()

        if kind_token == "use" and tokens and tokens[0].lower() == "case":
            tokens.pop(0)
            kind_token = "use case"
        elif kind_token == "value" and tokens and tokens[0].lower() == "type":
            tokens.pop(0)
            kind_token = "value type"
        elif kind_token == "individual" and tokens:
            modifiers.append("individual")
            kind_token = tokens.pop(0).lower()

        if kind_token == "package":
            return False

        flavor = None
        if tokens and tokens[0].lower() in {"def", "usage"}:
            flavor = tokens.pop(0).lower()

        if not tokens:
            return False

        name = self._clean_identifier(tokens.pop(0))
        if not name:
            return False

        type_of: List[str] = []
        specializes: List[str] = []

        iterator = list(tokens)
        idx = 0
        while idx < len(iterator):
            token = iterator[idx]
            lower = token.lower()
            if lower in {":", ":>", ":>>"}:
                values = self._collect_identifiers(iterator[idx + 1 :])
                if lower == ":":
                    type_of.extend(values)
                else:
                    specializes.extend(values)
                break
            idx += 1

        node = SysMLElement(
            name=name,
            kind=kind_token,
            flavor=flavor,
            package=package,
            type_of=self._unique(type_of),
            specializes=self._unique(specializes),
            modifiers=modifiers,
        )
        model.add_node(node)

        for parent in node.specializes:
            model.add_relation(
                SysMLRelation(
                    source=node.name, target=parent, relation="specializes", label="specializes"
                )
            )

        for target in node.type_of:
            model.add_relation(
                SysMLRelation(
                    source=node.name,
                    target=target,
                    relation="typed",
                    label="typed by" if node.flavor == "def" else "uses",
                )
            )
        return True

    def _collect_identifiers(self, tokens: List[str]) -> List[str]:
        results: List[str] = []
        for token in tokens:
            cleaned = self._clean_identifier(token)
            if not cleaned:
                continue
            if cleaned in {"{", "}", "connect", "from", "to", "and"}:
                break
            results.append(cleaned)
        return results

    def _clean_identifier(self, token: str) -> str:
        cleaned = token.strip(" ,;{}")
        return html.unescape(cleaned).strip("'\"")

    def _extract_relations(self, line: str, model: SysMLModel) -> None:
        for match in CONNECT_RE.finditer(line):
            src = self._clean_identifier(match.group("src"))
            dst = self._clean_identifier(match.group("dst"))
            if src and dst:
                model.add_relation(
                    SysMLRelation(
                        source=src,
                        target=dst,
                        relation="connects",
                        label="connects",
                    )
                )

        for match in FLOW_RE.finditer(line):
            src = self._clean_identifier(match.group("src"))
            dst = self._clean_identifier(match.group("dst"))
            if src and dst:
                model.add_relation(
                    SysMLRelation(
                        source=src, target=dst, relation="flows", label="flows"
                    )
                )

        for match in ROLE_RE.finditer(line):
            src = self._clean_identifier(match.group("name"))
            dst = self._clean_identifier(match.group("target"))
            if src and dst:
                model.add_relation(
                    SysMLRelation(
                        source=src, target=dst, relation="typed", label="role"
                    )
                )

    def _update_stack(self, stack: List[PackageContext], line: str) -> None:
        if not stack:
            return

        delta = line.count("{") - line.count("}")
        stack[-1].brace_balance += delta

        # Propagate closing braces to outer packages if needed.
        while stack and stack[-1].brace_balance <= 0:
            leftover = stack[-1].brace_balance
            stack.pop()
            if leftover < 0 and stack:
                stack[-1].brace_balance += leftover

    def _unique(self, values: List[str]) -> List[str]:
        return list(dict.fromkeys([val for val in values if val]))
