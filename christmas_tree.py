#!/usr/bin/env python3

import argparse
import colorsys
import math
import os
import random
import shutil
import sys
import time

TAU = math.tau

T_BG_END = 3.0
T_GROW_END = 7.0
T_SPIN_END = 12.5
T_GARLAND = (12.5, 15.5)
T_ORNAMENTS = (13.5, 18.5)
T_LIGHTS = (16.5, 19.5)
T_STAR_DROP = 19.8
T_STAR_LAND = 20.6
T_DECO_END = 22.0
T_TOTAL = 42.0
FADE_IN = 1.5
FADE_OUT = 1.5

SPIN_TURNS = 4
SLOW_SPIN = 0.45
BANDS = 10

MOON = (255, 246, 214)
MOON_SHADE = (196, 186, 228)
MOON_GLOW = (120, 125, 200)
RIDGE_FAR = (62, 54, 135)
RIDGE_FAR_TOP = (145, 140, 215)
RIDGE_NEAR = (92, 84, 185)
SNOWCAP = (232, 238, 255)
SNOW_LINE = (226, 236, 255)
SNOW_DOT_TOP = (130, 145, 200)
SNOW_DOT_BOTTOM = (60, 68, 115)
TREE_TOP = (150, 245, 180)
TREE_BOTTOM = (12, 150, 100)
BAND_K = [1.0, 0.72, 0.88]
NEEDLES = ['▲', '▴', '·']
TRUNK = (175, 112, 64)
GARLANDS = [(255, 205, 90), (205, 222, 255)]
ORNAMENT_COLORS = [(255, 70, 100), (255, 200, 60), (80, 160, 255), (200, 110, 255),
                   (240, 245, 255), (255, 140, 60), (60, 230, 210)]
LIGHT_COLORS = [(255, 80, 110), (110, 255, 150), (90, 170, 255), (255, 225, 90),
                (255, 120, 230), (80, 240, 255)]
PRESENTS = [
    (-12, (255, 95, 110), (255, 215, 110)),
    (-7, (100, 160, 255), (240, 240, 255)),
    (4, (80, 225, 160), (255, 90, 120)),
    (9, (190, 120, 255), (255, 215, 110)),
]
STAR_ART = [
    [" ╲│╱ ", "──★──", " ╱│╲ "],
    [" ╲┊╱ ", "╌╌★╌╌", " ╱┊╲ "],
]
HOUSE_ART = ["   ╱╲   ", "  ╱  ╲  ", " ╱▔▔▔▔╲ ", " │▪  ▪│ ", " │ ▐▌ │ "]


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, t):
    return a + (b - a) * t


def mix(c1, c2, t):
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))


def scale(c, k):
    return (c[0] * k, c[1] * k, c[2] * k)


def hue(h, s=1.0, v=1.0):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (r * 255, g * 255, b * 255)


def lum(c):
    return c[0] * 0.3 + c[1] * 0.59 + c[2] * 0.11


def smooth(u):
    u = clamp(u)
    return u * u * (3 - 2 * u)


def ease_out(u):
    u = clamp(u)
    return 1 - (1 - u) ** 3


def progress(t, start, end):
    return clamp((t - start) / (end - start))


def wrap_angle(a):
    return (a + math.pi) % TAU - math.pi


def hash2(a, b):
    v = math.sin(a * 12.9898 + b * 78.233) * 43758.5453
    return v - math.floor(v)


def rotation(t):
    if t < T_GROW_END:
        return 0.0
    if t < T_SPIN_END:
        return SPIN_TURNS * TAU * smooth(progress(t, T_GROW_END, T_SPIN_END))
    return SPIN_TURNS * TAU + SLOW_SPIN * (t - T_SPIN_END)


def _to256(r, g, b):
    if abs(r - g) < 12 and abs(g - b) < 12:
        avg = (r + g + b) // 3
        if avg < 8:
            return 16
        if avg > 238:
            return 231
        return 232 + (avg - 8) // 10

    def q(v):
        return 0 if v < 48 else 1 if v < 115 else (v - 35) // 40
    return 16 + 36 * q(r) + 6 * q(g) + q(b)


_ESC_CACHE = {}


def esc(rgb, truecolor):
    key = (rgb, truecolor)
    code = _ESC_CACHE.get(key)
    if code is None:
        if truecolor:
            code = "\x1b[38;2;%d;%d;%dm" % rgb
        else:
            code = "\x1b[38;5;%dm" % _to256(*rgb)
        if len(_ESC_CACHE) > 200000:
            _ESC_CACHE.clear()
        _ESC_CACHE[key] = code
    return code


