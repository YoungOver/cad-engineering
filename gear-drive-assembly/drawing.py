"""Сборочный чертёж А3 (ЕСКД) из 3D-модели: SVG (+ HTML-обёртка для JPG/PDF) и DXF.

Геометрия видов — точная проекция B-rep с удалением невидимых линий (OpenCascade HLR),
штриховка — реальные сечения тел плоскостью разреза. Размеры берутся из параметров модели.
"""
import json
import math
from pathlib import Path

import cadquery as cq
import ezdxf
import numpy as np
from ezdxf.enums import TextEntityAlignment
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepLib import BRepLib
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

import model as md

OUT = Path(__file__).parent
S = 0.5  # масштаб 1:2
BOM = json.loads((OUT / "bom.json").read_text(encoding="utf-8"))

# --------------------------------------------------------------------------- дисплей-лист
# слои: vis (основная), thin (тонкая), axis (штрихпунктир), hid (штриховая), frame
POLYS, HATCH, TEXTS, DIMS, LEADERS, MASKS = [], [], [], [], [], []


def pl(pts, layer="thin", closed=False):
    POLYS.append(dict(pts=[tuple(map(float, p)) for p in pts], layer=layer, closed=closed))


def line(a, b, layer="thin"):
    pl([a, b], layer)


def rect(x, y, w, h, layer="frame"):
    pl([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], layer, closed=True)


def text(x, y, s, h=3.5, anchor="start", rot=0.0, italic=True, mask=False):
    TEXTS.append(dict(x=x, y=y, s=s, h=h, anchor=anchor, rot=rot, mask=mask))


# --------------------------------------------------------------------------- OCC helpers
def edges_polys(comp, defl=0.015):
    out = []
    if comp is None or comp.IsNull():
        return out
    BRepLib.BuildCurves3d_s(comp, 1e-6)
    ex = TopExp_Explorer(comp, TopAbs_EDGE)
    while ex.More():
        e = TopoDS.Edge_s(ex.Current())
        try:
            c = BRepAdaptor_Curve(e)
            p = GCPnts_QuasiUniformDeflection(c, defl, c.FirstParameter(), c.LastParameter())
            if p.IsDone() and p.NbPoints() > 1:
                out.append([(p.Value(i + 1).X(), p.Value(i + 1).Y()) for i in range(p.NbPoints())])
        except Exception:  # noqa: BLE001
            pass
        ex.Next()
    return out


def hlr(shapes, ndir, xdir, smooth=False, hidden=False):
    comp = cq.Compound.makeCompound(shapes)
    algo = HLRBRep_Algo()
    algo.Add(comp.wrapped)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*ndir), gp_Dir(*xdir))))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    vis = edges_polys(h.VCompound()) + edges_polys(h.OutLineVCompound())
    sm = edges_polys(h.Rg1LineVCompound()) if smooth else []
    hid = (edges_polys(h.HCompound()) + edges_polys(h.OutLineHCompound())) if hidden else []
    return vis, sm, hid


def section_loops(shape, u, v, origin=(0, 0, 0), normal=(0, 1, 0), step=0.15):
    plane = cq.Face.makePlane(3000, 3000, basePnt=origin, dir=normal)
    sec = shape.intersect(plane)
    loops = []
    for f in sec.Faces():
        for w in [f.outerWire()] + f.innerWires():
            n = max(24, int(w.Length() / step))
            P = w.positions(np.linspace(0, 1, n, endpoint=False))
            loops.append([(p.dot(cq.Vector(*u)), p.dot(cq.Vector(*v))) for p in P])
    return loops



if __name__ == "__main__" and len(__import__("sys").argv) > 1 and __import__("sys").argv[1] == "--iso":
    import sys
    d = np.array(list(map(float, sys.argv[2].split(","))))
    d /= np.linalg.norm(d)
    xd_ = np.cross(d, [0, 0, 1])
    xd_ /= np.linalg.norm(xd_)
    ins = md.build(tap_d=8.0)
    v_, s_, _ = hlr([it["wp"].val() for it in ins], tuple(d), tuple(xd_), smooth=True)
    flip = lambda P: [[(-a, -b) for a, b in p] for p in P]  # noqa: E731  (xd_ = -(экранная X), поворот на 180°)
    Path(sys.argv[3]).write_text(json.dumps(dict(vis=flip(v_), sm=flip(s_))))
    sys.exit(0)

class View:
    """Проекция: u,v (мм модели) -> лист (мм), ось v вверх."""

    def __init__(self, cx, cy, s=S):
        self.cx, self.cy, self.s = cx, cy, s

    def __call__(self, u, v):
        return (self.cx + u * self.s, self.cy - v * self.s)

    def polys(self, polys, layer):
        for p in polys:
            pl([self(*q) for q in p], layer)


# --------------------------------------------------------------------------- модель
inst = md.build(tap_d=8.0)  # для чертежа резьбовое отверстие = наружный Ø резьбы (условно)
HALF = cq.Solid.makeBox(2000, 1000, 2000, pnt=cq.Vector(-1000, -1000, -1000))  # y<0

