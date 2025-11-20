# mkdocs-sysml2

MkDocs plugin for rendering SysML v2 textual models.  
It watches your SysML sources, renders lightweight diagrams directly inside your pages, and keeps your documentation and architecture views in sync.

> :rocket: This is **not** a full SysML compiler. The goal is to have a pragmatic renderer that visualises core structures (packages, parts, usages, connections) directly inside MkDocs without needing an external toolchain.

## Features

- Inline rendering of ```sysml``` or ```sysmlv2``` code blocks (no additional image pipeline).
- Simple SysML parser that recognises packages, parts, items, interfaces, usages, connect/flow statements, and renders them as cards + relationships.
- Configurable output format (`svg` or `html`) and title strategy.
- Works with `mkdocs serve` and `mkdocs build`.

## Quick start

1. Install the plugin (or add it to your dependency manager):

   ```bash
   pip install mkdocs-sysml2
   ```

2. Enable it inside `mkdocs.yml` (see the next section).
3. Add a fenced block with ```sysml``` or ```sysmlv2``` to any Markdown page.
4. Run `mkdocs serve` and view the rendered diagram inline.

The package works with any MkDocs theme and requires no external assets.

## Configuration

Add the plugin to `mkdocs.yml`:

```yaml
plugins:
  - search
  - sysml2:
      code_fences: "sysml,sysmlv2"  # languages to intercept
      output_format: html           # inline html (default) or raw svg
      title_source: page            # use page title, file name, or none
      strict: false                 # raise exceptions when rendering fails
```

The plugin intercepts fenced code blocks in Markdown and replaces them with rendered diagrams, so you only need to maintain the SysML next to the prose explaining it.

### Optional block attributes

You can override behaviour per block by adding lightweight attributes to the fence header:

````markdown
```sysml title="Battery interface" output="svg"
package Demo {
    interface def PowerInterface;
}
```
````

Supported attributes:

- `title="..."` overrides the title injected into the SVG.
- `output="html|svg"` temporarily overrides the configured `output_format`.

## Writing SysML inline

Create a fenced block inside any Markdown file:

````markdown
```sysml title="Vehicle structure"
package Batmobile {
    part def Vehicle;
    part def Batmobile :> Vehicle {
        part seat [2];
        part engine : BatmobileEngine;
        interface bat2eng : PowerInterface connect battery.powerPort to engine.port;
    }
}
```
````

Run `mkdocs serve` and the block will render inline as an SVG (wrapped in a `<figure>` by default).

## Output format

- `svg` (default): writes a standalone SVG file with embedded styles.
- `html`: wraps the SVG into a `<figure>` tag. Useful if you want to embed the output via templating rather than via Markdown image syntax.

## Sample project

This repo ships with `example/` showing inline rendering with MkDocs Material. Run it via:

```bash
pdm install
pdm run mkdocs serve -f example/mkdocs.yml
```

Open the dev server and inspect how the SysML block in `docs/index.md` turns into an SVG diagram dynamically.

To run the same checks our CI does, execute:

```bash
pdm run mkdocs build -f example/mkdocs.yml
```

## Live docs

The latest build of the example site is available on GitHub Pages:  
https://someshkashyap.github.io/mkdocs-sysmlv2/

## Contributing

Feel free to open issues or PRs with better parsing rules, styling ideas, or integration hooks.  
The parser is intentionally lightweight—if you need a new syntax feature, add a regression test and extend `SysMLParser`.

## License

Apache-2.0 (see `LICENSE`).
