"""Планировочное решение 54 м² (SVG) + мудборд -> plan.html"""
K, OX, OY = 92, 130, 150  # px на метр, отступы
X = lambda m: OX + m * K
Y = lambda m: OY + m * K
o = []
add = o.append


def rect(x, y, w, h, **a):
    at = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
    add(f'<rect x="{X(x):.1f}" y="{Y(y):.1f}" width="{w * K:.1f}" height="{h * K:.1f}" {at}/>')


def line(x1, y1, x2, y2, **a):
    at = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
    add(f'<line x1="{X(x1):.1f}" y1="{Y(y1):.1f}" x2="{X(x2):.1f}" y2="{Y(y2):.1f}" {at}/>')


def text(x, y, s, size=15, **a):
    at = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in a.items())
    add(f'<text x="{X(x):.1f}" y="{Y(y):.1f}" font-size="{size}" {at}>{s}</text>')


# полы по зонам
FL = dict(fill='url(#oak)')
rect(0, 0, 5.4, 3.8, **FL); rect(5.4, 0, 3.6, 3.8, **FL); rect(6.2, 3.8, 2.8, 2.2, **FL)
rect(0, 3.8, 2.2, 2.2, fill='url(#tile)'); rect(2.2, 3.8, 4.0, 2.2, fill='url(#stone)')
# мебель
F = dict(fill='#fbf8f3', stroke='#3a3f45', stroke_width=1.4, rx=4)
rect(0.12, 0.3, 0.6, 2.9, **F)                      # кухня
add(f'<circle cx="{X(0.42)}" cy="{Y(0.9)}" r="16" fill="none" stroke="#3a3f45"/><circle cx="{X(0.42)}" cy="{Y(2.4)}" r="12" fill="none" stroke="#3a3f45"/>')
rect(0.3, 1.45, 0.24, 0.5, fill='none', stroke='#3a3f45', rx=3)   # мойка
add(f'<circle cx="{X(2.1)}" cy="{Y(1.9)}" r="{0.55 * K}" fill="#e9dccb" stroke="#3a3f45" stroke-width="1.4"/>')  # стол
for dx, dy in ((0, -0.8), (0, 0.8), (-0.8, 0), (0.8, 0)):
    add(f'<circle cx="{X(2.1 + dx)}" cy="{Y(1.9 + dy)}" r="{0.2 * K}" fill="#fbf8f3" stroke="#3a3f45" stroke-width="1.2"/>')
rect(4.45, 0.7, 0.85, 2.3, fill='#c7cfc4', stroke='#3a3f45', stroke_width=1.4, rx=10)   # диван
rect(4.45, 0.7, 0.28, 2.3, fill='#b3bdb0', stroke='#3a3f45', stroke_width=1.2, rx=8)
rect(3.55, 1.35, 0.6, 1.0, fill='#e9dccb', stroke='#3a3f45', stroke_width=1.2, rx=30)   # столик
add(f'<ellipse cx="{X(3.9)}" cy="{Y(1.85)}" rx="{1.2 * K}" ry="{0.95 * K}" fill="none" stroke="#b8612a" stroke-width="1" stroke-dasharray="4 5"/>')  # ковёр
rect(7.0, 1.0, 1.95, 1.6, fill='#fbf8f3', stroke='#3a3f45', stroke_width=1.4, rx=6)     # кровать
rect(8.5, 1.1, 0.4, 0.65, fill='#e9dccb', stroke='#3a3f45', stroke_width=1, rx=6); rect(8.5, 1.85, 0.4, 0.65, fill='#e9dccb', stroke='#3a3f45', stroke_width=1, rx=6)
line(7.9, 1.0, 7.9, 2.6, stroke='#3a3f45', stroke_width=1)
rect(8.45, 0.45, 0.5, 0.45, **F); rect(8.45, 2.7, 0.5, 0.45, **F)                         # тумбы
rect(5.47, 0.3, 0.6, 2.1, **F); line(5.47, 1.35, 6.07, 1.35, stroke='#3a3f45')            # шкаф
rect(0.07, 3.9, 0.72, 1.7, fill='#fbf8f3', stroke='#3a3f45', stroke_width=1.4, rx=18)     # ванна
add(f'<ellipse cx="{X(1.85)}" cy="{Y(5.55)}" rx="18" ry="24" fill="#fbf8f3" stroke="#3a3f45" stroke-width="1.4"/>')  # унитаз
rect(1.1, 3.88, 0.6, 0.42, **F)                                                            # раковина
rect(1.5, 5.25, 0.55, 0.6, fill='#fbf8f3', stroke='#3a3f45', stroke_width=1.2, rx=4) if False else None
rect(4.75, 5.4, 1.4, 0.55, **F); line(5.45, 5.4, 5.45, 5.95, stroke='#3a3f45')            # шкаф прихожей
rect(2.3, 5.45, 0.9, 0.45, fill='#e9dccb', stroke='#3a3f45', stroke_width=1.2, rx=4)       # банкетка
rect(7.55, 3.9, 1.38, 0.62, **F); add(f'<circle cx="{X(8.2)}" cy="{Y(4.85)}" r="17" fill="#c7cfc4" stroke="#3a3f45"/>')  # стол + кресло
rect(6.3, 5.5, 2.6, 0.42, **F)                                                            # стеллаж
for i in range(1, 5): line(6.3 + i * 0.52, 5.5, 6.3 + i * 0.52, 5.92, stroke='#3a3f45', stroke_width=1)
# стены: наружные 0.3 визуально, перегородки 0.12
W = dict(stroke='#1f2328', stroke_linecap='square')
add(f'<rect x="{X(0)}" y="{Y(0)}" width="{9 * K}" height="{6 * K}" fill="none" stroke="#1f2328" stroke-width="16"/>')
for (x1, y1, x2, y2) in [(5.4, 0, 5.4, 3.8), (0, 3.8, 2.4, 3.8), (3.4, 3.8, 5.6, 3.8), (6.4, 3.8, 9, 3.8),
                         (2.2, 3.8, 2.2, 4.2), (2.2, 4.95, 2.2, 6), (6.2, 3.8, 6.2, 4.15), (6.2, 4.95, 6.2, 6)]:
    line(x1, y1, x2, y2, stroke_width=8, **W)