# ============================================================== ГЛАВНЫЙ ВИД: разрез А-А
MV = View(95, 76)
print("HLR: главный вид (разрез)…")
shapes, hatch_src = [], []
for it in inst:
    shp = it["wp"].val()
    if it["section"]:
        shapes.append(shp.cut(HALF))
        hatch_src.append(it)
    else:
        shapes.append(shp)
vis, _, _ = hlr(shapes, (0, -1, 0), (1, 0, 0))
MV.polys(vis, "vis")

# штриховки
_, rf, r_p, ra = md.gear()
PAT = {1: ("h45", 2.0), 4: ("h135", 2.0), 5: ("h135", 2.0), 3: ("h135", 1.4), 6: ("h45", 1.4),
       8: ("cross", 1.2), 9: ("h45", 1.0)}
for it in hatch_src:
    shp = it["wp"].val()
    if it["pos"] == 3:
        shp = shp.intersect(md.cyl_x(2 * rf, 50, 120).val())  # зубья в разрезе не штрихуют
    if it["pos"] == 9 and it["sub"] == "inner":
        pat = ("h135", 1.0)
    else:
        pat = PAT[it["pos"]]
    loops = section_loops(shp, (1, 0, 0), (0, 0, 1))
    if loops:
        HATCH.append(dict(loops=[[MV(*q) for q in lp] for lp in loops], pat=pat[0], sp=pat[1], pos=it["pos"]))

# зубчатое колесо: линия впадин (основная) и делительная (штрихпунктир)
x0g, x1g = md.X_GEAR_C - md.GEAR_B / 2, md.X_GEAR_C + md.GEAR_B / 2
for sgn in (1, -1):
    line(MV(x0g, sgn * rf), MV(x1g, sgn * rf), "vis")
    line(MV(x0g - 3, sgn * r_p), MV(x1g + 3, sgn * r_p), "axis")
# осевые линии
line(MV(-68, 0), MV(122, 0), "axis")
line(MV(md.X_GEAR_C, 58), MV(md.X_GEAR_C, -58), "axis")
for sgn in (1, -1):
    z = sgn * md.PCD / 2
    line(MV(-66, z), MV(-26, z), "axis")
    line(MV(26, z), MV(66, z), "axis")
line(MV(0, 30), MV(0, md.TUBE_D / 2 + md.BOSS_H + 4), "axis")
for xb in (-md.X_GEAR_C, ):
    pass

# ============================================================== ВИД СЛЕВА
LV = View(250, 56)
print("HLR: вид слева…")
full = [it["wp"].val() for it in inst]
vis, _, _ = hlr(full, (-1, 0, 0), (0, -1, 0))
LV.polys(vis, "vis")
line(LV(-64, 0), LV(64, 0), "axis")
line(LV(0, -89), LV(0, md.TUBE_D / 2 + md.BOSS_H + 4), "axis")
# окружность центров Ø84
pts = [LV(md.PCD / 2 * math.cos(t), md.PCD / 2 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 181)]
pl(pts, "axis")
for a in md.BOLT_ANGLES:
    ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    # в виде слева экранная u = -y; болт на (y,z)=(r cos a, r sin a) -> u = -r cos a
    uc, vc = -md.PCD / 2 * ca, md.PCD / 2 * sa
    line(LV(uc + 7 * ca, vc - 7 * sa) if False else LV(-(md.PCD / 2 - 7) * ca, (md.PCD / 2 - 7) * sa),
         LV(-(md.PCD / 2 + 7) * ca, (md.PCD / 2 + 7) * sa), "axis")
# след секущей плоскости А-А (плоскость y=0 -> u=0); взгляд в +y -> на экране влево
def cut_mark(view, u, v0, v1, letter, adir=(-1, 0)):
    a, b = view(u, v0), view(u, v1)
    line(a, b, "cut")
    LEADERS.append(dict(kind="cutarrow", at=b, d=adir))
    text(b[0] + adir[0] * 5.5 + (0 if adir[0] else 3.5), b[1] + (-1.2 if (b[1] < a[1]) else 5.2), letter, 5, "middle")


cut_mark(LV, 0, md.TUBE_D / 2 + md.BOSS_H + 3, md.TUBE_D / 2 + md.BOSS_H + 10, "А")
cut_mark(LV, 0, -md.H - 3, -md.H - 10, "А")

X_BB = 88.0
cut_mark(MV, X_BB, 55, 62, "Б", adir=(-1, 0))
cut_mark(MV, X_BB, -55, -62, "Б", adir=(-1, 0))

# ============================================================== СЕЧЕНИЕ Б-Б (плоскость x = 88, взгляд в -X)
BV = View(190, 172)
text(BV(0, 0)[0], BV(0, 60)[1] - 2, "Б–Б", 5, "middle")
PAT_BB = {3: ("h135", 1.4), 2: ("h45", 1.2), 10: ("h135", 1.0)}
for it in inst:
    if it["pos"] in PAT_BB:
        loops = section_loops(it["wp"].val(), (0, 1, 0), (0, 0, 1), origin=(X_BB, 0, 0), normal=(1, 0, 0), step=0.1)
        if loops:
            pts = [[BV(*q) for q in lp] for lp in loops]
            HATCH.append(dict(loops=pts, pat=PAT_BB[it["pos"]][0], sp=PAT_BB[it["pos"]][1], pos=it["pos"]))
            for lp in pts:
                pl(lp, "vis", closed=True)
