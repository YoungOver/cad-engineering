"""План квартиры в DXF (AutoCAD): слои, оси, стены со штриховкой, проёмы, размеры, экспликация.
python plan_dwg.py -> plan.dxf, acad_model.png (тёмная тема), acad_paper.png (лист)"""
import math
from pathlib import Path

import ezdxf
from ezdxf.enums import TextEntityAlignment

OUT = Path(__file__).parent
doc = ezdxf.new('R2018', setup=True)
doc.units = 4  # мм
msp = doc.modelspace()
for name, color, lt in [('А-ОСИ', 1, 'CENTER'), ('А-СТЕНЫ', 7, 'CONTINUOUS'), ('А-ПЕРЕГОРОДКИ', 8, 'CONTINUOUS'),
                        ('А-ПРОЁМЫ', 4, 'CONTINUOUS'), ('А-ОКНА', 5, 'CONTINUOUS'), ('А-РАЗМЕРЫ', 3, 'CONTINUOUS'),
                        ('А-ТЕКСТ', 2, 'CONTINUOUS'), ('А-МЕБЕЛЬ', 9, 'CONTINUOUS'), ('А-ШТРИХОВКА', 8, 'CONTINUOUS')]:
    doc.layers.add(name, color=color, linetype=lt)
doc.styles.add('GOST', font='isocpeur.ttf')
ds = doc.dimstyles.duplicate_entry('EZDXF', 'GOST')
ds.dxf.dimtxt = 250; ds.dxf.dimasz = 150; ds.dxf.dimtsz = 150; ds.dxf.dimexe = 150; ds.dxf.dimexo = 100
ds.dxf.dimlfac = 1; ds.dxf.dimtxsty = 'GOST'; ds.dxf.dimclrd = 3; ds.dxf.dimclre = 3; ds.dxf.dimclrt = 3; ds.dxf.dimtad = 1; ds.dxf.dimgap = 60

T_EXT, T_IN = 380, 120                      # толщина наружных стен и перегородок
W, H = 9000, 6000                            # внутренний габарит


def wall_band(pts, t, layer, hatch=True):
    """полоса стены по оси pts (прямоугольник), со штриховкой ANSI31"""
    (x1, y1), (x2, y2) = pts
    if x1 == x2:
        poly = [(x1 - t / 2, y1), (x1 + t / 2, y1), (x1 + t / 2, y2), (x1 - t / 2, y2)]
    else:
        poly = [(x1, y1 - t / 2), (x2, y1 - t / 2), (x2, y1 + t / 2), (x1, y1 + t / 2)]
    msp.add_lwpolyline(poly, close=True, dxfattribs={'layer': layer, 'lineweight': 50 if layer == 'А-СТЕНЫ' else 35})
    if hatch:
        h = msp.add_hatch(color=8, dxfattribs={'layer': 'А-ШТРИХОВКА'})
        h.set_pattern_fill('ANSI31', scale=18 if t > 200 else 8)
        h.paths.add_polyline_path(poly, is_closed=True)


# наружные стены с проёмами (разрывы по окнам и двери)
ow = T_EXT / 2
wins_top = [(1300, 3000), (3500, 4900), (6300, 8100)]
x = -ow
for a, b in wins_top:
    wall_band([(x, H + ow), (a, H + ow)], T_EXT, 'А-СТЕНЫ'); x = b
wall_band([(x, H + ow), (W + ow, H + ow)], T_EXT, 'А-СТЕНЫ')
wall_band([(-ow, -ow), (3550, -ow)], T_EXT, 'А-СТЕНЫ'); wall_band([(4450, -ow), (W + ow, -ow)], T_EXT, 'А-СТЕНЫ')
wall_band([(-ow, -ow), (-ow, H + ow)], T_EXT, 'А-СТЕНЫ')
wall_band([(W + ow, -ow), (W + ow, 700)], T_EXT, 'А-СТЕНЫ'); wall_band([(W + ow, 1900), (W + ow, H + ow)], T_EXT, 'А-СТЕНЫ')
# окна: 3 линии в проёме
for a, b in wins_top:
    for dy in (-ow, 0, ow):
        msp.add_line((a, H + ow + dy), (b, H + ow + dy), dxfattribs={'layer': 'А-ОКНА'})
for dx in (-ow, 0, ow):
    msp.add_line((W + ow + dx, 700), (W + ow + dx, 1900), dxfattribs={'layer': 'А-ОКНА'})