# окна
for (x1, x2) in [(1.3, 3.0), (3.5, 4.9), (6.3, 8.1)]:
    add(f'<rect x="{X(x1)}" y="{Y(0) - 8}" width="{(x2 - x1) * K}" height="16" fill="#fff" stroke="#1f2328" stroke-width="1.4"/>')
    line(x1, 0, x2, 0, stroke='#1f2328', stroke_width=1)
add(f'<rect x="{X(9) - 8}" y="{Y(4.3)}" width="16" height="{1.2 * K}" fill="#fff" stroke="#1f2328" stroke-width="1.4"/>')
# двери (полотно + дуга)


def door(hx, hy, L, a0, sweep):
    import math
    ex, ey = hx + L * math.cos(math.radians(a0)), hy + L * math.sin(math.radians(a0))
    a1 = a0 + sweep
    fx, fy = hx + L * math.cos(math.radians(a1)), hy + L * math.sin(math.radians(a1))
    line(hx, hy, ex, ey, stroke='#1f2328', stroke_width=2.5)
    add(f'<path d="M{X(ex):.1f} {Y(ey):.1f} A{L * K:.1f} {L * K:.1f} 0 0 {1 if sweep > 0 else 0} {X(fx):.1f} {Y(fy):.1f}" fill="none" stroke="#1f2328" stroke-width="1" stroke-dasharray="3 4"/>')


add(f'<rect x="{X(3.55)}" y="{Y(6) - 9}" width="{0.9 * K}" height="18" fill="#fff"/>')
door(3.55, 6, 0.9, -90, 90)          # входная
door(5.6, 3.8, 0.8, -90, 90)         # спальня
door(2.2, 4.2, 0.75, 90, -90) if False else door(2.2, 4.95, 0.75, 180, 90)   # санузел
door(6.2, 4.15, 0.8, 0, 90)          # кабинет
# подписи помещений
T = dict(fill='#1f2328', font_family='Manrope', font_weight='700', text_anchor='middle')
S = dict(fill='#6a6f76', font_family='Manrope', text_anchor='middle')
for x, y, n, a in [(2.9, 3.3, 'Кухня-гостиная', '20,5'), (7.25, 3.3, 'Спальня', '13,7'), (1.35, 5.1, 'С/у', '4,8'),
                   (4.0, 4.75, 'Прихожая', '8,8'), (6.95, 4.75, 'Кабинет', '6,2')]:
    text(x, y, n, 17, **T); text(x, y + 0.26, f'{a} м²', 14, **S)
# размеры
D = dict(stroke='#6a6f76', stroke_width=1)


def hdim(x1, x2, y, s):
    line(x1, y, x2, y, **D)
    for xx in (x1, x2):
        line(xx, y - 0.08, xx, y + 0.08, **D)
        add(f'<line x1="{X(xx) - 5}" y1="{Y(y) + 5}" x2="{X(xx) + 5}" y2="{Y(y) - 5}" stroke="#1f2328" stroke-width="1.6"/>')
    text((x1 + x2) / 2, y - 0.08, s, 13, **S)


def vdim(y1, y2, x, s):
    line(x, y1, x, y2, **D)
    for yy in (y1, y2):
        line(x - 0.08, yy, x + 0.08, yy, **D)
        add(f'<line x1="{X(x) - 5}" y1="{Y(yy) + 5}" x2="{X(x) + 5}" y2="{Y(yy) - 5}" stroke="#1f2328" stroke-width="1.6"/>')
    add(f'<text x="{X(x) - 8:.1f}" y="{Y((y1 + y2) / 2):.1f}" font-size="13" fill="#6a6f76" font-family="Manrope" text-anchor="middle" transform="rotate(-90 {X(x) - 8:.1f} {Y((y1 + y2) / 2):.1f})">{s}</text>')