line(BV(-60, 0), BV(60, 0), "axis")
line(BV(0, -60), BV(0, 60), "axis")
_, _rf, _rp, _ = md.gear()
pl([BV(_rp * math.cos(t), _rp * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 241)], "axis")
pl([BV(31.5 * math.cos(t), 31.5 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 181)], "axis")

# ============================================================== ВИД СВЕРХУ
TV = View(95, 172)
print("HLR: вид сверху…")
vis, _, _ = hlr(full, (0, 0, 1), (1, 0, 0))
TV.polys(vis, "vis")
line(TV(-68, 0), TV(122, 0), "axis")
line(TV(md.X_GEAR_C, -60), TV(md.X_GEAR_C, 60), "axis")
for sx in (-1, 1):
    for sy in (-1, 1):
        x, y = sx * md.FOOT_X, sy * md.FOOT_Y
        line(TV(x - 11, y), TV(x + 11, y), "axis")
        line(TV(x, y - 11), TV(x, y + 11), "axis")
    line(TV(sx * md.FOOT_X, -md.FOOT_Y + 11), TV(sx * md.FOOT_X, md.FOOT_Y - 11), "axis")
line(TV(0, -14), TV(0, 14), "axis")

# ============================================================== ИЗОМЕТРИЯ
print("HLR: изометрия…")


def iso_hlr():
    """HLR в изометрии в дочернем процессе (OCC HLR иногда падает на отдельных направлениях)."""
    import subprocess
    import sys
    cache = OUT / "out" / "_iso_hlr.json"
    for d in ("1,-1,1", "1,-1,1.001", "1.02,-1,1", "1,-1.02,1", "1,-0.98,1.01"):
        r = subprocess.run([sys.executable, str(OUT / "drawing.py"), "--iso", d, str(cache)], capture_output=True)
        if r.returncode == 0 and cache.exists():
            dat = json.loads(cache.read_text())
            print("  iso dir", d)
            return dat["vis"], dat["sm"]
    raise RuntimeError("iso HLR failed")


vis, sm = iso_hlr()
allp = [q for p in vis for q in p]
us, vs = [q[0] for q in allp], [q[1] for q in allp]
ISO_BOX = (304, 12, 106, 92)  # x, y, w, h на листе
k_iso = min(ISO_BOX[2] / (max(us) - min(us)), ISO_BOX[3] / (max(vs) - min(vs)))
IV = View(ISO_BOX[0] + ISO_BOX[2] / 2 - (max(us) + min(us)) / 2 * k_iso,
          ISO_BOX[1] + ISO_BOX[3] / 2 + (max(vs) + min(vs)) / 2 * k_iso, k_iso)
IV.polys(vis, "vis_iso")
IV.polys(sm, "thin")


# ============================================================== РАЗМЕРЫ
def dim(kind, p1, p2, at, txt, **kw):
    """kind: h|v (линейные), p1/p2 — точки на листе, at — координата размерной линии (y для h, x для v)."""
    DIMS.append(dict(kind=kind, p1=p1, p2=p2, at=at, txt=txt, **kw))


# главный вид
T = md.TUBE_D / 2 + md.BOSS_H
xl_bolt = -(md.X_FACE + md.COVER_T + 5.3)
xr_bolt = md.SHAFT_END + 8 + 5.3
dim("h", MV(-md.X_FACE, md.FLANGE_D / 2), MV(md.X_FACE, md.FLANGE_D / 2), MV(0, T + 12)[1], "92")
dim("h", MV(md.X_FACE, md.FLANGE_D / 2), MV(md.X_GEAR_C, r_p + 4), MV(0, T + 12)[1], "38")
dim("h", MV(xl_bolt, 0), MV(xr_bolt, 0), MV(0, T + 22)[1], f"{xr_bolt - xl_bolt:.1f}*".replace(".", ","))
dim("h", MV(-md.BASE_L / 2, -md.H), MV(md.BASE_L / 2, -md.H), MV(0, -md.H - 10)[1], "120")
dim("v", MV(-md.BASE_L / 2, -md.H), MV(-66, 0), MV(-76, 0)[0], "85±0,1")
dim("v", MV(-md.BASE_L / 2, -md.H + md.BASE_T), MV(-md.BASE_L / 2, -md.H), MV(-66, 0)[0], "16", small=True)
dim("v", MV(-32, md.BORE_D / 2), MV(-32, -md.BORE_D / 2), MV(-32, 0)[0], "⌀62 H7/l0", inside=True, tpos=0.5)
dim("v", MV(32, 15), MV(32, -15), MV(32, 0)[0], "⌀30 L0/k6", inside=True, tpos=0.5)
dim("v", MV(101, 12.5), MV(101, -12.5), MV(101, 0)[0], "⌀25 H7/k6", inside=True, tpos=0.5)
# сечение Б-Б: шпоночное соединение
dim("h", BV(-4, 16), BV(4, 16), BV(0, 25)[1], "8 P9/h9", small=True)

