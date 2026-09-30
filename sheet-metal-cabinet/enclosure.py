"""Щит навесной из листа 1,5 мм: корпус, дверь, монтажная панель (CadQuery) + развёртка корпуса в DXF.
python enclosure.py -> *.step, *.glb, flat.dxf, flat.png"""
import math
from pathlib import Path

import cadquery as cq
import trimesh

OUT = Path(__file__).parent
W, D, H = 400.0, 200.0, 500.0     # наружные габариты, мм
t, R, K = 1.5, 2.0, 0.44          # толщина, внутренний радиус гиба, K-фактор

# ---------- корпус: коробка без передней стенки
outer = cq.Workplane('XY').box(W, D, H).edges('|Y or >Y').fillet(R + t)
inner = cq.Workplane('XY').box(W - 2 * t, D, H - 2 * t).edges('|Y or >Y').fillet(R).translate((0, -t, 0))
body = outer.cut(inner)
# жалюзи на боковинах: 6 щелей
for sx in (1, -1):
    pts = [(0, z) for z in (-150, -100, -50, 0, 50, 100)]
    body = body.faces('>X' if sx > 0 else '<X').workplane(centerOption='CenterOfBoundBox').pushPoints(pts).slot2D(90, 7).cutBlind(-t * 3)
# гермовводы в дне: 3 × Ø20,5 (M20)
body = body.faces('<Z').workplane(centerOption='CenterOfBoundBox').pushPoints([(-100, 20), (0, 20), (100, 20)]).hole(20.5, t * 3)
# навесные пазы на задней стенке
body = body.faces('>Y').workplane(centerOption='CenterOfBoundBox').pushPoints([(-150, 200), (150, 200), (-150, -200), (150, -200)]).slot2D(16, 8, 90).cutBlind(-t * 3)

# ---------- монтажная панель (оцинковка 2 мм), на стойках 15 мм от задней стенки
plate = cq.Workplane('XZ').rect(W - 60, H - 60).extrude(-2).translate((0, D / 2 - t - 15, 0))
plate = plate.faces('<Y').workplane(centerOption='CenterOfBoundBox').rarray(1, 90, 1, 4).rect(W - 100, 8).cutBlind(-4)
# DIN-рейки 35 мм
rails = cq.Workplane('XZ')
for z in (-135, -45, 45, 135):
    rails = rails.union(cq.Workplane('XZ').center(0, z).rect(W - 90, 35).extrude(7.5).translate((0, D / 2 - t - 17, 0)))

# ---------- дверь: панель с отбортовкой 20 мм, открыта на 105° вокруг левой петли
door = cq.Workplane('XZ').rect(W - 4, H - 4).extrude(t)
door = door.union(cq.Workplane('XZ').rect(W - 4, H - 4).rect(W - 4 - 2 * t, H - 4 - 2 * t).extrude(20).translate((0, 0, 0)))
door = door.translate((0, -D / 2 - 1, 0))
hinge = cq.Vector(-W / 2, -D / 2 - 1, 0)
door_open = door.rotate(hinge, hinge + cq.Vector(0, 0, 1), -105)
# ручка-замок
lock = cq.Workplane('XZ').center(W / 2 - 40, 0).rect(22, 90).extrude(-14).edges('|Y').fillet(4).translate((0, -D / 2 - 1 - t, 0))
lock = lock.rotate(hinge, hinge + cq.Vector(0, 0, 1), -105)

parts = {'body': body, 'plate': plate, 'rails': rails, 'door': door_open, 'lock': lock}
for n, p in parts.items():
    cq.exporters.export(p, str(OUT / f'{n}.stl'), tolerance=0.08, angularTolerance=0.12)
    trimesh.load(str(OUT / f'{n}.stl')).export(str(OUT / f'{n}.glb'))
cq.exporters.export(body, str(OUT / 'body.step'))
asm = cq.Assembly().add(body, name='Корпус').add(plate, name='Панель монтажная').add(rails, name='DIN-рейки').add(door_open, name='Дверь').add(lock, name='Замок')
asm.save(str(OUT / 'shield.step'))

# ---------- развёртка корпуса
BA = math.pi / 2 * (R + K * t)          # длина дуги по нейтральному слою
OS = R + t                              # наружный отступ до вершины гиба
BD = 2 * OS - BA                        # вычет на гиб
fw = W - 2 * OS                         # плоская часть задней стенки
fh = H - 2 * OS
fl = D - OS                             # плоская часть полки (от вершины гиба до кромки)
print(f'BA={BA:.2f}  BD={BD:.2f}  развёртка {fw + 2 * (BA + fl):.1f} × {fh + 2 * (BA + fl):.1f} мм')

