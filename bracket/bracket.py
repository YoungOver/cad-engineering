"""Параметрический L-кронштейн (CadQuery): STEP/STL/GLB + SVG-проекции для чертежа."""
from pathlib import Path

import cadquery as cq

# Параметры (мм)
W = 80        # ширина кронштейна
L_BASE = 120  # длина основания
H_WALL = 100  # высота стенки
T = 8         # толщина
R_IN = 6      # внутренний радиус сгиба
RIB_T = 6     # толщина ребра

base = cq.Workplane('XY').box(L_BASE, W, T, centered=(False, True, False))
wall = cq.Workplane('XY').box(T, W, H_WALL, centered=(False, True, False))
body = base.union(wall)
body = body.edges('|Y and (>X or >Z)').fillet(3)
try:
    body = body.edges(cq.selectors.NearestToPointSelector((T, 0, T))).fillet(R_IN)
except Exception:
    pass

# рёбра жёсткости по краям
for y in (W / 2 - RIB_T / 2, -W / 2 + RIB_T / 2):
    rib = cq.Workplane('XZ').moveTo(T, T).lineTo(T + 70, T).lineTo(T, T + 60).close().extrude(RIB_T / 2, both=True)
    body = body.union(rib.translate((0, y, 0)))

# пазы крепления в основании
body = (body.faces('<Z').workplane(centerOption='CenterOfBoundBox')
        .pushPoints([(35, 20), (35, -20)]).slot2D(22, 9, 0).cutThruAll())
# отверстия с зенковкой в стенке
body = (body.faces('<X').workplane(centerOption='CenterOfBoundBox')
        .pushPoints([(-22, 25), (22, 25), (-22, -25), (22, -25)])
        .cskHole(8.5, 16, 90))
# облегчающий вырез в стенке
body = (body.faces('<X').workplane(centerOption='CenterOfBoundBox')
        .center(0, 0).rect(24, 30).cutThruAll())
body = body.edges('|X').edges(cq.selectors.BoxSelector((-1, -12.5, 34), (T + 1, 12.5, 66))).fillet(4) if False else body

out = Path(__file__).parent
cq.exporters.export(body, str(out / 'bracket.step'))
cq.exporters.export(body, str(out / 'bracket.stl'), tolerance=0.05, angularTolerance=0.1)
import trimesh; trimesh.load(str(out / 'bracket.stl')).export(str(out / 'bracket.glb'))
opts = {'showAxes': False, 'strokeWidth': 0.4, 'width': 640, 'height': 480, 'marginLeft': 90, 'marginTop': 60, 'showHidden': True, 'hiddenColor': (150, 150, 150)}
for name, d in [('front', (0, -1, 0)), ('top', (0, 0, 1)), ('side', (1, 0, 0)), ('iso', (1, -1, 0.8))]:
    o = dict(opts, projectionDir=d, showHidden=name != 'iso')
    cq.exporters.export(body, str(out / f'view_{name}.svg'), opt=o)
bb = body.val().BoundingBox()
vol = body.val().Volume()
print(f'bbox {bb.xlen:.0f}x{bb.ylen:.0f}x{bb.zlen:.0f} мм, объём {vol/1000:.1f} см3, масса (сталь 7.85) {vol*7.85e-6:.2f} кг')
