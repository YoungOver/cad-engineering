"""Узел приводного вала (корпус подшипниковый с зубчатым колесом) — параметрическая модель CadQuery.

Система координат: ось вала = ось X, Z вверх, ось вала на высоте H над опорной плоскостью
(в модели ось проходит через 0, опорная плоскость основания на z = -H).

Запуск:  python model.py   ->  assembly.step, parts/*.step|*.stl, render_data.json, bom.json
"""
import base64
import json
import math
from pathlib import Path

import cadquery as cq
import numpy as np

OUT = Path(__file__).parent

# ------------------------------------------------------------------ параметры, мм
H = 85.0            # высота оси вала
BASE_L, BASE_W, BASE_T = 120.0, 170.0, 16.0
FOOT_HOLE_D, FOOT_X, FOOT_Y, SPOT_D = 14.0, 40.0, 68.0, 24.0
TUBE_D, FLANGE_D = 92.0, 110.0
X_FACE = 46.0       # торцы корпуса
X_FL = 34.0         # начало фланца
BORE_D = 62.0       # под подшипник 206 (D = 62)
PCD = 84.0          # окружность крепёжных отверстий крышек
BOSS_H = 10.0       # прилив под маслёнку над трубой
N_BOLT = 6
TAP_D = 6.8         # сверло под М8
BRG_d, BRG_D, BRG_B = 30.0, 62.0, 16.0
BRG_X = 24.0        # внутренний торец подшипника
COVER_SPIGOT = 6.0
COVER_T = 10.0
# зубчатое колесо
M, Z, ALPHA = 2.5, 40, math.radians(20)
GEAR_B = 30.0
GEAR_HUB_D, GEAR_HUB_L = 45.0, 40.0
X_GEAR0 = 64.0      # заплечик вала под ступицу
X_GEAR_C = X_GEAR0 + GEAR_HUB_L / 2
SHAFT_END = 102.0


def cyl_x(d, x0, x1):
    """Сплошной цилиндр вдоль X от x0 до x1."""
    return cq.Workplane("YZ").workplane(offset=x0).circle(d / 2).extrude(x1 - x0)


def ring_x(d_out, d_in, x0, x1):
    return cq.Workplane("YZ").workplane(offset=x0).circle(d_out / 2).circle(d_in / 2).extrude(x1 - x0)


def polar(r, deg):
    a = math.radians(deg)
    return (r * math.cos(a), r * math.sin(a))


BOLT_ANGLES = [90 + 60 * k for k in range(N_BOLT)]


def try_fillet(wp, sel, r):
    try:
        res = wp.edges(sel).fillet(r)
        if res.val().isValid():
            return res
    except Exception as e:  # noqa: BLE001
        print("  fillet skipped:", r, e.__class__.__name__)
    return wp


