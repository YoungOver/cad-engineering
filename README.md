# cad-engineering

Mechanical design done as code: parametric 3D models, ESKD-style drawings and flat patterns generated with CadQuery, OpenCascade and ezdxf. Change a parameter, rerun the script, get a new STEP, STL, DXF and SVG.

![](docs/cabinet.gif)

## gear-drive-assembly

A ten-part shaft assembly: housing, shaft, spur gear, two 206 bearings, covers, key and fasteners.

- `model.py` builds every part parametrically and exports STEP, STL and GLB
- `drawing.py` projects the assembly with hidden-line removal and writes an A3 assembly drawing with dimensions, balloons, title block and bill of materials to DXF and SVG
- `bom.json` feeds both the drawing and the specification

| Render | Exploded view | Assembly drawing A3 |
|---|---|---|
| ![](docs/asm_render.jpg) | ![](docs/asm_exploded.jpg) | ![](docs/asm_drawing.jpg) |

## sheet-metal-cabinet

Electrical cabinet from 1.5 mm sheet steel with a hinged door, mounting plate and DIN rails.

- body built as a bent shell, not as a solid block
- flat pattern for laser cutting computed with a K-factor bend allowance and exported to DXF with bend lines
- door opening animation rendered in the browser with Three.js

| 3D | Flat pattern |
|---|---|
| ![](docs/sheet_3d.jpg) | ![](docs/sheet_show.jpg) |

## autocad-floor-plan

54 m2 apartment plan generated straight into DXF: walls on proper layers, doors and windows as blocks, dimensions at the right scale, room areas and a paper-space sheet ready to plot.

| Model space | Paper space |
|---|---|
| ![](docs/acad_model.jpg) | ![](docs/acad_paper.jpg) |

## bracket

A parametric bracket with fillets and counterbored holes, exported to STEP, STL, GLB and four orthographic SVG views.

## Stack

CadQuery, OpenCascade (OCP), ezdxf, trimesh, numpy, matplotlib, Three.js for web previews. Files open in SolidWorks, KOMPAS-3D, AutoCAD and FreeCAD.

```bash
pip install -r requirements.txt
python gear-drive-assembly/model.py && python gear-drive-assembly/drawing.py
python sheet-metal-cabinet/enclosure.py
python autocad-floor-plan/plan_dwg.py
```