# вид слева
dim("v", LV(md.BASE_W / 2, -md.H), LV(11, T), LV(md.BASE_W / 2 + 12, 0)[0], "141*")
dim("diam", LV(0, 0), md.FLANGE_D / 2 * S, math.radians(125), "⌀110", shelf=14)
dim("diam", LV(0, 0), md.PCD / 2 * S, math.radians(-35), "⌀84", shelf=8, half=True)
# вид сверху
dim("h", TV(-md.FOOT_X, -md.FOOT_Y), TV(md.FOOT_X, -md.FOOT_Y), TV(0, -md.BASE_W / 2 - 9)[1], "80")
dim("v", TV(-md.FOOT_X, md.FOOT_Y), TV(-md.FOOT_X, -md.FOOT_Y), TV(-md.BASE_L / 2 - 8, 0)[0], "136")
dim("v", TV(-md.BASE_L / 2, md.BASE_W / 2), TV(-md.BASE_L / 2, -md.BASE_W / 2), TV(-md.BASE_L / 2 - 17, 0)[0], "170")
LEADERS.append(dict(kind="note", at=TV(md.FOOT_X + 5, md.FOOT_Y - 5), to=(TV(0, 0)[0] + 50, TV(0, md.FOOT_Y + 14)[1]),
                    txt="4 отв. ⌀14"))

# ============================================================== ПОЗИЦИИ (главный вид)
POSN = [  # (поз, точка на детали в коорд. модели (x,z), полка на листе (x,y))
    (1, (-20, 40), (40, 30)),
    (4, (-51, 44), (40, 38)),
    (7, (-58, 42), (40, 46)),
    (9, (-32, 29), (40, 54)),
    (2, (-10, 7), (40, 62)),
    (3, (84, 30), (162, 50)),
    (6, (107, 14), (162, 60)),
    (10, (84, 13.5), (162, 78)),
    (8, (51, -22), (162, 88)),
    (5, (51, -38), (162, 96)),
]
for p, (u, v), shelf in POSN:
    LEADERS.append(dict(kind="pos", at=MV(u, v), to=shelf, txt=str(p)))

# подписи видов
text(MV(0, 0)[0] + 10, 18, "А–А", 5, "middle")

# ============================================================== РАМКА, ШТАМП, СПЕЦИФИКАЦИЯ
SW, SH = 420, 297
rect(0, 0, SW, SH, "trim")
rect(20, 5, SW - 25, SH - 10, "frame")
# графа 26 (обозначение, повернутое на 180°)
rect(20, 5, 70, 14, "frame")
text(55, 12, "АИ.301.001.00 СБ", 3.5, "middle", rot=180)
# боковые графы (Инв. № подл. и т.д.)
gx = 8
for y0, hh, lab in ((5 + 287 - 25, 25, "Инв. № подл."), (5 + 287 - 60, 35, "Подп. и дата"), (5 + 287 - 85, 25, "Взам. инв. №"),
                    (5 + 287 - 110, 25, "Инв. № дубл."), (5 + 287 - 145, 35, "Подп. и дата")):
    rect(gx, y0, 5, hh, "frame")
    rect(gx + 5, y0, 7, hh, "frame")
    text(gx + 3.6, y0 + hh / 2, lab, 2.5, "middle", rot=-90)

# основная надпись форма 1 (185 x 55)
TX, TY = SW - 5 - 185, SH - 5 - 55
rect(TX, TY, 185, 55, "frame")
for i in range(1, 11):  # строки левой части
    lay = "frame" if i in (5, 6) else "thin"
    line((TX, TY + 5 * i), (TX + 65, TY + 5 * i), lay)
for dx in (7, 17, 40, 55):
    line((TX + dx, TY), (TX + dx, TY + (30 if dx in (7, 17) else 55)), "frame")
line((TX + 65, TY), (TX + 65, TY + 55), "frame")
line((TX + 65, TY + 15), (TX + 185, TY + 15), "frame")
line((TX + 135, TY + 15), (TX + 135, TY + 55), "frame")
line((TX + 65, TY + 40), (TX + 135, TY + 40), "frame")
line((TX + 135, TY + 20), (TX + 185, TY + 20), "frame")
line((TX + 135, TY + 35), (TX + 185, TY + 35), "frame")
line((TX + 135, TY + 40), (TX + 185, TY + 40), "frame")
for dx in (140, 145, 150):
    line((TX + dx, TY + 20), (TX + dx, TY + 35), "thin")
line((TX + 150, TY + 15), (TX + 150, TY + 35), "frame")
line((TX + 167, TY + 15), (TX + 167, TY + 35), "frame")
line((TX + 155, TY + 35), (TX + 155, TY + 40), "frame")
f = 2.6
for lab, x in (("Изм.", 3.5), ("Лист", 12), ("№ докум.", 28.5), ("Подп.", 47.5), ("Дата", 60)):
    text(TX + x, TY + 29.2, lab, f, "middle")
for i, lab in enumerate(("Разраб.", "Пров.", "Т.контр.", "", "Н.контр.", "Утв.")):
    text(TX + 1, TY + 34.2 + 5 * i, lab, f)
