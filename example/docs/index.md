# SysML v2 Sample

The `mkdocs-sysml2` plugin renders SysML fences inline. The snippet below stays inside
this Markdown file, and the plugin converts it into a diagram while `mkdocs serve` is
running:

````markdown
```sysml title="Batmobile structure"
package Demo::Batmobile {
    part def Vehicle;
    part def Batmobile :> Vehicle {
        part seat [2];
        part engine : BatmobileEngine;
        interface bat2eng : PowerInterface connect battery.powerPort to engine.powerPort;
    }
    part def BatmobileEngine;
    interface def PowerInterface;
    part usage FleetVehicle : Batmobile;
}
```
````