hdim(0, 5.4, -0.55, '5400'); hdim(5.4, 9, -0.55, '3600'); hdim(0, 9, -0.95, '9000')
vdim(0, 3.8, -0.55, '3800'); vdim(3.8, 6, -0.55, '2200'); vdim(0, 6, -0.95, '6000')
# север
add(f'<g transform="translate({X(9.55)},{Y(0.3)})"><circle r="22" fill="none" stroke="#1f2328"/><path d="M0 -18 L7 8 L0 3 L-7 8Z" fill="#1f2328"/><text y="-28" font-size="14" text-anchor="middle" font-family="Manrope" font-weight="700">С</text></g>')

svg = f'''<svg width="1060" height="860" viewBox="0 0 1060 860" xmlns="http://www.w3.org/2000/svg">
<defs>
<pattern id="oak" width="120" height="18" patternUnits="userSpaceOnUse"><rect width="120" height="18" fill="#e7d5bb"/><path d="M0 17.5H120M60 0V18" stroke="#d3bd9d" stroke-width="1"/></pattern>
<pattern id="tile" width="27" height="27" patternUnits="userSpaceOnUse"><rect width="27" height="27" fill="#dfe6e6"/><path d="M0 26.5H27M26.5 0V27" stroke="#c3cccc"/></pattern>
<pattern id="stone" width="55" height="55" patternUnits="userSpaceOnUse"><rect width="55" height="55" fill="#d9d4cc"/><path d="M0 54.5H55M54.5 0V55" stroke="#c6c0b6"/></pattern>
</defs>{''.join(x for x in o if x)}</svg>'''

html = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&family=Cormorant+Garamond:wght@500;600&display=swap" rel="stylesheet">
<style>*{{margin:0;box-sizing:border-box}}body{{width:1800px;height:1100px;background:#f6f3ee;font-family:Manrope;color:#1f2328;display:grid;grid-template-columns:1080px 1fr;gap:40px;padding:60px}}
.sheet{{display:grid;place-items:center;background:#fff;border-radius:24px;box-shadow:0 40px 80px -50px #0005;padding:10px}}
h1{{font:600 64px/1 'Cormorant Garamond';margin-bottom:14px}}p{{font-size:19px;line-height:1.55;color:#4b5057}}
.sw{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:34px 0}}.sw div{{height:120px;border-radius:14px;display:flex;align-items:flex-end;padding:12px;font-size:13px;font-weight:700}}
.mat{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.mat div{{height:150px;border-radius:14px;position:relative}}.mat span{{position:absolute;left:12px;bottom:10px;background:#fffc;border-radius:8px;padding:4px 10px;font-size:13px;font-weight:700}}
ul{{margin-top:28px;padding-left:20px;font-size:17px;line-height:1.7;color:#4b5057}}</style></head><body>
<div class="sheet">{svg}</div>
<div><h1>Квартира 54 м²<br>для пары с ребёнком</h1>
<p>Планировочное решение: кухня-гостиная у окон, спальня изолирована от прихожей, отдельный кабинет, который потом станет детской.</p>
<div class="sw"><div style="background:#e7d5bb">Дуб #E7D5BB</div><div style="background:#c7cfc4">Шалфей #C7CFC4</div><div style="background:#b8612a;color:#fff">Терракота #B8612A</div><div style="background:#2e3338;color:#fff">Графит #2E3338</div></div>
<div class="mat"><div style="background:repeating-linear-gradient(90deg,#d8c09c 0 3px,#e6d3b4 3px 11px,#dcc5a3 11px 14px,#ead9bd 14px 26px)"><span>Инженерная доска, дуб</span></div>
<div style="background:radial-gradient(circle at 30% 40%,#e6e1d9 0 18%,transparent 19%),radial-gradient(circle at 70% 70%,#cfc8bd 0 14%,transparent 15%),#dbd5cb"><span>Керамогранит «камень»</span></div>
<div style="background:repeating-linear-gradient(45deg,#c1cabd 0 4px,#cad2c6 4px 8px)"><span>Букле, диван</span></div>
<div style="background:linear-gradient(135deg,#b8612a,#8f4618)"><span style="background:#fffd">Глиняная штукатурка</span></div></div>
<ul><li>Хранение: 3 шкафа до потолка — 7,4 м погонных</li><li>Обеденный стол на 4 места между кухней и диваном</li><li>Санузел совмещён, место под стиральную машину</li><li>Все проходы от 90 см</li></ul></div></body></html>'''
open('plan.html', 'w', encoding='utf-8').write(html)
print('ok')