text(TX + 18, TY + 34.2, "Атуев И.", f)
text(TX + 56, TY + 34.2, "09.26", 2.3)
text(TX + 125, TY + 10, "АИ.301.001.00 СБ", 6, "middle")
text(TX + 100, TY + 25.5, "Узел приводного вала", 5, "middle")
text(TX + 100, TY + 33, "Сборочный чертеж", 3.5, "middle")
text(TX + 142.5, TY + 19, "Лит.", f, "middle")
text(TX + 158.5, TY + 19, "Масса", f, "middle")
text(TX + 176, TY + 19, "Масштаб", f, "middle")
text(TX + 158.5, TY + 29.5, f"{BOM['total_mass']:.2f}".replace(".", ","), 5, "middle")
text(TX + 176, TY + 29.5, "1:2", 5, "middle")
text(TX + 137, TY + 39, "Лист 1", f)
text(TX + 157, TY + 39, "Листов 1", f)
text(TX + 160, TY + 47, "Атуев И.", 3.5, "middle")
text(TX + 160, TY + 52, "3D-модели и чертежи", 2.6, "middle")
text(TX + 100, TY + 49, "", 3.5, "middle")  # графа «Материал» на СБ не заполняется
# под штампом: копировал / формат
text(TX + 90, SH - 1.2, "Копировал", 2.5, "middle")
text(TX + 160, SH - 1.2, "Формат А3", 2.5, "middle")

# спецификация (ГОСТ 2.106, форма 1) над основной надписью
COLS = [6, 6, 8, 70, 63, 10, 22]
rows = [("", "", "", "", "Документация", "", "", "hdr"),
        ("А3", "", "", "АИ.301.001.00 СБ", "Сборочный чертеж", "", "", ""),
        ("", "", "", "", "Детали", "", "", "hdr")]
fmt = {1: "А3", 2: "А4", 3: "А4", 4: "А4", 5: "А4", 6: "А4"}
for p in range(1, 7):
    b = BOM["bom"][str(p)]
    rows.append((fmt[p], "", str(p), b["code"], b["name"], str(b["qty"]), b.get("note", "").replace("; ", " "), ""))
rows.append(("", "", "", "", "Стандартные изделия", "", "", "hdr"))
for p in range(7, 11):
    b = BOM["bom"][str(p)]
    rows.append(("", "", str(p), "", b["name"], str(b["qty"]), "", ""))
SPH = 15 + 8 * len(rows)
SX, SY = TX, TY - SPH
rect(SX, SY, 185, SPH, "frame")
x = SX
for w in COLS[:-1]:
    x += w
    line((x, SY), (x, SY + SPH), "frame")
line((SX, SY + 15), (SX + 185, SY + 15), "frame")
for i in range(1, len(rows)):
    line((SX, SY + 15 + 8 * i), (SX + 185, SY + 15 + 8 * i), "thin")
hx = np.cumsum([0] + COLS)
for lab, i, rot in (("Формат", 0, -90), ("Зона", 1, -90), ("Поз.", 2, -90), ("Обозначение", 3, 0), ("Наименование", 4, 0),
                    ("Кол.", 5, -90), ("Приме-", 6, 0)):
    cx_ = SX + (hx[i] + hx[i + 1]) / 2
    if rot:
        text(cx_ + 1, SY + 7.5, lab, 2.5, "middle", rot=-90)
    else:
        text(cx_, SY + 8.8 if lab != "Приме-" else SY + 6.6, lab, 3.5, "middle")
text(SX + (hx[6] + hx[7]) / 2, SY + 11.6, "чание", 3.5, "middle")
for i, r in enumerate(rows):
    yb = SY + 15 + 8 * i + 5.6
    if r[7] == "hdr":
        cx_ = SX + (hx[4] + hx[5]) / 2
        text(cx_, yb, r[4], 3.5, "middle")
        wv = len(r[4]) * 1.95
        line((cx_ - wv / 2, yb + 0.9), (cx_ + wv / 2, yb + 0.9), "thin")
        continue
    for j, val in enumerate(r[:7]):
        if not val:
            continue
        if j in (0, 1, 2, 5):
            text(SX + (hx[j] + hx[j + 1]) / 2, yb, val, 3.5, "middle")
        else:
            hh = 3.5 if len(val) * 2.45 < COLS[j] - 2.4 else (COLS[j] - 2.4) / len(val) / 0.70
            text(SX + hx[j] + 1.2, yb, val, min(3.5, hh))

# технические требования
TT = ["1. *Размеры для справок.",
      "2. Осевую игру вала 0,05...0,15 мм обеспечить",
      "    подрезкой пояска крышки поз. 4 по месту.",
      "3. Полости подшипников заполнить смазкой",
      "    Литол-24 ГОСТ 21150-2017 на 2/3 объема.",
      "4. Вал должен проворачиваться от руки",
      "    плавно, без заеданий.",
      "5. Необработанные поверхности корпуса и крышек",
      "    окрасить эмалью ПФ-115 ГОСТ 6465-76."]
for i, s_ in enumerate(TT):
    text(122, 238 + 5.9 * i, s_, 3.0)

# ============================================================== ВЫВОД SVG
STROKE = {"vis": 0.5, "vis_iso": 0.35, "thin": 0.18, "axis": 0.18, "hid": 0.18, "frame": 0.6, "trim": 0.15, "cut": 0.9}
DASH = {"axis": "7 1.2 1 1.2", "hid": "2 1"}