# перегородки (в системе y вверх: кухня-гостиная сверху)
Y = lambda m: H - m
parts = [[(5400, Y(0)), (5400, Y(3800))], [(0, Y(3800)), (2400, Y(3800))], [(3400, Y(3800)), (5600, Y(3800))],
         [(6400, Y(3800)), (W, Y(3800))], [(2200, Y(3800)), (2200, Y(4200))], [(2200, Y(4950)), (2200, Y(6000))],
         [(6200, Y(3800)), (6200, Y(4150))], [(6200, Y(4950)), (6200, Y(6000))]]
for p in parts:
    wall_band(p, T_IN, 'А-ПЕРЕГОРОДКИ')


def door(hx, hy, L, a0, sweep):
    ex, ey = hx + L * math.cos(math.radians(a0)), hy + L * math.sin(math.radians(a0))
    msp.add_line((hx, hy), (ex, ey), dxfattribs={'layer': 'А-ПРОЁМЫ', 'lineweight': 35})
    s, e = (a0, a0 + sweep) if sweep > 0 else (a0 + sweep, a0)
    msp.add_arc((hx, hy), L, s, e, dxfattribs={'layer': 'А-ПРОЁМЫ'})


door(3550, -ow, 900, 90, -90) if False else door(3550, 0, 900, 90, -90)   # входная
door(5600, Y(3800), 800, 270, 90)           # спальня
door(2200, Y(4950), 750, 180, 90)           # с/у
door(6200, Y(4150), 800, 0, -90)            # кабинет

# мебель (упрощённо, слой А-МЕБЕЛЬ)
F = {'layer': 'А-МЕБЕЛЬ'}
msp.add_lwpolyline([(120, Y(300)), (720, Y(300)), (720, Y(3200)), (120, Y(3200))], close=True, dxfattribs=F)
msp.add_circle((2100, Y(1900)), 550, dxfattribs=F)
msp.add_lwpolyline([(4450, Y(700)), (5300, Y(700)), (5300, Y(3000)), (4450, Y(3000))], close=True, dxfattribs=F)
msp.add_lwpolyline([(7000, Y(1000)), (8950, Y(1000)), (8950, Y(2600)), (7000, Y(2600))], close=True, dxfattribs=F)
msp.add_lwpolyline([(70, Y(3900)), (790, Y(3900)), (790, Y(5600)), (70, Y(5600))], close=True, dxfattribs=F)
msp.add_lwpolyline([(7550, Y(3900)), (8930, Y(3900)), (8930, Y(4520)), (7550, Y(4520))], close=True, dxfattribs=F)

# оси
axes_x = [('1', -ow), ('2', 5400), ('3', W + ow)]
axes_y = [('А', -ow), ('Б', Y(3800)), ('В', H + ow)]
R = 400
for n, xx in axes_x:
    msp.add_line((xx, -ow - 2600), (xx, H + ow + 2600), dxfattribs={'layer': 'А-ОСИ'})
    for yy in (-ow - 2600 - R, H + ow + 2600 + R):
        msp.add_circle((xx, yy), R, dxfattribs={'layer': 'А-ОСИ'})
        msp.add_text(n, height=350, dxfattribs={'layer': 'А-ОСИ', 'style': 'GOST'}).set_placement((xx, yy), align=TextEntityAlignment.MIDDLE_CENTER)
for n, yy in axes_y:
    msp.add_line((-ow - 2600, yy), (W + ow + 2600, yy), dxfattribs={'layer': 'А-ОСИ'})
    for xx in (-ow - 2600 - R, W + ow + 2600 + R):
        msp.add_circle((xx, yy), R, dxfattribs={'layer': 'А-ОСИ'})
        msp.add_text(n, height=350, dxfattribs={'layer': 'А-ОСИ', 'style': 'GOST'}).set_placement((xx, yy), align=TextEntityAlignment.MIDDLE_CENTER)

# размеры: цепочки по осям и общие
D = {'layer': 'А-РАЗМЕРЫ'}
for (a, b) in [(-ow, 5400), (5400, W + ow)]:
    msp.add_linear_dim(base=(0, H + ow + 1200), p1=(a, H + ow), p2=(b, H + ow), dimstyle='GOST', dxfattribs=D).render()