class Canvas:

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.ch = [[' '] * w for _ in range(h)]
        self.fg = [[(255, 255, 255)] * w for _ in range(h)]
        self.bold = [[False] * w for _ in range(h)]

    def copy(self):
        c = Canvas.__new__(Canvas)
        c.w, c.h = self.w, self.h
        c.ch = [row[:] for row in self.ch]
        c.fg = [row[:] for row in self.fg]
        c.bold = [row[:] for row in self.bold]
        return c

    def put(self, x, y, ch, fg=None, bold=False):
        x = int(round(x))
        y = int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.ch[y][x] = ch
            if fg is not None:
                self.fg[y][x] = fg
            self.bold[y][x] = bold

    def tint(self, x, y, col, k):
        if 0 <= x < self.w and 0 <= y < self.h and self.ch[y][x] != ' ':
            self.fg[y][x] = mix(self.fg[y][x], col, k)

    def text(self, x, y, s, fg=None, bold=False):
        for i, c in enumerate(s):
            if c != ' ':
                self.put(x + i, y, c, fg, bold)

    def render(self, truecolor, bright=1.0):
        out = []
        for y in range(self.h):
            parts = ["\x1b[%d;1H\x1b[0m" % (y + 1)]
            last_fg, last_bold = None, False
            chs, fgs, bolds = self.ch[y], self.fg[y], self.bold[y]
            for x in range(self.w):
                c = chs[x]
                if c != ' ':
                    f = fgs[x]
                    fq = (int(clamp(f[0] * bright, 0, 255)),
                          int(clamp(f[1] * bright, 0, 255)),
                          int(clamp(f[2] * bright, 0, 255)))
                    if fq[0] + fq[1] + fq[2] < 14:
                        c = ' '
                    else:
                        b = bolds[x]
                        if b != last_bold:
                            parts.append("\x1b[1m" if b else "\x1b[22m")
                            last_bold = b
                        if fq != last_fg:
                            parts.append(esc(fq, truecolor))
                            last_fg = fq
                parts.append(c)
            out.append("".join(parts))
        return "".join(out) + "\x1b[0m"


BRAILLE_BITS = ((0x01, 0x08), (0x02, 0x10), (0x04, 0x20), (0x40, 0x80))


class Braille:
    def __init__(self):
        self.cells = {}

    def dot(self, sx, sy, color):
        sx, sy = int(sx), int(math.floor(sy))
        if sx < 0 or sy < 0:
            return
        key = (sx >> 1, sy >> 2)
        bit = BRAILLE_BITS[sy & 3][sx & 1]
        cell = self.cells.get(key)
        if cell is None:
            self.cells[key] = [bit, color, lum(color)]
        else:
            cell[0] |= bit
            lc = lum(color)
            if lc > cell[2]:
                cell[1], cell[2] = color, lc

    def blit(self, cv):
        for (x, y), (bits, col, _) in self.cells.items():
            cv.put(x, y, chr(0x2800 + bits), col)