# ------------------------------------------------------------------ детали
def housing(tap_d=TAP_D):
    base = cq.Workplane("XY").box(BASE_L, BASE_W, BASE_T, centered=(True, True, False)).translate((0, 0, -H))
    base = base.edges("|Z").fillet(10)
    zt = -H + BASE_T
    ped = (cq.Workplane("YZ").workplane(offset=-40)
           .polyline([(-56, zt), (56, zt), (30, 0), (-30, 0)]).close().extrude(80))
    tube = cyl_x(TUBE_D, -X_FL, X_FL)
    fl = cyl_x(FLANGE_D, -X_FACE, -X_FL).union(cyl_x(FLANGE_D, X_FL, X_FACE))
    boss = cq.Workplane("XY").circle(11).extrude(TUBE_D / 2 + BOSS_H)
    body = base.union(ped).union(tube).union(fl).union(boss)
    # литейные галтели: пьедестал — основание
    body = try_fillet(body, cq.selectors.BoxSelector((-41, -57, zt - 0.5), (41, 57, zt + 0.5)), 5)
    # галтель пьедестал — труба
    body = try_fillet(body, cq.selectors.BoxSelector((-40.5, -46.5, -46), (40.5, 46.5, -1)), 4)
    # полость (облегчение) снизу
    cav = (cq.Workplane("XY").workplane(offset=-H - 1).rect(60, 70).extrude(H - 36))
    cav = cav.edges("|Z").fillet(8)
    body = body.cut(cav)
    # расточки
    body = body.cut(cyl_x(BORE_D, -X_FACE - 1, X_FACE + 1)).cut(cyl_x(68, -BRG_X, BRG_X))
    # отверстие под маслёнку
    body = body.cut(cq.Workplane("XY").workplane(offset=20).circle(4.25).extrude(40))
    # резьбовые отверстия М8 под крышки
    for s in (-1, 1):
        for a in BOLT_ANGLES:
            y, z = polar(PCD / 2, a)
            x0 = s * X_FACE
            h = cyl_x(tap_d, min(x0, x0 - s * 16), max(x0, x0 - s * 16)).translate((0, y, z))
            body = body.cut(h)
    # крепёжные отверстия лап + цековки
    for sx in (-1, 1):
        for sy in (-1, 1):
            p = (sx * FOOT_X, sy * FOOT_Y)
            body = body.cut(cq.Workplane("XY").workplane(offset=-H - 1).center(*p).circle(FOOT_HOLE_D / 2).extrude(BASE_T + 2))
            body = body.cut(cq.Workplane("XY").workplane(offset=zt - 1).center(*p).circle(SPOT_D / 2).extrude(2))
    return body


def cover(through):
    """Крышка подшипника; внутренний торец пояска на x=0, фланец наружу (+X)."""
    c = cyl_x(BORE_D, 0, COVER_SPIGOT).union(cyl_x(FLANGE_D, COVER_SPIGOT, COVER_SPIGOT + COVER_T))
    c = c.faces(">X").edges().chamfer(1.5)
    c = try_fillet(c, cq.selectors.NearestToPointSelector((COVER_SPIGOT, 0, BORE_D / 2)), 1.0)
    for a in BOLT_ANGLES:
        y, z = polar(PCD / 2, a)
        c = c.cut(cyl_x(9, COVER_SPIGOT - 1, COVER_SPIGOT + COVER_T + 1).translate((0, y, z)))
    xo = COVER_SPIGOT + COVER_T
    if through:
        c = c.cut(cyl_x(31, -1, xo + 1)).cut(cyl_x(52, COVER_SPIGOT, xo + 1))
    else:
        c = c.cut(cyl_x(44, -1, 4))
        # выступ-прилив на наружном торце (литейный знак)
        c = c.union(cyl_x(40, xo, xo + 2).faces(">X").edges().chamfer(0.8))
    return c


def shaft():
    pts = [(-42, 0), (-42, 15), (-BRG_X, 15), (-BRG_X, 18), (BRG_X, 18), (BRG_X, 15),
           (X_GEAR0, 15), (X_GEAR0, 12.5), (SHAFT_END, 12.5), (SHAFT_END, 0)]
    s = cq.Workplane("XY").polyline(pts).close().revolve(360, (0, 0, 0), (1, 0, 0))
    for p in [(-42, 0, 15), (SHAFT_END, 0, 12.5), (-BRG_X, 0, 18), (BRG_X, 0, 18)]:
        s = s.edges(cq.selectors.NearestToPointSelector(p)).chamfer(1.0)
    # шпоночный паз 8x4, l=28
    kw = cq.Workplane("XY").workplane(offset=12.5 - 4).center(X_GEAR_C, 0).slot2D(28, 8).extrude(10)
    s = s.cut(kw)
    # резьбовое отверстие М8 в торце
    s = s.cut(cyl_x(TAP_D, SHAFT_END - 18, SHAFT_END + 1))
    return s


