# sysmlv2

MkDocs plugin that mimics the workflow of [mkdocs-build-plantuml](https://github.com/christo-ph/mkdocs_build_plantuml) but targets SysML v2 textual models.  
It watches your SysML sources, renders lightweight SVG diagrams, and drops the files into an `out` directory that you can reference just like any other image in Markdown.

> :rocket: This is **not** a full SysML compiler. The goal is to have a pragmatic renderer that visualises core structures (packages, parts, usages, connections) directly inside MkDocs without needing an external toolchain.

## Features

- Recursive discovery of `docs/diagrams/src/**/*.sysml` (same layout as the PlantUML plugin).
- Incremental rendering (only updates SVG/HTML artifacts when the source is newer).
- Simple SysML parser that recognises packages, parts, items, interfaces, usages, connect/flow statements, and renders them as cards + relationships.
- Configurable output format (`svg` or `html`), output location, and title strategy.
- Works with `mkdocs serve` and `mkdocs build`.

## Installation

```bash
pip install sysmlv2
```

The package is defined as a standard MkDocs plugin, so it can be installed alongside any MkDocs theme (Material, etc.).

## Example project layout

```
docs/
  diagrams/
    src/
      Batmobile.sysml
    out/
      Batmobile.svg
mkdocs.yml
```

Any `.sysml` (or `.sysmlv2`) file you place under `docs/diagrams/src` will get rendered to `docs/diagrams/out` by default. You can organise your models into sub-directories; the plugin mirrors the folder structure inside the `out` directory, just like the PlantUML build plugin.

## Configuration

Add the plugin to `mkdocs.yml`:

```yaml
plugins:
  - search
  - sysmlv2:
      diagram_root: docs/diagrams   # parent folder that contains src/out
      input_folder: src             # folder with *.sysml files
      output_folder: out            # rendered artifacts
      output_format: svg            # svg (default) or html
      input_extensions: ".sysml,.sysmlv2"
      title_mode: filename          # filename, package, filename+package
      allow_multiple_roots: false   # look for multiple diagram_root matches
      output_in_dir: false          # mimic mkdocs-build-plantuml behaviour
      always_render: false          # force rebuild every time
```

All configuration keys line up with the PlantUML build plugin so the upgrade path is predictable.  
If you change the folder layout, ensure that the resulting artifacts still live below `docs_dir` so MkDocs can serve them.

## Writing SysML

Create a `.sysml` file under your `src` directory:

```sysml
package Batmobile {
    part def Vehicle;
    part def Batmobile :> Vehicle {
        part seat [2];
        part engine : BatmobileEngine;
        interface bat2eng : PowerInterface connect battery.powerPort to engine.port;
    }

    part usage fleetVehicle : Batmobile;
}
```

Start MkDocs:

```bash
mkdocs serve
```

The plugin creates an SVG next to the source file, e.g. `docs/diagrams/out/Batmobile.svg`.  
Reference it like a normal image:

```markdown
![Batmobile](diagrams/out/Batmobile.svg)
```

Each render contains:

- Cards for every element the parser recognises (parts, interfaces, use cases, etc.).
- Edges for specialisations (`:>`), typings/usages (`:`), `connect` statements, and `from/to` flow statements.
- Tooltips that show the source path (to keep track of the file that introduced the view).

## Output format

- `svg` (default): writes a standalone SVG file with embedded styles.
- `html`: wraps the SVG into a `<figure>` tag. Useful if you want to embed the output via templating rather than via Markdown image syntax.

## Sample project

This repo ships with a ready-to-run MkDocs site in `example/` that demonstrates the plugin end to end.

```bash
# 1. Install dependencies and register the plugin in editable mode.
pdm install

# 2. Launch MkDocs using the sample config.
pdm run mkdocs serve -f example/mkdocs.yml
```

PDM expands a local virtual environment and exposes the `sysmlv2` plugin to MkDocs. When the dev server starts, open http://127.0.0.1:8000 — the front page references `docs/diagrams/out/batmobile.svg`, which is rendered from `docs/diagrams/src/batmobile.sysml` by the plugin. Edit the `.sysml` file and the diagram will refresh as you save.

## Relationship to mkdocs-build-plantuml

The project mirrors the ergonomics of `mkdocs-build-plantuml-plugin`:

- identical default directories (`docs/diagrams/src` ➜ `docs/diagrams/out`);
- incremental builds;
- ability to discover multiple `diagram_root` folders in monorepos;
- simple MkDocs plug-in entry point (`plugins: - sysmlv2`).

You can therefore drop it into an existing document set that already uses the PlantUML plugin with minimal changes.

## Contributing

Feel free to open issues or PRs with better parsing rules, styling ideas, or integration hooks.  
The parser is intentionally lightweight—if you need a new syntax feature, add a regression test and extend `SysMLParser`.

## License

Apache-2.0 (see `LICENSE`).