class Scene:
    MIN_W, MIN_H = 50, 20

    def __init__(self, w, h, seed):
        self.w, self.h = w, h
        self.rng = random.Random(seed)
        self.last_t = None
        self.sparkles = []
        self.shooting = []
        self.next_shoot = self.rng.uniform(4.0, 7.0)

        self._build_tree_geometry()
        self._build_ground()
        self._build_houses_and_pines()
        self._build_static()
        self._build_decorations()
        self._build_sky_objects()
        self._build_snow()

    def _build_tree_geometry(self):
        w, h = self.w, self.h
        self.ground_base = h - 5
        self.cx = w // 2
        self.base_y = self.ground_base
        self.trunk_h = 2
        bottom = self.base_y - self.trunk_h - 1
        self.top_y = max(4, bottom - 34 + 1)
        n = bottom - self.top_y + 1
        self.n = n
        R = min(w * 0.36, n * 1.25 + 2)
        self.radius = R
        self.lims = []
        for i in range(n):
            f = i / max(1, n - 1)
            base = 1 + f * (R - 1)
            jag = 0.8 + 0.2 * ((i % 4) / 3.0)
            self.lims.append(max(1, int(base * jag + 0.5)) if i else 1)
        self.trunk_w = 1 if R < 14 else 2

    def _ground_at(self, xf):
        hill = 0.9 * math.sin(xf * 0.09 + self.gp[0]) + 0.7 * math.sin(xf * 0.031 + self.gp[1])
        blend = clamp((abs(xf - self.cx - 0.5) - self.radius) / 8.0)
        v = self.ground_base + hill * blend
        for a, b, level in self.flats:
            if a <= xf < b:
                return level
            edge = min(abs(xf - a), abs(xf - b))
            if edge < 4.0:
                v = lerp(level, v, smooth(edge / 4.0))
        return v

    def _near_ridge(self, xf):
        v = self.ground_base - 3 - (4 + 3 * math.sin(xf * 0.07 + self.gp[2])
                                    + 2 * math.sin(xf * 0.19 + self.gp[3]))
        return max(self.min_top, min(v, self._ground_at(xf) - 1))

    def _far_ridge(self, xf):
        v = self.ground_base - 7 - (5 + 4 * math.sin(xf * 0.045 + self.gp[4])
                                    + 1.5 * math.sin(xf * 0.13 + self.gp[5]))
        return max(1.0, v)

    def _build_ground(self):
        self.gp = [self.rng.random() * TAU for _ in range(6)]
        self.flats = []
        self.min_top = max(self.top_y, int(self.ground_base * 0.45))
        self.ground = [int(math.floor(self._ground_at(x + 0.5))) for x in range(self.w)]

    def _build_houses_and_pines(self):
        w, rng = self.w, self.rng
        self.houses = []
        left = self.cx - int(self.radius) - 15
        right = self.cx + int(self.radius) + 7
        for x0 in (left, right):
            if 1 <= x0 and x0 + 9 < w:
                level = self.ground[x0 + 3]
                self.flats.append((x0 - 1, x0 + 9, float(level)))
                for x in range(x0 - 1, x0 + 9):
                    self.ground[x] = level
                self.houses.append(x0)

        blocked = [(self.cx - int(self.radius) - 3, self.cx + int(self.radius) + 3)]
        blocked += [(x0 - 2, x0 + 10) for x0 in self.houses]
        self.pines = []
        for _ in range(w // 12):
            x = rng.randrange(2, w - 2)
            if any(a <= x <= b for a, b in blocked):
                continue
            self.pines.append(x)
            blocked.append((x - 2, x + 2))

    def _build_static(self):
        w, h, rng = self.w, self.h, self.rng
        cv = Canvas(w, h)
        br = Braille()

        self.moon = (w - 14, 5)
        mx, my = self.moon
        R = 9.0
        mcx, mcy = mx * 2 + 1, my * 4 + 2
        for sy in range(int(mcy - R * 2), int(mcy + R * 2) + 1):
            for sx in range(int(mcx - R * 2), int(mcx + R * 2) + 1):
                dx, dy = sx - mcx, sy - mcy
                d = math.hypot(dx, dy)
                if d <= R:
                    if math.hypot(dx + 6.0, dy + 3.0) < R * 0.86:
                        continue
                    br.dot(sx, sy, mix(MOON_SHADE, MOON, clamp(0.45 + 0.55 * dx / R)))
                elif d < R * 2.0:
                    k = 1 - (d - R) / R
                    if rng.random() < 0.16 * k * k:
                        br.dot(sx, sy, scale(MOON_GLOW, 0.35 + 0.5 * k))

        self.mount = [int(min(self._far_ridge(x + 0.5), self._near_ridge(x + 0.5)))
                      for x in range(w)]
        gb = self.ground_base

        def ridge(fn, limit, color_at, texture):
            prev = None
            for sx in range(w * 2):
                xf = sx / 2.0 + 0.25
                ys = int(fn(xf) * 4)
                lim = limit(xf)
                lo, hi = (ys, ys) if prev is None else (min(prev + 1, ys), max(prev - 1, ys))
                for sy in range(lo, hi + 1):
                    if sy < lim:
                        br.dot(sx, sy, color_at(sy))
                if texture:
                    for d in range(2, 8):
                        sy = ys + d
                        if sy < lim and hash2(sx, sy) < 0.2 * (1 - d / 8.0):
                            br.dot(sx, sy, scale(color_at(sy), 0.45))
                prev = ys

        ridge(self._far_ridge,
              lambda xf: self._near_ridge(xf) * 4 - 1,
              lambda sy: mix(RIDGE_FAR, RIDGE_FAR_TOP, clamp((gb - 8 - sy / 4.0) / 8.0)),
              False)
        ridge(self._near_ridge,
              lambda xf: self._ground_at(xf) * 4,
              lambda sy: mix(RIDGE_NEAR, SNOWCAP, clamp((gb - 4 - sy / 4.0) / 7.0)),
              True)

        prev = None
        for sx in range(w * 2):
            ys = int(self._ground_at(sx / 2.0 + 0.25) * 4)
            lo, hi = (ys, ys) if prev is None else (min(prev, ys), max(prev, ys))
            col = scale(SNOW_LINE, 0.85 + 0.15 * hash2(sx, 7))
            for sy in range(lo, hi + 2):
                br.dot(sx, sy, col)
            prev = ys
        br.blit(cv)

        for x in range(w):
            for y in range(self.ground[x] + 1, h):
                if rng.random() < 0.06:
                    f = clamp((y - self.ground[x]) / 4.0)
                    cv.put(x, y, '·', mix(SNOW_DOT_TOP, SNOW_DOT_BOTTOM, f))

        for x in self.pines:
            gy = self.ground[x]
            cv.put(x, gy - 1, '▲', (30, 120, 105))
            cv.put(x, gy - 2, '▴', (45, 150, 125))

        self.windows = []
        for x0 in self.houses:
            bottom = self.ground[x0 + 3] - 1
            for r, line in enumerate(HOUSE_ART):
                y = bottom - (len(HOUSE_ART) - 1 - r)
                first = len(line) - len(line.lstrip())
                for c in range(first, len(line.rstrip())):
                    cv.put(x0 + c, y, ' ')
                for c, ch in enumerate(line):
                    if ch == ' ':
                        continue
                    if ch == '▪':
                        self.windows.append((x0 + c, y, rng.random() * TAU))
                    elif ch in '╱╲':
                        cv.put(x0 + c, y, ch, SNOWCAP)
                    elif ch == '▔':
                        cv.put(x0 + c, y, ch, (255, 110, 130))
                    elif ch == '│':
                        cv.put(x0 + c, y, ch, (150, 135, 210))
                    else:
                        cv.put(x0 + c, y, ch, (200, 130, 80))
        self.static = cv

    def _build_decorations(self):
        rng, n = self.rng, self.n
        self.ornaments = []
        for i in range(2, n - 1, 2):
            count = max(1, int(self.lims[i] * 0.7))
            for j in range(count):
                phi = (j + rng.random() * 0.6) / count * TAU
                if rng.random() < 0.12:
                    ch, col = '✦', (235, 240, 255)
                else:
                    ch, col = rng.choice('●●◆◉'), rng.choice(ORNAMENT_COLORS)
                self.ornaments.append([i, phi, ch, col, 0.0])
        rng.shuffle(self.ornaments)
        a, b = T_ORNAMENTS
        for k, o in enumerate(self.ornaments):
            o[4] = a + (b - a) * k / max(1, len(self.ornaments))

        self.lights = []
        a, b = T_LIGHTS
        for i in range(1, n, 2):
            count = max(1, int(self.lims[i] * 1.1))
            for j in range(count):
                phi = (j + rng.random() * 0.7) / count * TAU
                t0 = a + (b - a) * i / n + rng.random() * 0.25
                self.lights.append((i, phi, rng.choice(LIGHT_COLORS), t0,
                                    rng.random() * TAU, rng.uniform(1.5, 4.0)))

    def _build_sky_objects(self):
        rng, w = self.rng, self.w
        self.stars = []
        mx, my = self.moon
        for _ in range(w * self.h // 30):
            x = rng.randrange(w)
            y = rng.randrange(0, max(1, self.mount[x] - 1))
            if math.hypot((x - mx) / 2.0, y - my) < 6.0:
                continue
            kind = rng.random()
            kind = 0 if kind < 0.7 else 1 if kind < 0.94 else 2
            tint = rng.choice([(255, 255, 255), (190, 210, 255), (255, 235, 200), (225, 200, 255)])
            self.stars.append((x, y, kind, tint, rng.random() * TAU,
                               rng.uniform(1.0, 3.5), rng.uniform(0.3, 2.8)))
        self.glints = []
        for _ in range(w // 5):
            x = rng.randrange(w)
            y = self.ground[x] + rng.randint(1, 3)
            if y < self.h:
                self.glints.append((x, y, rng.random() * TAU, rng.uniform(1.0, 3.0)))
        self.aurora_ph = (rng.random() * TAU, rng.random() * TAU)

    def _build_snow(self):
        rng = self.rng
        self.snow = []
        for _ in range(self.w * self.h // 18):
            near = rng.random() < 0.3
            self.snow.append([rng.random() * self.w, rng.random() * self.h,
                              rng.uniform(4.0, 7.0) if near else rng.uniform(1.5, 3.5),
                              rng.uniform(0.3, 1.5), rng.random() * TAU, near])

    def draw(self, t):
        dt = 0.0 if self.last_t is None else clamp(t - self.last_t, 0.0, 0.1)
        self.last_t = t
        cv = self.static.copy()
        rot = rotation(t)

        self._draw_aurora(cv, t)
        self._draw_stars(cv, t)
        self._draw_windows(cv, t)
        self._draw_shooting_stars(cv, t)
        self._update_snow(t, dt)
        self._draw_snow(cv, t, near=False)
        self._draw_tree(cv, t, rot)
        self._draw_decorations(cv, t, rot)
        self._draw_star(cv, t)
        self._emit_spin_sparkles(t, dt)
        self._draw_sparkles(cv, dt)
        self._draw_presents(cv, t)
        self._draw_banner(cv, t)
        self._draw_snow(cv, t, near=True)
        return cv

    def _draw_aurora(self, cv, t):
        k = progress(t, 0.3, T_BG_END)
        if k <= 0:
            return
        br = Braille()
        mx, my = self.moon
        base = max(2.5, self.h * 0.16)
        p1, p2 = self.aurora_ph
        for sx in range(self.w * 2):
            x = sx * 0.5
            inten = (0.5 + 0.5 * math.sin(x * 0.03 - t * 0.5 + p2)) * k
            if inten < 0.15:
                continue
            c = base + 2.2 * math.sin(x * 0.045 + t * 0.35 + p1) + 1.0 * math.sin(x * 0.13 - t * 0.6)
            top = int(c * 4)
            length = int(5 + 10 * inten)
            limit = (self.mount[int(x)] - 1) * 4
            col = hue(0.42 + 0.35 * (0.5 + 0.5 * math.sin(x * 0.02 + t * 0.2)), 0.7, 1.0)
            for j in range(length):
                sy = top + j
                if sy >= limit:
                    break
                fall = 1 - j / float(length)
                if sy >= 0 and hash2(sx, sy) < inten * fall * 0.85:
                    if math.hypot((x - mx) / 2.0, sy / 4.0 - my) < 6.5:
                        continue
                    br.dot(sx, sy, scale(col, 0.22 + 0.4 * inten * fall))
        br.blit(cv)

    def _draw_stars(self, cv, t):
        for x, y, kind, tint, ph, spd, t0 in self.stars:
            if t < t0:
                continue
            pop = clamp((t - t0) * 3)
            tw = 0.5 + 0.5 * math.sin(t * spd + ph)
            if kind == 0:
                ch = '·'
            elif kind == 1:
                ch = '⋆' if tw > 0.6 else '·'
            else:
                ch = '✦' if tw > 0.35 else '✧'
            cv.put(x, y, ch, scale(tint, (0.3 + 0.7 * tw) * pop), kind == 2 and tw > 0.7)
        for x, y, ph, spd in self.glints:
            tw = math.sin(t * spd + ph)
            if tw > 0.8:
                cv.put(x, y, '✦', mix((180, 200, 255), (255, 255, 255), (tw - 0.8) * 5))

    def _draw_windows(self, cv, t):
        for x, y, ph in self.windows:
            f = 0.5 + 0.5 * math.sin(t * 2.3 + ph) * math.sin(t * 0.7 + ph * 2)
            cv.put(x, y, '▪', mix((255, 170, 70), (255, 235, 160), f))

    def _draw_shooting_stars(self, cv, t):
        rng = self.rng
        if t >= self.next_shoot:
            self.next_shoot = t + rng.uniform(5.0, 10.0)
            self.shooting.append((rng.uniform(self.w * 0.3, self.w * 0.95),
                                  rng.uniform(0, self.h * 0.2),
                                  -rng.uniform(30, 45), rng.uniform(6, 10), t))
        alive = []
        for s in self.shooting:
            x0, y0, vx, vy, born = s
            age = t - born
            if age < 0 or age > 1.0:
                continue
            alive.append(s)
            fade = 1 - age
            for k in range(13, -1, -1):
                a = age - k * 0.012
                if a < 0:
                    continue
                xi, yi = int(round(x0 + vx * a)), int(round(y0 + vy * a))
                if 0 <= xi < self.w and 0 <= yi < self.mount[xi]:
                    ch = '✦' if k == 0 else '─' if k < 8 else '·'
                    col = mix((255, 248, 230), (110, 140, 255), k / 13.0)
                    cv.put(xi, yi, ch, scale(col, fade * (1 - k / 15.0)), k == 0)
        self.shooting = alive

    def _update_snow(self, t, dt):
        active = int(len(self.snow) * progress(t, 0.5, T_BG_END))
        rng = self.rng
        for f in self.snow[:active]:
            f[1] += f[2] * dt
            xi = int(f[0]) % self.w
            if f[1] >= self.ground[xi] + (0.5 if f[5] else 0):
                f[0] = rng.random() * self.w
                f[1] = -rng.random() * 3
        self.active_snow = active

    def _draw_snow(self, cv, t, near):
        for x, y, vy, amp, ph, is_near in self.snow[:self.active_snow]:
            if is_near != near or y < 0:
                continue
            xd = x + amp * math.sin(t * 1.3 + ph)
            if near:
                cv.put(xd, y, '•' if ph < 3.5 else '∗', (245, 248, 255))
            else:
                cv.put(xd, y, '·', (150, 165, 220))

    def _draw_tree(self, cv, t, rot):
        g = progress(t, T_BG_END, T_GROW_END)
        if g <= 0:
            return
        cx, n, rng = self.cx, self.n, self.rng

        trunk_rows = int(math.ceil(clamp(g * 8) * self.trunk_h))
        for k in range(trunk_rows):
            y = self.base_y - 1 - k
            for dx in range(-self.trunk_w, self.trunk_w + 1):
                if dx == -self.trunk_w:
                    cv.put(cx + dx, y, '▐', scale(TRUNK, 0.75))
                elif dx == self.trunk_w:
                    cv.put(cx + dx, y, '▌', scale(TRUNK, 0.55))
                else:
                    cv.put(cx + dx, y, '▓', TRUNK)

        rows_shown = clamp((g - 0.1) / 0.9) * n
        garland_rows = progress(t, *T_GARLAND) * n
        turns = max(2.5, n / 9.0)
        g_step = turns * TAU / n
        shimmer = t > T_DECO_END
        sweep = ((t - T_DECO_END) * 0.45) % 1.8 - 0.4
        for i in range(n):
            from_bottom = n - 1 - i
            if from_bottom >= rows_shown:
                continue
            frac = clamp(rows_shown - from_bottom)
            lim_full = self.lims[i]
            lim = int(round(lim_full * ease_out(frac)))
            span = lim_full + 0.5
            y = self.top_y + i
            hcol = mix(TREE_TOP, TREE_BOTTOM, i / max(1.0, n - 1.0))

            if frac < 1 and rng.random() < 0.6:
                side = rng.choice((-1, 1))
                self.sparkles.append([cx + side * lim, y, side * rng.uniform(3, 8),
                                      -rng.uniform(1, 4), 0.6, 0.6,
                                      rng.choice([(255, 220, 110), (150, 255, 190)])])

            for dx in range(-lim, lim + 1):
                theta = math.asin(dx / span)
                phi = theta + rot
                light = 0.35 + 0.65 * (0.5 + 0.5 * math.cos(theta + 0.55))
                band = int(math.floor(phi * (BANDS / TAU) + i * 0.35)) % 3
                x = cx + dx
                if lim > 0 and abs(dx) == lim:
                    fg = scale(hcol, light * 0.9)
                    ch = '╱' if dx < 0 else '╲'
                else:
                    ch = NEEDLES[band]
                    if ch == '▲' and light < 0.55:
                        ch = '▴'
                    fg = scale(hcol, light * BAND_K[band])
                    if i < garland_rows:
                        for gi, gcol in enumerate(GARLANDS):
                            d = wrap_angle(phi - (i * g_step + gi * math.pi))
                            if abs(d) < 0.28:
                                ch, fg = '•', scale(gcol, 0.4 + 0.6 * math.cos(theta))
                                break
                if shimmer:
                    d = abs(i / float(n) + dx / span * 0.25 - sweep)
                    if d < 0.07:
                        fg = mix(fg, (235, 255, 245), 0.6 * (1 - d / 0.07))
                cv.put(x, y, ch, fg)

    def _place(self, i, phi, rot):
        dphi = wrap_angle(phi - rot)
        depth = math.cos(dphi)
        if depth < 0.15:
            return None
        lim = self.lims[i]
        dx = int(round((lim + 0.5) * math.sin(dphi)))
        if abs(dx) >= lim:
            dx = (lim - 1) * (1 if dx > 0 else -1)
        return self.cx + dx, self.top_y + i, depth

    def _draw_decorations(self, cv, t, rot):
        if t < T_ORNAMENTS[0] and t < T_LIGHTS[0]:
            return
        final = t >= T_DECO_END

        lit, dim, flashes = [], [], []
        for i, phi, col, t0, ph, spd in self.lights:
            if t < t0:
                continue
            p = self._place(i, phi, rot)
            if p is None:
                continue
            x, y, depth = p
            if t - t0 < 0.2:
                flashes.append((x, y))
                continue
            if final:
                on = math.sin(t * 3.0 - i * 0.45 + ph * 0.3) > -0.2
            else:
                on = math.sin(t * spd + ph) > -0.3
            k = 0.5 + 0.5 * depth
            (lit if on else dim).append((x, y, scale(col, k)))

        for x, y, col in lit:
            for oy in (-1, 0, 1):
                for ox in (-2, -1, 0, 1, 2):
                    if ox or oy:
                        cv.tint(x + ox, y + oy, col, 0.5 / (abs(ox) + 2 * abs(oy) + 0.5))
        for x, y, col in dim:
            cv.put(x, y, '∙', scale(col, 0.35))
        for x, y, col in lit:
            cv.put(x, y, '●', col, True)
        for x, y in flashes:
            cv.put(x, y, '✦', (255, 255, 255), True)

        for i, phi, ch, col, t0 in self.ornaments:
            if t < t0:
                continue
            p = self._place(i, phi, rot)
            if p is None:
                continue
            x, y, depth = p
            age = t - t0
            if age < 0.15:
                cv.put(x, y, '✦', (255, 255, 255), True)
                cv.put(x - 1, y, '─', (255, 250, 210))
                cv.put(x + 1, y, '─', (255, 250, 210))
                continue
            c = scale(col, 0.45 + 0.55 * depth)
            if age < 0.35:
                c = mix(c, (255, 255, 255), 0.6)
            elif depth > 0.95:
                c = mix(c, (255, 255, 255), 0.35)
            cv.put(x, y, ch, c, depth > 0.8)

    def _draw_star(self, cv, t):
        if t < T_STAR_DROP:
            return
        cx = self.cx
        p = ease_out(progress(t, T_STAR_DROP, T_STAR_LAND))
        cy = int(round(lerp(-2, self.top_y - 2, p)))
        glow = 0.5 + 0.5 * math.sin(t * 5)
        core = mix((255, 200, 50), (255, 255, 230), glow)
        ray = mix((255, 165, 40), (255, 235, 130), 1 - glow)
        art = STAR_ART[int(t * 4) % 2]
        for r, row in enumerate(art):
            for c, ch in enumerate(row):
                if ch != ' ':
                    cv.put(cx - 2 + c, cy - 1 + r, ch, core if ch == '★' else ray, ch == '★')
        if p < 1:
            for k in range(1, 5):
                cv.put(cx, cy - 1 - k, '│' if k < 3 else '·', scale((255, 220, 110), 1 - k / 5.0))
        a = t - T_STAR_LAND
        if 0 <= a < 1.2:
            rad = a * 12
            fade = 1 - a / 1.2
            ch = '✦' if a < 0.4 else '✧' if a < 0.8 else '·'
            for k in range(24):
                ang = k * TAU / 24
                cv.put(cx + math.cos(ang) * rad * 2, cy + math.sin(ang) * rad, ch,
                       scale(hue(k / 24.0 - t * 0.3, 0.45, 1.0), fade))

    def _emit_spin_sparkles(self, t, dt):
        if not (T_GROW_END < t < T_SPIN_END) or dt <= 0:
            return
        speed = (rotation(t) - rotation(t - 0.05)) / 0.05
        rng = self.rng
        expected = speed * dt * 8
        count = int(expected) + (1 if rng.random() < expected % 1 else 0)
        for _ in range(count):
            i = rng.randrange(self.n)
            side = rng.choice((-1, 1))
            self.sparkles.append([self.cx + side * self.lims[i], self.top_y + i,
                                  side * rng.uniform(5, 10 + speed * 2), -rng.uniform(0, 4),
                                  0.9, 0.9, rng.choice([(255, 220, 110), (150, 255, 190),
                                                        (255, 255, 255), (140, 200, 255)])])

    def _draw_sparkles(self, cv, dt):
        alive = []
        for s in self.sparkles:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[3] += 6 * dt
            s[4] -= dt
            if s[4] <= 0:
                continue
            alive.append(s)
            f = s[4] / s[5]
            ch = '✦' if f > 0.6 else '✧' if f > 0.3 else '·'
            cv.put(s[0], s[1], ch, scale(s[6], 0.3 + 0.7 * f), f > 0.6)
        self.sparkles = alive[-400:]

    def _draw_presents(self, cv, t):
        if t < T_DECO_END:
            return
        bottom = self.base_y - 1
        for k, (off, box, ribbon) in enumerate(PRESENTS):
            age = t - (T_DECO_END + 0.3 + k * 0.35)
            if age < 0:
                continue
            drop = int(round((1 - ease_out(age / 0.35)) * 6))
            x0 = self.cx + off
            y = bottom - drop
            for c, (top, bot) in enumerate(zip("┏━╋━┓", "┗━┻━┛")):
                col = ribbon if c == 2 else box
                cv.put(x0 + c, y - 1, top, col)
                cv.put(x0 + c, y, bot, scale(col, 0.8))
            cv.put(x0 + 2, y - 2, '⋈', ribbon, True)

    def _draw_banner(self, cv, t):
        t0 = T_DECO_END + 2.0
        if t < t0:
            return
        line1 = "M E R R Y   C H R I S T M A S"
        flank = 8
        if len(line1) + 2 * (flank + 3) > self.w:
            line1 = "MERRY CHRISTMAS"
        if len(line1) + 2 * (flank + 3) > self.w:
            flank = 0
        line2 = "✧  and a happy new year  ✧"
        y1, y2 = self.h - 3, self.h - 2
        n1 = len(line1)
        x1 = self.cx - n1 // 2
        x2 = self.cx - len(line2) // 2
        el = t - t0

        for x in range(x1 - flank - 3, x1 + n1 + flank + 3):
            cv.put(x, y1, ' ')
        for x in range(x2 - 1, x2 + len(line2) + 1):
            cv.put(x, y2, ' ')

        grow = int(clamp(el * 1.5) * flank)
        for j in range(grow):
            col = scale((255, 210, 120), 1 - j / float(flank + 2))
            cv.put(x1 - 2 - j, y1, '─', col)
            cv.put(x1 + n1 + 1 + j, y1, '─', col)
        if flank and grow == flank:
            cv.put(x1 - 2 - flank, y1, '✦', (255, 225, 140), True)
            cv.put(x1 + n1 + 1 + flank, y1, '✦', (255, 225, 140), True)

        shown = int(el * 14)
        sweep = (el * 12) % (n1 + 24) - 12
        for k, ch in enumerate(line1[:shown]):
            if ch != ' ':
                col = hue(0.93 + k * 0.018 - el * 0.08, 0.55, 1.0)
                d = abs(k - sweep)
                if d < 3:
                    col = mix(col, (255, 255, 255), 0.7 * (1 - d / 3.0))
                cv.put(x1 + k, y1, ch, col, True)

        shown2 = int((el - n1 / 14.0 - 0.4) * 18)
        for k, ch in enumerate(line2[:max(0, shown2)]):
            if ch != ' ':
                f = k / float(len(line2) - 1)
                cv.put(x2 + k, y2, ch, mix((255, 200, 130), (255, 130, 185), f))


def detect_truecolor(choice):
    if choice != "auto":
        return choice == "truecolor"
    if os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return True
    return os.environ.get("TERM_PROGRAM", "") in ("iTerm.app", "WezTerm", "vscode", "ghostty")


def main():
    ap = argparse.ArgumentParser(description="Animated ASCII Christmas tree.")
    ap.add_argument("--fps", type=float, default=20, help="frames per second (default 20)")
    ap.add_argument("--speed", type=float, default=1.0, help="animation speed multiplier")
    ap.add_argument("-i", "--infinite", "--once", dest="once", action="store_true",
                    help="never reset: after the greeting, keep snowing and spinning forever")
    ap.add_argument("--start", type=float, default=0.0,
                    help="start at this many seconds into the show")
    ap.add_argument("--colors", choices=("auto", "truecolor", "256"), default="auto",
                    help="colour mode (default: auto-detect)")
    ap.add_argument("--seed", type=int, help="random seed for a reproducible scene")
    args = ap.parse_args()

    truecolor = detect_truecolor(args.colors)
    seed = args.seed if args.seed is not None else random.randrange(1 << 30)
    frame_time = 1.0 / max(1.0, args.fps)
    out = sys.stdout

    out.write("\x1b[?1049h\x1b[?25l\x1b[0m\x1b[2J")
    out.flush()
    try:
        size, scene = None, None
        clock0 = time.monotonic() - args.start / args.speed
        while True:
            now = time.monotonic()
            cols, rows = shutil.get_terminal_size((80, 24))
            if (cols, rows) != size:
                size = (cols, rows)
                out.write("\x1b[0m\x1b[2J")
                big_enough = cols >= Scene.MIN_W and rows >= Scene.MIN_H
                scene = Scene(cols, rows, seed) if big_enough else None

            t = (now - clock0) * args.speed
            if not args.once and t >= T_TOTAL:
                seed = random.randrange(1 << 30)
                scene = Scene(cols, rows, seed) if scene else None
                clock0, t = now, 0.0

            if scene is None:
                msg = "Please enlarge the terminal to at least %dx%d" % (Scene.MIN_W, Scene.MIN_H)
                out.write("\x1b[0m\x1b[2J\x1b[1;1H" + msg[:cols])
            else:
                bright = clamp(t / FADE_IN)
                if not args.once:
                    bright *= clamp((T_TOTAL - t) / FADE_OUT)
                out.write(scene.draw(t).render(truecolor, bright))
            out.flush()
            time.sleep(max(0.0, frame_time - (time.monotonic() - now)))
    except KeyboardInterrupt:
        pass
    finally:
        out.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        out.flush()
        print("Merry Christmas! ✦")


if __name__ == "__main__":
    main()