def gear_outline():
    """Эвольвентный профиль (u,v) в плоскости YZ; зуб на 90° (сверху)."""
    r = M * Z / 2
    rb = r * math.cos(ALPHA)
    ra = r + M
    rf = r - 1.25 * M
    inv = lambda a: math.tan(a) - a  # noqa: E731
    half0 = math.pi / (2 * Z) + inv(ALPHA)

    def psi(R):
        R = max(R, rb)
        return half0 - inv(math.acos(rb / R))

    step = 2 * math.pi / Z
    wp = cq.Workplane("YZ").workplane(offset=X_GEAR_C - GEAR_B / 2)
    radii = np.linspace(rb, ra, 7)
    first = True
    for k in range(Z):
        c = math.pi / 2 + k * step
        # правый бок (меньший угол)
        a0 = c - psi(rb)
        p_root = (rf * math.cos(a0), rf * math.sin(a0))
        if first:
            wp = wp.moveTo(*p_root)
            first = False
        else:
            # дуга впадины от предыдущего зуба
            prev = c - step + psi(rb)
            am = (prev + a0) / 2
            wp = wp.threePointArc((rf * math.cos(am), rf * math.sin(am)), p_root)
        wp = wp.lineTo(rb * math.cos(a0), rb * math.sin(a0))
        fl = [(R * math.cos(c - psi(R)), R * math.sin(c - psi(R))) for R in radii[1:]]
        wp = wp.spline(fl, includeCurrent=True)
        am = c
        wp = wp.threePointArc((ra * math.cos(am), ra * math.sin(am)),
                              (ra * math.cos(c + psi(ra)), ra * math.sin(c + psi(ra))))
        fl = [(R * math.cos(c + psi(R)), R * math.sin(c + psi(R))) for R in radii[::-1][1:]]
        wp = wp.spline(fl, includeCurrent=True)
        a1 = c + psi(rb)
        wp = wp.lineTo(rf * math.cos(a1), rf * math.sin(a1))
    # замыкающая дуга впадины
    c0 = math.pi / 2
    a_end = c0 - psi(rb) + 2 * math.pi
    a_start = c0 + (Z - 1) * step + psi(rb)
    am = (a_start + a_end) / 2
    wp = wp.threePointArc((rf * math.cos(am), rf * math.sin(am)),
                          (rf * math.cos(a_end), rf * math.sin(a_end)))
    return wp.close(), rf, r, ra


def gear():
    wp, rf, r, ra = gear_outline()
    g = wp.extrude(GEAR_B)
    x0, x1 = X_GEAR_C - GEAR_B / 2, X_GEAR_C + GEAR_B / 2
    g = g.union(cyl_x(GEAR_HUB_D, X_GEAR0, X_GEAR0 + GEAR_HUB_L))
    web = 12.0
    g = g.cut(ring_x(80, GEAR_HUB_D + 0.01, x0 - 1, X_GEAR_C - web / 2))
    g = g.cut(ring_x(80, GEAR_HUB_D + 0.01, X_GEAR_C + web / 2, x1 + 1))
    for k in range(6):
        y, z = polar(31.5, 60 * k)
        g = g.cut(cyl_x(13, x0, x1).translate((0, y, z)))
    g = g.cut(cyl_x(25, X_GEAR0 - 1, X_GEAR0 + GEAR_HUB_L + 1))
    g = g.cut(cq.Workplane("XY").box(GEAR_HUB_L + 2, 8, 15.8, centered=(True, True, False)).translate((X_GEAR_C, 0, 0)))
    for x in (X_GEAR0, X_GEAR0 + GEAR_HUB_L):
        g = try_fillet(g, cq.selectors.NearestToPointSelector((x, 0, -GEAR_HUB_D / 2)), 1.0)
    return g, rf, r, ra


def key():
    return cq.Workplane("XY").workplane(offset=12.5 - 4).center(X_GEAR_C, 0).slot2D(28, 8).extrude(7).edges("|Z or >Z").chamfer(0.3)


def end_washer():
    w = cyl_x(40, 0, 6).faces(">X").edges().chamfer(1.0)
    return w.cut(cyl_x(9, -1, 7)).translate((X_GEAR0 + GEAR_HUB_L, 0, 0))