def fmt_n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def svg_text(t):
    tr = f' transform="rotate({t["rot"]} {fmt_n(t["x"])} {fmt_n(t["y"])})"' if t["rot"] else ""
    s = t["s"].replace("&", "&amp;").replace("<", "&lt;")
    return (f'<text x="{fmt_n(t["x"])}" y="{fmt_n(t["y"])}" font-size="{t["h"] * 1.36:.2f}" '
            f'text-anchor="{t["anchor"]}"{tr}>{s}</text>')


def arrow(tip, ang, L=2.8, W=0.85):
    ca, sa = math.cos(ang), math.sin(ang)
    b1 = (tip[0] - L * ca - W / 2 * -sa, tip[1] - L * sa - W / 2 * ca)
    b2 = (tip[0] - L * ca + W / 2 * -sa, tip[1] - L * sa + W / 2 * ca)
    return f'<path d="M{fmt_n(tip[0])},{fmt_n(tip[1])} L{fmt_n(b1[0])},{fmt_n(b1[1])} L{fmt_n(b2[0])},{fmt_n(b2[1])} Z" class="ar"/>', (tip, b1, b2)


DXF_EXTRA = []  # (kind, data) для DXF, чтобы не дублировать расчёты


def svg_dims():
    out = []
    for d in DIMS:
        if d["kind"] in ("h", "v"):
            (x1, y1), (x2, y2), at = d["p1"], d["p2"], d["at"]
            if d["kind"] == "h":
                a, b = (x1, at), (x2, at)
                for (px, py), (qx, qy) in (((x1, y1), a), ((x2, y2), b)):
                    if not d.get("noext"):
                        sg = 1 if qy > py else -1
                        out.append(f'<line x1="{fmt_n(px)}" y1="{fmt_n(py)}" x2="{fmt_n(qx)}" y2="{fmt_n(qy + sg * 2)}" class="t"/>')
                ang = 0
            else:
                a, b = (at, y1), (at, y2)
                for (px, py), (qx, qy) in (((x1, y1), a), ((x2, y2), b)):
                    if not d.get("noext") and not d.get("inside"):
                        sg = 1 if qx > px else -1
                        out.append(f'<line x1="{fmt_n(px)}" y1="{fmt_n(py)}" x2="{fmt_n(qx + sg * 2)}" y2="{fmt_n(qy)}" class="t"/>')
                ang = math.pi / 2
            Lh = math.dist(a, b)
            outside = Lh < 9
            ext = 7 if outside else 0
            ux, uy = (b[0] - a[0]) / Lh, (b[1] - a[1]) / Lh
            A0 = (a[0] - ux * ext, a[1] - uy * ext)
            B0 = (b[0] + ux * ext, b[1] + uy * ext)
            out.append(f'<line x1="{fmt_n(A0[0])}" y1="{fmt_n(A0[1])}" x2="{fmt_n(B0[0])}" y2="{fmt_n(B0[1])}" class="t"/>')
            th = math.atan2(uy, ux)
            for tip, an in ((a, th + math.pi if not outside else th), (b, th if not outside else th + math.pi)):
                out.append(arrow(tip, an)[0])
            tp = d.get("tpos", 0.5)
            mx, my = a[0] + (b[0] - a[0]) * tp, a[1] + (b[1] - a[1]) * tp
            h = 3.5 if not d.get("small") else 3.0
            if d["kind"] == "h":
                t = dict(x=mx, y=my - 0.9, s=d["txt"], h=h, anchor="middle", rot=0)
            else:
                t = dict(x=mx - 0.9, y=my, s=d["txt"], h=h, anchor="middle", rot=-90)
            if d.get("inside"):
                wbox = len(d["txt"]) * h * 0.62 + 1.2
                out.append(f'<rect x="{fmt_n(mx - 0.9 - h * 1.12)}" y="{fmt_n(my - wbox / 2)}" width="{fmt_n(h * 1.12)}" height="{fmt_n(wbox)}" class="mask"/>')
            out.append(svg_text(t))
        elif d["kind"] == "diam":
            (cx, cy), r, ang = d["p1"], d["p2"], d["at"]
            ca, sa = math.cos(ang), -math.sin(ang)
            p_far = (cx - r * ca, cy - r * sa) if not d.get("half") else (cx, cy)
            p_near = (cx + r * ca, cy + r * sa)
            L = d.get("shelf", 10)
            ext = (cx + (r + 8) * ca, cy + (r + 8) * sa)
            out.append(f'<polyline points="{fmt_n(p_far[0])},{fmt_n(p_far[1])} {fmt_n(ext[0])},{fmt_n(ext[1])} {fmt_n(ext[0] + (L if ca >= 0 else -L))},{fmt_n(ext[1])}" class="t" fill="none"/>')
            out.append(arrow(p_near, math.atan2(sa, ca))[0])
            if not d.get("half"):
                out.append(arrow(p_far, math.atan2(-sa, -ca))[0])
            tx = ext[0] + (L / 2 if ca >= 0 else -L / 2)
            out.append(svg_text(dict(x=tx, y=ext[1] - 0.9, s=d["txt"], h=3.5, anchor="middle", rot=0)))
    for ld in LEADERS:
        if ld["kind"] == "pos":
            (ax, ay), (sx, sy) = ld["at"], ld["to"]
            L = 7
            left = sx < ax
            x_end = sx - L if left else sx + L
            out.append(f'<circle cx="{fmt_n(ax)}" cy="{fmt_n(ay)}" r="0.55" class="dot"/>')
            out.append(f'<polyline points="{fmt_n(ax)},{fmt_n(ay)} {fmt_n(sx)},{fmt_n(sy)} {fmt_n(x_end)},{fmt_n(sy)}" class="t" fill="none"/>')
            out.append(svg_text(dict(x=(sx + x_end) / 2, y=sy - 1.0, s=ld["txt"], h=5, anchor="middle", rot=0)))
        elif ld["kind"] == "note":
            (ax, ay), (sx, sy) = ld["at"], ld["to"]
            L = len(ld["txt"]) * 2.1
            ang = math.atan2(ay - sy, ax - sx)
            out.append(f'<polyline points="{fmt_n(ax)},{fmt_n(ay)} {fmt_n(sx)},{fmt_n(sy)} {fmt_n(sx + L)},{fmt_n(sy)}" class="t" fill="none"/>')
            out.append(arrow((ax, ay), ang)[0])
            out.append(svg_text(dict(x=sx + L / 2, y=sy - 0.9, s=ld["txt"], h=3.5, anchor="middle", rot=0)))
        elif ld["kind"] == "cutarrow":
            (x, y) = ld["at"]
            out.append(f'<line x1="{fmt_n(x - 1)}" y1="{fmt_n(y)}" x2="{fmt_n(x - 7)}" y2="{fmt_n(y)}" class="t"/>')
            out.append(arrow((x - 7.5, y), math.pi, L=3.5, W=1.1)[0])
    return out