import ezdxf
from ezdxf.enums import TextEntityAlignment
doc = ezdxf.new('R2018', setup=True)
doc.units = 4
msp = doc.modelspace()
doc.layers.add('CUT', color=7); doc.layers.add('BEND', color=1, linetype='DASHED'); doc.layers.add('DIM', color=3); doc.layers.add('TXT', color=2)
ds = doc.dimstyles.duplicate_entry('EZDXF', 'G'); ds.dxf.dimlfac = 1; ds.dxf.dimtxt = 14; ds.dxf.dimasz = 8; ds.dxf.dimexe = 6; ds.dxf.dimexo = 4; ds.dxf.dimtad = 1; ds.dxf.dimclrd = 3; ds.dxf.dimclre = 3; ds.dxf.dimclrt = 3
a = BA + fl                               # вылет полки в развёртке от линии гиба-начала
X0, X1, Y0, Y1 = -fw / 2, fw / 2, -fh / 2, fh / 2
relief = 3                                # угловой вырез-разгрузка
outline = [(X0, Y0 - a), (X1, Y0 - a), (X1, Y0 - relief), (X1 + relief, Y0 - relief), (X1 + relief, Y0), (X1 + a, Y0),
           (X1 + a, Y1), (X1 + relief, Y1), (X1 + relief, Y1 + relief), (X1, Y1 + relief), (X1, Y1 + a), (X0, Y1 + a),
           (X0, Y1 + relief), (X0 - relief, Y1 + relief), (X0 - relief, Y1), (X0 - a, Y1), (X0 - a, Y0), (X0 - relief, Y0),
           (X0 - relief, Y0 - relief), (X0, Y0 - relief)]
msp.add_lwpolyline(outline, close=True, dxfattribs={'layer': 'CUT', 'lineweight': 50})
for (p, q) in [((X0, Y0), (X1, Y0)), ((X0, Y1), (X1, Y1)), ((X0, Y0), (X0, Y1)), ((X1, Y0), (X1, Y1))]:
    msp.add_line(p, q, dxfattribs={'layer': 'BEND'})
# отверстия в развёртке: пазы на задней стенке, гермовводы на нижней полке, жалюзи на боковых
for sx, sy in ((-150, 200), (150, 200), (-150, -200), (150, -200)):
    msp.add_lwpolyline([(sx - 4, sy - 4), (sx + 4, sy - 4), (sx + 4, sy + 4), (sx - 4, sy + 4)], close=True, dxfattribs={'layer': 'CUT'})
for gx in (-100, 0, 100):
    msp.add_circle((gx, Y0 - BA - (D / 2 - OS) + 0), 10.25, dxfattribs={'layer': 'CUT'})
for sx in (1, -1):
    cx = (X1 if sx > 0 else X0) + sx * (BA + (D / 2 - OS))
    for z in (-150, -100, -50, 0, 50, 100):
        msp.add_lwpolyline([(cx - 45, z - 3.5), (cx + 45, z - 3.5), (cx + 45, z + 3.5), (cx - 45, z + 3.5)], close=True, dxfattribs={'layer': 'CUT'})
L = X1 + a - (X0 - a); Hh = Y1 + a - (Y0 - a)
msp.add_linear_dim(base=(0, Y1 + a + 40), p1=(X0 - a, Y1), p2=(X1 + a, Y1), dimstyle='G', dxfattribs={'layer': 'DIM'}).render()
msp.add_linear_dim(base=(X1 + a + 40, 0), p1=(X1, Y0 - a), p2=(X1, Y1 + a), angle=90, dimstyle='G', dxfattribs={'layer': 'DIM'}).render()
msp.add_linear_dim(base=(0, Y1 + a + 15), p1=(X0, Y1), p2=(X1, Y1), dimstyle='G', dxfattribs={'layer': 'DIM'}).render()
for i, s in enumerate([f'Развёртка корпуса ЩН-400.500.200', f'Лист 1,5 мм, R гиба {R:.0f}, K = {K}',
                       f'Гибов: 4 × 90° вверх', f'Вычет на гиб {BD:.2f} мм'.replace('.', ',')]):
    msp.add_text(s, height=16 if i else 20, dxfattribs={'layer': 'TXT'}).set_placement((X0 - a, Y0 - a - 50 - i * 26))
doc.saveas(OUT / 'flat.dxf')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy, LineweightPolicy
fig = plt.figure(figsize=(10, 10)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor('#212830'); fig.patch.set_facecolor('#212830')
Frontend(RenderContext(doc), MatplotlibBackend(ax), config=Configuration(background_policy=BackgroundPolicy.CUSTOM, custom_bg_color='#212830', color_policy=ColorPolicy.COLOR,
         lineweight_policy=LineweightPolicy.ABSOLUTE, lineweight_scaling=1.5)).draw_layout(msp, finalize=True)
fig.savefig(OUT / 'flat.png', dpi=150, facecolor='#212830')
print('ok', f'{L:.1f} x {Hh:.1f}')