def bolt_m8(length=20.0):
    """Болт М8 ГОСТ 7798: опорный торец головки на x=0, головка в -X, стержень в +X."""
    s, k = 13.0, 5.3
    hexa = cq.Workplane("YZ").workplane(offset=-k).polygon(6, s / math.cos(math.pi / 6)).extrude(k)
    ch = cyl_x(s / math.cos(math.pi / 6), -k, 0).faces("<X").edges().chamfer(0.75, 1.2)
    head = hexa.intersect(ch)
    shank = cyl_x(8, 0, length).faces(">X").edges().chamfer(0.8)
    return head.union(shank)


def seal():
    """Манжета 1.1-30x52: упрощённый профиль (металлический каркас + рабочая кромка)."""
    pr = [(0, 26), (10, 26), (10, 20.5), (8.8, 20.5), (8.8, 24.2), (1.4, 24.2), (1.4, 21),
          (6.5, 16.2), (8.2, 15), (5.2, 15), (0, 18.2)]
    return cq.Workplane("XY").polyline(pr).close().revolve(360, (0, 0, 0), (1, 0, 0))


def bearing_parts():
    """Подшипник 206: наружное кольцо, внутреннее кольцо, тела качения (x = 0..B)."""
    B, pc, rb = BRG_B, 23.0, 4.76
    tor = cq.Workplane().add(cq.Solid.makeTorus(pc, rb * 1.02, cq.Vector(B / 2, 0, 0), cq.Vector(1, 0, 0)))
    outer = ring_x(BRG_D, 53, 0, B)
    outer = try_fillet(outer, cq.selectors.RadiusNthSelector(1), 0.8).cut(tor)
    inner = ring_x(39, BRG_d, 0, B)
    inner = try_fillet(inner, cq.selectors.RadiusNthSelector(0), 0.8).cut(tor)
    balls = None
    for k in range(10):
        y, z = polar(pc, 90 + 36 * k)
        b = cq.Workplane().add(cq.Solid.makeSphere(rb, cq.Vector(B / 2, y, z), angleDegrees1=-90, angleDegrees2=90))
        balls = b if balls is None else balls.union(b)
    return outer, inner, balls


# ------------------------------------------------------------------ сборка
def rot_z180(wp):
    return wp.rotate((0, 0, 0), (0, 0, 1), 180)


POS = {
    1: dict(code="АИ.301.001.01", name="Корпус", mat="СЧ20 ГОСТ 1412-85", rho=7.2, qty=1),
    2: dict(code="АИ.301.001.02", name="Вал", mat="Сталь 45 ГОСТ 1050-2013", rho=7.85, qty=1),
    3: dict(code="АИ.301.001.03", name="Колесо зубчатое", mat="Сталь 40Х ГОСТ 4543-2016", rho=7.85, qty=1, note="m=2,5; z=40"),
    4: dict(code="АИ.301.001.04", name="Крышка глухая", mat="СЧ15 ГОСТ 1412-85", rho=7.2, qty=1),
    5: dict(code="АИ.301.001.05", name="Крышка сквозная", mat="СЧ15 ГОСТ 1412-85", rho=7.2, qty=1),
    6: dict(code="АИ.301.001.06", name="Шайба концевая", mat="Ст3 ГОСТ 380-2005", rho=7.85, qty=1),
    7: dict(code="", name="Болт М8-6gx20.58 ГОСТ 7798-70", mat="", rho=7.85, qty=13),
    8: dict(code="", name="Манжета 1.1-30x52-1 ГОСТ 8752-79", mat="", rho=1.3, qty=1),
    9: dict(code="", name="Подшипник 206 ГОСТ 8338-75", mat="", rho=None, qty=2, mass=0.20),
    10: dict(code="", name="Шпонка 8x7x28 ГОСТ 23360-78", mat="", rho=7.85, qty=1),
}