def path_d(pts, closed=False):
    s = "M" + " L".join(f"{fmt_n(x)},{fmt_n(y)}" for x, y in pts)
    return s + (" Z" if closed else "")


def build_svg():
    by = {}
    for p in POLYS:
        by.setdefault(p["layer"], []).append(path_d(p["pts"], p["closed"]))
    pats = []
    for name, ang in (("h45", -45), ("h135", 45)):
        for sp in (1.0, 1.2, 1.4, 2.0):
            pats.append(f'<pattern id="{name}_{sp}" patternUnits="userSpaceOnUse" width="{sp}" height="{sp}" patternTransform="rotate({ang})">'
                        f'<line x1="0" y1="0" x2="0" y2="{sp}" stroke="#111" stroke-width="0.16"/></pattern>')
    for sp in (1.2,):
        pats.append(f'<pattern id="cross_{sp}" patternUnits="userSpaceOnUse" width="{sp}" height="{sp}" patternTransform="rotate(45)">'
                    f'<path d="M0,0 V{sp} M0,0 H{sp}" stroke="#111" stroke-width="0.14"/></pattern>')
    hatch = [f'<path d="{" ".join(path_d(lp, True) for lp in h["loops"])}" fill="url(#{h["pat"]}_{h["sp"]})" fill-rule="evenodd"/>' for h in HATCH]
    body = []
    body += hatch
    for lay, ds in by.items():
        dash = f' stroke-dasharray="{DASH[lay]}"' if lay in DASH else ""
        body.append(f'<path d="{" ".join(ds)}" fill="none" stroke="#111" stroke-width="{STROKE[lay]}"{dash} stroke-linecap="round" stroke-linejoin="round"/>')
    body += svg_dims()
    body += [svg_text(t) for t in TEXTS if t["s"]]
    css = ("text{font-family:'GOST type B','GOST Type BU','ISOCPEUR','Arial Narrow',sans-serif;fill:#111;}"
           ".t{stroke:#111;stroke-width:0.18}.ar{fill:#111;stroke:none}.dot{fill:#111}.mask{fill:#fff}")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297">'
            f'<defs><style>@font-face{{font-family:"GOST type B";src:url("fonts/GOST_BU.ttf")}}{css}</style>{"".join(pats)}</defs>'
            f'<rect width="420" height="297" fill="#fff"/>{"".join(body)}</svg>')


svg = build_svg()
(OUT / "drawing_A3.svg").write_text(svg, encoding="utf-8")
(OUT / "drawing_sheet.html").write_text(
    '<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#fff}'
    'img,svg{display:block;width:100vw;height:100vh}</style></head><body>' + svg +
    '<script>document.fonts.ready.then(()=>requestAnimationFrame(()=>document.body.dataset.ready="1"))</script></body></html>',
    encoding="utf-8")
print("SVG ok")

# ============================================================== ВЫВОД DXF
doc = ezdxf.new("R2010", setup=True)
doc.units = ezdxf.units.MM
doc.styles.add("GOST", font="GOST_BU.ttf")
for nm, col, lw, lt in (("VIS", 7, 50, "CONTINUOUS"), ("THIN", 7, 18, "CONTINUOUS"), ("AXIS", 1, 18, "CENTER"),
                        ("HATCH", 8, 13, "CONTINUOUS"), ("DIM", 3, 18, "CONTINUOUS"), ("TEXT", 7, 25, "CONTINUOUS"),
                        ("FRAME", 7, 60, "CONTINUOUS"), ("CUT", 7, 90, "CONTINUOUS")):
    doc.layers.add(nm, color=col, lineweight=lw, linetype=lt)