msp.add_linear_dim(base=(0, H + ow + 1900), p1=(-ow, H + ow), p2=(W + ow, H + ow), dimstyle='GOST', dxfattribs=D).render()
for (a, b) in [(-ow, Y(3800)), (Y(3800), H + ow)]:
    msp.add_linear_dim(base=(-ow - 1200, 0), p1=(-ow, a), p2=(-ow, b), angle=90, dimstyle='GOST', dxfattribs=D).render()
msp.add_linear_dim(base=(-ow - 1900, 0), p1=(-ow, -ow), p2=(-ow, H + ow), angle=90, dimstyle='GOST', dxfattribs=D).render()
# привязка окон снизу-сверху (внутренняя цепочка)
pts = [-ow] + [v for ab in wins_top for v in ab] + [W + ow]
for a, b in zip(pts, pts[1:]):
    msp.add_linear_dim(base=(0, H + ow + 600), p1=(a, H + ow), p2=(b, H + ow), dimstyle='GOST', dxfattribs=D).render()

# помещения: номер в круге + площадь
rooms = [(1, 'Кухня-гостиная', 20.5, 2900, Y(2700)), (2, 'Спальня', 13.7, 7250, Y(3300)), (3, 'С/у', 4.8, 1350, Y(5000)),
         (4, 'Прихожая', 8.8, 4000, Y(4700)), (5, 'Кабинет', 6.2, 6950, Y(5300))]
for n, name, s, cx, cy in rooms:
    msp.add_circle((cx, cy + 350), 280, dxfattribs={'layer': 'А-ТЕКСТ'})
    msp.add_text(str(n), height=260, dxfattribs={'layer': 'А-ТЕКСТ', 'style': 'GOST'}).set_placement((cx, cy + 350), align=TextEntityAlignment.MIDDLE_CENTER)
    msp.add_text(f'{s:.1f}'.replace('.', ','), height=260, dxfattribs={'layer': 'А-ТЕКСТ', 'style': 'GOST'}).set_placement((cx, cy - 150), align=TextEntityAlignment.MIDDLE_CENTER)
    msp.add_line((cx - 450, cy + 20), (cx + 450, cy + 20), dxfattribs={'layer': 'А-ТЕКСТ'})

# экспликация справа
ex, ey = W + ow + 4200, H + ow
msp.add_text('Экспликация помещений', height=300, dxfattribs={'layer': 'А-ТЕКСТ', 'style': 'GOST'}).set_placement((ex, ey + 200))
cols = [0, 900, 5200, 6800]
rows_ = [('№', 'Наименование', 'S, м²')] + [(str(n), nm, f'{s:.1f}'.replace('.', ',')) for n, nm, s, *_ in rooms] + [('', 'Итого', '54,0')]
for i, r in enumerate(rows_):
    y0 = ey - i * 600
    msp.add_line((ex, y0), (ex + cols[-1], y0), dxfattribs={'layer': 'А-ТЕКСТ'})
    for j, v in enumerate(r):
        msp.add_text(v, height=240, dxfattribs={'layer': 'А-ТЕКСТ', 'style': 'GOST'}).set_placement((ex + cols[j] + 120, y0 - 420))
yb = ey - len(rows_) * 600
msp.add_line((ex, yb), (ex + cols[-1], yb), dxfattribs={'layer': 'А-ТЕКСТ'})
for c in cols:
    msp.add_line((ex + c, ey), (ex + c, yb), dxfattribs={'layer': 'А-ТЕКСТ'})

doc.saveas(OUT / 'plan.dxf')

# ---------- рендер: тёмная тема пространства модели
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy, LineweightPolicy

for name, bg, pol in [('acad_model', '#212830', ColorPolicy.COLOR), ('acad_paper', '#ffffff', ColorPolicy.BLACK)]:
    fig = plt.figure(figsize=(16, 9), dpi=150)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(bg); fig.patch.set_facecolor(bg)
    ctx = RenderContext(doc)
    cfg = Configuration(background_policy=BackgroundPolicy.CUSTOM, custom_bg_color=bg, color_policy=pol, lineweight_scaling=1.6,
                        lineweight_policy=LineweightPolicy.ABSOLUTE)
    Frontend(ctx, MatplotlibBackend(ax), config=cfg).draw_layout(msp, finalize=True)
    ax.set_facecolor(bg)
    fig.set_size_inches(16, 9); fig.savefig(OUT / f'{name}.png', facecolor=bg, dpi=160)
    plt.close(fig)
print('ok')