def build(tap_d=TAP_D):
    """Возвращает список экземпляров: dict(pos, part, shape, mat, sub, explode)."""
    inst = []

    def add(pos, part, wp, mat, explode=(0, 0, 0), sub=None, section=True):
        inst.append(dict(pos=pos, part=part, wp=wp, mat=mat, explode=explode, sub=sub, section=section))

    add(1, "korpus", housing(tap_d), "paint", (0, 0, 0))
    UP = 150.0
    add(2, "val", shaft(), "steel", (0, 0, UP), section=False)
    g, *_ = gear()
    add(3, "koleso", g, "steel2", (150, 0, UP))
    add(10, "shponka", key(), "steel", (0, 0, UP + 34), section=False)
    add(6, "shaiba", end_washer(), "steel", (215, 0, UP))
    b = bolt_m8()
    add(7, "bolt", rot_z180(b).translate((SHAFT_END + 8, 0, 0)), "black", (255, 0, UP), sub="end", section=False)
    # подшипники
    o, i, balls = bearing_parts()
    for s, ex in ((1, 100), (-1, -75)):
        for nm, w, mat in (("outer", o, "chrome"), ("inner", i, "chrome"), ("balls", balls, "chrome")):
            wp = w if s > 0 else rot_z180(w)
            wp = wp.translate((s * BRG_X, 0, 0)) if s > 0 else wp.translate((-BRG_X, 0, 0))
            add(9, "podshipnik_206", wp, mat, (ex, 0, UP), sub=nm, section=(nm != "balls"))
    # крышки
    xc = X_FACE - COVER_SPIGOT  # 40
    add(4, "kryshka_glukhaya", rot_z180(cover(False)).translate((-xc, 0, 0)), "paint", (-105, 0, 0))
    add(5, "kryshka_skvoznaya", cover(True).translate((xc, 0, 0)), "paint", (105, 0, 0))
    add(8, "manzheta", seal().translate((X_FACE, 0, 0)), "rubber", (150, 0, 0))
    xo = X_FACE + COVER_T
    for s in (-1, 1):
        for a in BOLT_ANGLES:
            y, z = polar(PCD / 2, a)
            w = b if s < 0 else rot_z180(b)
            w = w.translate((s * xo, y, z))
            add(7, "bolt", w, "black", (s * 215, 0, 0), section=False)
    return inst


def mass_table(inst):
    m = {}
    for it in inst:
        p = POS[it["pos"]]
        if p.get("rho") is None:
            continue
        m[it["pos"]] = m.get(it["pos"], 0) + it["wp"].val().Volume() * p["rho"] * 1e-6
    m[9] = POS[9]["mass"] * 2
    return m


# ------------------------------------------------------------------ экспорт
def is_machined(f, is_cover=False):
    """Для окрашенных литых деталей: обработанные поверхности (торцы, расточки, отверстия, опорная плоскость)."""
    gt = f.geomType()
    c = f.Center()
    if gt == "PLANE":
        n = f.normalAt()
        if abs(n.x) > 0.99:
            return abs(c.x) < X_FACE + COVER_T - 0.5 if is_cover else abs(abs(c.x) - X_FACE) < 0.05
        if abs(n.z) > 0.99:
            return (abs(c.z + H) < 0.01 or (abs(c.z + H - BASE_T + 1) < 0.01 and f.Area() < 500)
                    or abs(c.z - TUBE_D / 2 - BOSS_H) < 0.01)
        return False
    if gt == "CYLINDER":
        try:
            r = f._geomAdaptor().Cylinder().Radius()
            u0, u1, _, _ = f._uvBounds()
        except Exception:  # noqa: BLE001
            return False
        full = (u1 - u0) > 6.2
        return full and any(abs(r - m) < 0.05 for m in (3.4, 4.25, 4.5, 7, 12, 15.5, 22, 26, 31, 34))
    return False


def tess(shape, tol=0.04, ang=0.12, split=False, is_cover=False):
    """Тесселяция по граням; при split=True — второй массив индексов для обработанных граней."""
    V, T, T2 = [], [], []
    off = 0
    for f in shape.Faces():
        vs, tris = f.tessellate(tol, ang)
        if not tris:
            continue
        V += [(p.x, p.y, p.z) for p in vs]
        idx = [i + off for tr in tris for i in tr]
        (T2 if split and is_machined(f, is_cover) else T).extend(idx)
        off += len(vs)
    return (np.array(V, dtype=np.float32), np.array(T, dtype=np.uint32), np.array(T2, dtype=np.uint32))