msp = doc.modelspace()
Y = lambda y: SH - y  # noqa: E731  (DXF: ось Y вверх)
LAY = {"vis": "VIS", "vis_iso": "VIS", "thin": "THIN", "axis": "AXIS", "hid": "THIN", "frame": "FRAME", "trim": "THIN", "cut": "CUT"}
for p in POLYS:
    msp.add_lwpolyline([(x, Y(y)) for x, y in p["pts"]], close=p["closed"], dxfattribs={"layer": LAY[p["layer"]], "ltscale": 0.4} if p["layer"] == "axis" else {"layer": LAY[p["layer"]]})
for h in HATCH:
    hh = msp.add_hatch(dxfattribs={"layer": "HATCH"})
    ang = 45 if h["pat"] == "h45" else 135
    if h["pat"] == "cross":
        hh.set_pattern_fill("ANSI37", scale=h["sp"] / 3.175 * 1.2, angle=0)
    else:
        hh.set_pattern_fill("ANSI31", scale=h["sp"] / 3.175, angle=ang - 45)
    for lp in h["loops"]:
        hh.paths.add_polyline_path([(x, Y(y)) for x, y in lp], is_closed=True)
for t in TEXTS:
    if not t["s"]:
        continue
    e = msp.add_text(t["s"].replace("⌀", "%%c"), height=t["h"], rotation=-t["rot"], dxfattribs={"layer": "TEXT", "style": "GOST", "width": 0.9, "oblique": 15})
    al = {"start": TextEntityAlignment.BOTTOM_LEFT, "middle": TextEntityAlignment.BOTTOM_CENTER}[t["anchor"]]
    e.set_placement((t["x"], Y(t["y"])), align=al)

ds = doc.dimstyles.new("ESKD")
ds.dxf.dimtxsty = "GOST"
ds.dxf.dimtxt = 3.5
ds.dxf.dimasz = 2.8
ds.dxf.dimexe = 2.0
ds.dxf.dimexo = 0.0
ds.dxf.dimgap = 0.8
ds.dxf.dimtad = 1
ds.dxf.dimtih = 0
ds.dxf.dimtoh = 0
ds.dxf.dimdec = 1
ds.dxf.dimdsep = ord(",")
ds.dxf.dimlfac = 1 / S
ds.dxf.dimclrd = 3
ds.dxf.dimclre = 3
for d in DIMS:
    txt = d["txt"].replace("⌀", "%%c")
    if d["kind"] in ("h", "v"):
        (x1, y1), (x2, y2), at = d["p1"], d["p2"], d["at"]
        if d["kind"] == "h":
            base, ang = (x1, Y(at)), 0
        else:
            base, ang = (at, Y(y1)), 90
        ov = {"dimse1": 1, "dimse2": 1} if d.get("inside") or d.get("noext") else {}
        dm = msp.add_linear_dim(base=base, p1=(x1, Y(y1)), p2=(x2, Y(y2)), angle=ang, text=txt,
                                dimstyle="ESKD", override=ov, dxfattribs={"layer": "DIM"})
        dm.render()
    elif d["kind"] == "diam":
        (cx, cy), r, ang = d["p1"], d["p2"], d["at"]
        if d.get("half"):
            dm = msp.add_radius_dim(center=(cx, Y(cy)), radius=r, angle=math.degrees(ang), text=txt, dimstyle="ESKD",
                                    dxfattribs={"layer": "DIM"})
        else:
            dm = msp.add_diameter_dim(center=(cx, Y(cy)), radius=r, angle=math.degrees(ang), text=txt, dimstyle="ESKD",
                                      dxfattribs={"layer": "DIM"})
        dm.render()
for ld in LEADERS:
    if ld["kind"] == "pos":
        (ax, ay), (sx, sy) = ld["at"], ld["to"]
        x_end = sx - 7 if sx < ax else sx + 7
        msp.add_lwpolyline([(ax, Y(ay)), (sx, Y(sy)), (x_end, Y(sy))], dxfattribs={"layer": "THIN"})
        msp.add_circle((ax, Y(ay)), 0.55, dxfattribs={"layer": "THIN"})
        msp.add_text(ld["txt"], height=5, dxfattribs={"layer": "TEXT", "style": "GOST"}).set_placement(
            ((sx + x_end) / 2, Y(sy) + 1.0), align=TextEntityAlignment.BOTTOM_CENTER)
    elif ld["kind"] == "note":
        (ax, ay), (sx, sy) = ld["at"], ld["to"]
        L = len(ld["txt"]) * 2.1
        msp.add_leader([(ax, Y(ay)), (sx, Y(sy)), (sx + L, Y(sy))], dimstyle="ESKD", dxfattribs={"layer": "DIM"})
        msp.add_text(ld["txt"].replace("⌀", "%%c"), height=3.5, dxfattribs={"layer": "TEXT", "style": "GOST"}).set_placement(
            (sx + L / 2, Y(sy) + 0.9), align=TextEntityAlignment.BOTTOM_CENTER)
    elif ld["kind"] == "cutarrow":
        (x, y) = ld["at"]
        msp.add_leader([(x - 7.5, Y(y)), (x - 1, Y(y))], dimstyle="ESKD", dxfattribs={"layer": "THIN"})
doc.saveas(OUT / "drawing_A3.dxf")
print("DXF ok")