def feature_edges(shape, defl=0.05):
    from OCP.GCPnts import GCPnts_QuasiUniformDeflection
    segs = []
    for e in shape.Edges():
        if e.geomType() == "LINE" and e.Length() < 1e-6:
            continue
        try:
            c = e._geomAdaptor()
            pts = GCPnts_QuasiUniformDeflection(c, defl, c.FirstParameter(), c.LastParameter())
            P = [pts.Value(k + 1) for k in range(pts.NbPoints())]
        except Exception:  # noqa: BLE001
            continue
        for a, bpt in zip(P, P[1:]):
            segs += [a.X(), a.Y(), a.Z(), bpt.X(), bpt.Y(), bpt.Z()]
    return np.array(segs, dtype=np.float32)


def b64(a):
    return base64.b64encode(a.tobytes()).decode()


COLORS = {"paint": (0.23, 0.30, 0.38), "steel": (0.75, 0.76, 0.78), "steel2": (0.70, 0.71, 0.73),
          "black": (0.12, 0.12, 0.13), "chrome": (0.85, 0.86, 0.88), "rubber": (0.08, 0.08, 0.08)}


def main():
    inst = build()
    (OUT / "parts").mkdir(exist_ok=True)
    assy = cq.Assembly(name="uzel_privodnogo_vala")
    counters = {}
    for it in inst:
        k = f"{it['pos']:02d}_{it['part']}" + (f"_{it['sub']}" if it["sub"] and it['pos'] == 9 else "")
        counters[k] = counters.get(k, 0) + 1
        assy.add(it["wp"].val(), name=f"{k}_{counters[k]}", color=cq.Color(*COLORS[it["mat"]]))
    assy.export(str(OUT / "assembly.step"))
    # уникальные детали — в своей СК
    uniq = {"01_korpus": housing(), "02_val": shaft(), "03_koleso_zubchatoe": gear()[0],
            "04_kryshka_glukhaya": cover(False), "05_kryshka_skvoznaya": cover(True),
            "06_shaiba_koncevaya": end_washer(), "07_bolt_M8x20": bolt_m8(), "08_manzheta_30x52": seal(),
            "10_shponka_8x7x28": key()}
    o, i, balls = bearing_parts()
    uniq["09_podshipnik_206"] = cq.Workplane().add(cq.Compound.makeCompound([o.val(), i.val(), balls.val()]))
    for nm, wp in uniq.items():
        cq.exporters.export(wp, str(OUT / "parts" / f"{nm}.stl"), tolerance=0.03, angularTolerance=0.1)
        cq.exporters.export(wp, str(OUT / "parts" / f"{nm}.step"))
    # данные для рендера
    data = []
    for it in inst:
        shp = it["wp"].val()
        v, t, t2 = tess(shp, split=it["mat"] == "paint", is_cover=it["pos"] in (4, 5))
        e = feature_edges(shp)
        bb = shp.BoundingBox()
        data.append(dict(pos=it["pos"], part=it["part"], sub=it["sub"], mat=it["mat"], explode=it["explode"],
                         v=b64(v), t=b64(t), t2=b64(t2), e=b64(e),
                         c=[(bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, (bb.zmin + bb.zmax) / 2],
                         bb=[bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax]))
    (OUT / "render_data.json").write_text(json.dumps(data))
    m = mass_table(inst)
    total = sum(m.values())
    bom = {str(k): dict(POS[k], mass=round(m.get(k, 0), 3)) for k in POS}
    (OUT / "bom.json").write_text(json.dumps(dict(bom=bom, total_mass=round(total, 2)), ensure_ascii=False, indent=1), encoding="utf-8")
    for k in POS:
        print(f"{k:2d} {POS[k]['name']:<36} {m.get(k, 0):7.3f} кг")
    print(f"Итого масса: {total:.2f} кг; экземпляров: {len(inst)}")


if __name__ == "__main__":
    main()
