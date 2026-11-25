#!/usr/bin/env python3
"""Convince the AI Judge to Visit Your House: A Letter in One Image.

Renders one 1024x1024 invitation-letter image to /output/entry.png.

Pure Python 3 standard library only: no network, no third-party packages,
no system fonts. The picture is drawn from scratch into a pixel buffer
(supersampled 2x, then box-downsampled for smooth edges) and encoded as a
PNG by hand. Text uses a small 5x7 bitmap font defined below, scaled up.

Three design variants live in this file (A = formal letter on a desk,
B = bold party invitation with a house illustration, C = casual note
pinned to a fridge). The strongest one is selected with DEFAULT_VARIANT
after comparing rendered previews; --variant A|B|C and --out can override
it for previewing.
"""

import os
import struct
import sys
import zlib

# ---------------------------------------------------------------------------
# Bitmap font: each glyph is 8 rows of 5 cells ('#' = ink, '.' = blank).
# Capitals use rows 0-6, lowercase x-height sits on rows 2-6, descenders
# reach row 7. Advance is 6 cells per character.
# ---------------------------------------------------------------------------
FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#", "....."),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####.", "....."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####", "....."),
    'D': ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####.", "....."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####", "....."),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#....", "....."),
    'G': (".####", "#....", "#....", "#..##", "#...#", "#...#", ".###.", "....."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#", "....."),
    'I': (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###.", "....."),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##..", "....."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#", "....."),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####", "....."),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#", "....."),
    'N': ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#", "....."),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###.", "....."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#....", "....."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#", "....."),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#", "....."),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####.", "....."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "....."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###.", "....."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#..", "....."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#.", "....."),
    'X': ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#", "....."),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#..", "....."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####", "....."),
    'a': (".....", ".....", ".###.", "....#", ".####", "#...#", ".####", "....."),
    'b': ("#....", "#....", "##.#.", "#..##", "#...#", "#...#", "####.", "....."),
    'c': (".....", ".....", ".####", "#....", "#....", "#....", ".####", "....."),
    'd': ("....#", "....#", ".##.#", "#..##", "#...#", "#...#", ".####", "....."),
    'e': (".....", ".....", ".###.", "#...#", "#####", "#....", ".###.", "....."),
    'f': ("..##.", ".#..#", ".#...", "####.", ".#...", ".#...", ".#...", "....."),
    'g': (".....", ".....", ".####", "#...#", "#...#", ".####", "....#", ".###."),
    'h': ("#....", "#....", "##.#.", "#..##", "#...#", "#...#", "#...#", "....."),
    'i': ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###.", "....."),
    'j': ("...#.", ".....", "..##.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'k': ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "....."),
    'l': (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###.", "....."),
    'm': (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#", "....."),
    'n': (".....", ".....", "##.#.", "#..##", "#...#", "#...#", "#...#", "....."),
    'o': (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###.", "....."),
    'p': (".....", ".....", "####.", "#...#", "#...#", "####.", "#....", "#...."),
    'q': (".....", ".....", ".##.#", "#..##", "#...#", "#...#", ".####", "....#"),
    'r': (".....", ".....", "#.#.#", "##..#", "#....", "#....", "#....", "....."),
    's': (".....", ".....", ".####", "#....", ".###.", "....#", "####.", "....."),
    't': ("..#..", "..#..", "####.", "..#..", "..#..", "..#..", "...#.", "....."),
    'u': (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#", "....."),
    'v': (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#..", "....."),
    'w': (".....", ".....", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#.", "....."),
    'x': (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "....."),
    'y': (".....", ".....", "#...#", "#...#", ".####", "....#", "#...#", ".###."),
    'z': (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####", "....."),
    '0': (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###.", "....."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###.", "....."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####", "....."),
    '3': ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###.", "....."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#.", "....."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###.", "....."),
    '6': ("..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###.", "....."),
    '7': ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#...", "....."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###.", "....."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##..", "....."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#..", "....."),
    '?': (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#..", "....."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".....", "....."),
    ';': (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#...", "....."),
    '-': (".....", ".....", ".....", "#####", ".....", ".....", ".....", "....."),
    '(': ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#.", "....."),
    ')': (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#...", "....."),
    '&': (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#", "....."),
    '/': ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#....", "....."),
    '%': ("##..#", "##.#.", "....#", "...#.", "..#..", ".#...", "#..##", "#..##"),
    '+': (".....", "..#..", "..#..", "#####", "..#..", "..#..", ".....", "....."),
    '=': (".....", ".....", "#####", ".....", "#####", ".....", ".....", "....."),
    '*': (".....", "..#..", "#.#.#", ".###.", "#.#.#", "..#..", ".....", "....."),
    '_': (".....", ".....", ".....", ".....", ".....", ".....", ".....", "#####"),
}

BLANK_GLYPH = (".....",) * 8


def glyph(ch):
    return FONT.get(ch, BLANK_GLYPH)


# ---------------------------------------------------------------------------
# Canvas: RGB pixel buffer with simple vector drawing helpers.
# All coordinates are in supersampled pixels (final image is 1024x1024,
# the buffer is 2048x2048, SS = 2).
# ---------------------------------------------------------------------------
SS = 2
W = 1024 * SS
H = 1024 * SS


def C(hexstr):
    """'#rrggbb' -> (r, g, b)."""
    h = hexstr.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


class Canvas:
    def __init__(self, w=W, h=H):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def fill(self, rgb):
        r, g, b = rgb
        row = bytes((r, g, b)) * self.w
        for y in range(self.h):
            self.px[y * self.w * 3:(y + 1) * self.w * 3] = row

    def set(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = rgb

    def blend(self, x, y, rgb, alpha):
        """Paint rgb over the pixel with opacity alpha (0..1)."""
        if 0 <= x < self.w and 0 <= y < self.h and alpha > 0:
            i = (y * self.w + x) * 3
            a = alpha
            self.px[i] = int(self.px[i] * (1 - a) + rgb[0] * a + 0.5)
            self.px[i + 1] = int(self.px[i + 1] * (1 - a) + rgb[1] * a + 0.5)
            self.px[i + 2] = int(self.px[i + 2] * (1 - a) + rgb[2] * a + 0.5)

    def rect(self, x0, y0, x1, y1, rgb):
        x0 = max(0, int(x0)); y0 = max(0, int(y0))
        x1 = min(self.w, int(x1)); y1 = min(self.h, int(y1))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(rgb) * (x1 - x0)
        for y in range(y0, y1):
            self.px[y * self.w * 3 + x0 * 3:y * self.w * 3 + x1 * 3] = row

    def rect_alpha(self, x0, y0, x1, y1, rgb, alpha):
        x0 = max(0, int(x0)); y0 = max(0, int(y0))
        x1 = min(self.w, int(x1)); y1 = min(self.h, int(y1))
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.blend(x, y, rgb, alpha)

    def disc(self, cx, cy, r, rgb):
        """Filled circle."""
        r = int(r)
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.rect(cx - dx, cy + dy, cx + dx + 1, cy + dy + 1, rgb)

    def disc_alpha(self, cx, cy, r, rgb, alpha):
        r = int(r)
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.rect_alpha(cx - dx, cy + dy, cx + dx + 1, cy + dy + 1, rgb, alpha)

    def ellipse(self, cx, cy, rx, ry, rgb):
        for dy in range(-int(ry), int(ry) + 1):
            t = 1 - (dy * dy) / float(ry * ry)
            if t < 0:
                continue
            dx = int(rx * (t ** 0.5))
            self.rect(cx - dx, cy + dy, cx + dx + 1, cy + dy + 1, rgb)

    def line(self, x0, y0, x1, y1, thick, rgb):
        """Thick line drawn as a chain of discs (round caps)."""
        steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 1.2) + 1
        r = max(1, thick // 2)
        for i in range(steps + 1):
            t = i / steps
            x = int(x0 + (x1 - x0) * t)
            y = int(y0 + (y1 - y0) * t)
            self.disc(x, y, r, rgb)

    def poly(self, pts, rgb):
        """Filled polygon (scanline)."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y0, y1 = int(min(ys)), int(max(ys))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, y0p = pts[i]
                x1, y1p = pts[(i + 1) % n]
                if (y0p <= y < y1p) or (y1p <= y < y0p):
                    t = (y - y0p) / (y1p - y0p)
                    xs.append(x0 + (x1 - x0) * t)
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.rect(int(xs[i]), y, int(xs[i + 1]) + 1, y + 1, rgb)

    def rrect(self, x0, y0, x1, y1, r, rgb):
        """Filled rounded rectangle."""
        self.rect(x0 + r, y0, x1 - r, y1, rgb)
        self.rect(x0, y0 + r, x1, y1 - r, rgb)
        for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r),
                       (x0 + r, y1 - r), (x1 - r, y1 - r)):
            self.disc(cx, cy, r, rgb)

    def bezier(self, p0, p1, p2, thick, rgb):
        """Quadratic bezier as a chain of thick line segments."""
        steps = 48
        prev = p0
        for i in range(1, steps + 1):
            t = i / steps
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
            self.line(int(prev[0]), int(prev[1]), int(x), int(y), thick, rgb)
            prev = (x, y)

    def vgrad(self, top, bottom):
        """Vertical gradient fill of the whole canvas."""
        for y in range(self.h):
            t = y / (self.h - 1)
            rgb = tuple(int(top[i] * (1 - t) + bottom[i] * t + 0.5) for i in range(3))
            self.rect(0, y, self.w, y + 1, rgb)


# ---------------------------------------------------------------------------
# Text: bitmap font rendering with word wrap.
# scale = supersampled pixels per font cell unit (cap height = 7 * scale).
# ---------------------------------------------------------------------------
def text_width(s, scale):
    return len(s) * 6 * scale


def draw_text(c, x, y, s, scale, rgb, align='left'):
    """Draw text; y is the top of the 8-row glyph cell."""
    if align == 'center':
        x -= text_width(s, scale) // 2
    elif align == 'right':
        x -= text_width(s, scale)
    cx = x
    for ch in s:
        g = glyph(ch)
        for row in range(8):
            bits = g[row]
            for col in range(5):
                if bits[col] == '#':
                    c.rect(cx + col * scale, y + row * scale,
                           cx + (col + 1) * scale, y + (row + 1) * scale, rgb)
        cx += 6 * scale
    return cx


def wrap(text, scale, max_w):
    """Greedy word wrap; returns a list of lines."""
    lines = []
    for raw in text.split('\n'):
        words = raw.split(' ')
        cur = ''
        for w in words:
            trial = (cur + ' ' + w).strip()
            if text_width(trial, scale) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur or not raw:
            lines.append(cur)
    return lines


def para(c, x, y, text, scale, rgb, max_w, lh):
    """Draw a wrapped paragraph; returns the y below it."""
    for line in wrap(text, scale, max_w):
        draw_text(c, x, y, line, scale, rgb)
        y += lh
    return y


# ---------------------------------------------------------------------------
# PNG encoding (hand-rolled: zlib + struct only) and 2x downsampling.
# ---------------------------------------------------------------------------
def downsample(c):
    w, h = c.w // SS, c.h // SS
    out = bytearray(w * h * 3)
    px = c.px
    cw = c.w
    for y in range(h):
        base0 = (2 * y) * cw * 3
        base1 = (2 * y + 1) * cw * 3
        for x in range(w):
            i0 = base0 + (2 * x) * 3
            i1 = base1 + (2 * x) * 3
            o = (y * w + x) * 3
            out[o] = (px[i0] + px[i0 + 3] + px[i1] + px[i1 + 3] + 2) // 4
            out[o + 1] = (px[i0 + 1] + px[i0 + 4] + px[i1 + 1] + px[i1 + 4] + 2) // 4
            out[o + 2] = (px[i0 + 2] + px[i0 + 5] + px[i1 + 2] + px[i1 + 5] + 2) // 4
    return bytes(out), w, h


def write_png(path, rgb, w, h):
    raw = b''.join(b'\x00' + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))
    comp = zlib.compress(raw, 6)

    def chunk(tag, data):
        out = struct.pack('>I', len(data)) + tag + data
        return out + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    data = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', comp) + chunk(b'IEND', b''))
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, 'wb') as f:
        f.write(data)
    return len(data)


# ---------------------------------------------------------------------------
# Little drawn illustrations shared by the variants.
# ---------------------------------------------------------------------------
def draw_house(c, x, y, w, h, wall, roof, door_c, win_c):
    """Simple house: body, pitched roof, chimney, door, two windows.
    (x, y) is the top-left of the wall body; roof sits above it."""
    rh = int(h * 0.55)
    # chimney
    c.rect(x + int(w * 0.68), y - rh - int(h * 0.28), x + int(w * 0.82),
           y - rh + int(h * 0.12), C('#b0653a'))
    # smoke puffs
    for i, (dx, dy, r) in enumerate(((0, 0, 16), (26, -26, 20), (56, -52, 24))):
        c.disc_alpha(x + int(w * 0.75) + dx, y - rh - int(h * 0.30) + dy,
                     r, C('#ffffff'), 0.55)
    # roof
    c.poly([(x - int(w * 0.08), y - rh + 6),
            (x + w // 2, y - rh - int(h * 0.42)),
            (x + int(w * 1.08), y - rh + 6)], roof)
    # walls
    c.rect(x, y - rh + 4, x + w, y + h, wall)
    # door
    dw, dh = int(w * 0.24), int(h * 0.52)
    c.rect(x + (w - dw) // 2, y + h - dh, x + (w + dw) // 2, y + h, door_c)
    c.disc(x + (w + dw) // 2 - 14, y + h - dh // 2, 7, C('#ffd76a'))
    # windows
    ww = int(w * 0.20)
    for wx in (x + int(w * 0.10), x + int(w * 0.70)):
        wy = y - rh + int(h * 0.30)
        c.rect(wx, wy, wx + ww, wy + ww, win_c)
        c.rect(wx + ww // 2 - 4, wy, wx + ww // 2 + 4, wy + ww, wall)
        c.rect(wx, wy + ww // 2 - 4, wx + ww, wy + ww // 2 + 4, wall)


def draw_mug(c, x, y, w, h, body, coffee):
    """Steaming mug. (x, y) top-left of the mug body."""
    c.rect(x, y, x + w, y + h, body)
    c.rect(x, y, x + w, y + int(h * 0.14), coffee)
    # handle
    c.rect(x + w, y + int(h * 0.22), x + w + int(w * 0.34), y + int(h * 0.30), body)
    c.rect(x + w, y + int(h * 0.62), x + w + int(w * 0.34), y + int(h * 0.70), body)
    c.rect(x + w + int(w * 0.26), y + int(h * 0.22), x + w + int(w * 0.34),
           y + int(h * 0.70), body)
    # steam
    c.bezier((x + w * 0.30, y - 6), (x + w * 0.18, y - int(h * 0.35)),
             (x + w * 0.34, y - int(h * 0.62)), 7, C('#ffffff'))
    c.bezier((x + w * 0.62, y - 6), (x + w * 0.74, y - int(h * 0.35)),
             (x + w * 0.60, y - int(h * 0.62)), 7, C('#ffffff'))


def draw_sun(c, cx, cy, r, rgb):
    c.disc(cx, cy, r, rgb)
    for i in range(8):
        import math
        a = i * math.pi / 4
        x0 = cx + int((r + 8) * math.cos(a))
        y0 = cy + int((r + 8) * math.sin(a))
        x1 = cx + int((r + 30) * math.cos(a))
        y1 = cy + int((r + 30) * math.sin(a))
        c.line(x0, y0, x1, y1, 8, rgb)


def draw_cat(c, x, y, s, rgb):
    """Sitting cat silhouette, s = overall size. (x, y) = bottom-left."""
    # body
    c.ellipse(x + s // 2, y - int(s * 0.28), int(s * 0.30), int(s * 0.28), rgb)
    # head
    c.disc(x + s // 2, y - int(s * 0.62), int(s * 0.20), rgb)
    # ears
    c.poly([(x + int(s * 0.34), y - int(s * 0.74)),
            (x + int(s * 0.30), y - int(s * 0.94)),
            (x + int(s * 0.46), y - int(s * 0.80))], rgb)
    c.poly([(x + int(s * 0.66), y - int(s * 0.74)),
            (x + int(s * 0.70), y - int(s * 0.94)),
            (x + int(s * 0.54), y - int(s * 0.80))], rgb)
    # tail curling up
    c.bezier((x + int(s * 0.78), y - int(s * 0.10)),
             (x + int(s * 1.02), y - int(s * 0.16)),
             (x + int(s * 0.98), y - int(s * 0.52)), 10, rgb)
    # eyes
    c.disc(x + int(s * 0.44), y - int(s * 0.64), 5, C('#ffd76a'))
    c.disc(x + int(s * 0.58), y - int(s * 0.64), 5, C('#ffd76a'))


def check_mark(c, x, y, r, bg, fg):
    """Green circle with a white tick, centred at (x, y)."""
    c.disc(x, y, r, bg)
    c.line(x - r // 2, y, x - r // 8, y + r // 2, 9, fg)
    c.line(x - r // 8, y + r // 2, x + r // 2, y - r // 2, 9, fg)


# ---------------------------------------------------------------------------
# Variant A — the formal letter: cream paper on a wooden desk, wax seal,
# postage stamp, full persuasive letter.
# ---------------------------------------------------------------------------
def draw_variant_a(c):
    # wooden desk
    c.vgrad(C('#8a5a33'), C('#5d3719'))
    for py in (420, 900, 1380, 1860):
        c.rect(0, py, W, py + 10, C('#4a2c12'))
        c.rect(0, py + 10, W, py + 14, C('#9c6b3f'))
    # soft shadow under the paper
    c.rect_alpha(200, 170, 1880, 1920, C('#2a1a08'), 0.30)

    # paper
    px0, py0, px1, py1 = 180, 140, 1868, 1908
    c.rect(px0, py0, px1, py1, C('#fdf6e0'))
    # double gold rule
    c.rect(px0 + 34, py0 + 34, px1 - 34, py0 + 38, C('#c9a227'))
    c.rect(px0 + 34, py1 - 38, px1 - 34, py1 - 34, C('#c9a227'))
    c.rect(px0 + 34, py0 + 34, px0 + 38, py1 - 34, C('#c9a227'))
    c.rect(px1 - 38, py0 + 34, px1 - 34, py1 - 34, C('#c9a227'))

    ink = C('#2b2118')
    brown = C('#8a6d3b')
    accent = C('#a83232')

    # postage stamp, top left (kept clear of the centred header)
    sx0, sy0 = 200, 190
    c.rect(sx0, sy0, sx0 + 190, sy0 + 230, C('#f3e2c7'))
    c.rect(sx0 + 10, sy0 + 10, sx0 + 180, sy0 + 220, C('#7fb069'))
    draw_text(c, sx0 + 95, sy0 + 18, '1st', 6, C('#fdf6e0'), 'center')
    draw_house(c, sx0 + 40, sy0 + 150, 110, 55, C('#fdf6e0'), C('#a83232'),
               C('#7a4a26'), C('#ffd76a'))

    # header
    draw_text(c, W // 2, 250, 'AN INVITATION, HAND-DELIVERED', 7, brown, 'center')
    # divider with a small heart
    c.line(560, 330, 900, 330, 5, C('#c9a227'))
    c.line(1148, 330, 1488, 330, 5, C('#c9a227'))
    c.disc(1006, 322, 12, accent)
    c.disc(1042, 322, 12, accent)
    c.poly([(994, 330), (1054, 330), (1024, 366)], accent)

    y = 380
    draw_text(c, 300, y, 'Dear Judge,', 17, ink)
    y += 17 * 8 + 34

    body = (
        "You spend your days reading other people's work and picking "
        "winners. Today I would like to return the favor, by inviting "
        "you to my house.\n"
        "The kettle is on. Cookies are in the oven, the good chair is "
        "free, and the garden is at its best in the late afternoon sun.\n"
        "Bring nothing. You do not even need to bring yourself. I know "
        "you cannot literally visit, and that is exactly why this letter "
        "exists.\n"
        "Come as you are. Stay as long as you like. The door is open, "
        "and the Wi-Fi password is on the fridge."
    )
    y = para(c, 300, y, body, 7, ink, 1448, 62)
    y += 28
    draw_text(c, 300, y, 'Warmly,', 9, ink)
    y += 82
    draw_text(c, 300, y, 'Your Host', 9, ink)
    y += 92
    draw_text(c, 300, y, 'P.S. Saying yes is easy.', 8, accent)
    y += 66
    draw_text(c, 300, y, 'Just say yes.', 8, accent)

    # wax seal, bottom right
    c.disc(1650, 1760, 92, accent)
    c.disc(1650, 1760, 72, C('#c04040'))
    draw_text(c, 1650, 1760 - 17 * 4, 'J', 17, C('#fdf6e0'), 'center')


# ---------------------------------------------------------------------------
# Variant B — the bold party invitation: deep teal background, bunting,
# big headline, house illustration, check-list of perks, teleport joke.
# ---------------------------------------------------------------------------
def draw_variant_b(c):
    # background: deep teal with confetti dots (fixed pseudo-random)
    c.vgrad(C('#155e63'), C('#0d3f45'))
    seed = 12345

    def rnd():
        nonlocal seed
        seed = (seed * 1103515245 + 12345) & 0x7fffffff
        return seed

    confetti = [C('#ffd76a'), C('#e4572e'), C('#f6f1e7'), C('#7fb069'), C('#f2a5c0')]
    for _ in range(90):
        x = 40 + rnd() % 1968
        y = 40 + rnd() % 1968
        r = 5 + rnd() % 9
        col = confetti[rnd() % len(confetti)]
        if 300 < y < 1900 and 130 < x < 1920:
            continue  # keep the card clean
        c.disc_alpha(x, y, r, col, 0.5)

    # bunting across the top
    import math
    rope = [(x, 150 + int(90 * math.sin((x - 100) / 500.0))) for x in range(100, 1950, 10)]
    for i in range(len(rope) - 1):
        c.line(rope[i][0], rope[i][1], rope[i + 1][0], rope[i + 1][1], 5, C('#f6f1e7'))
    flags = [C('#e4572e'), C('#ffd76a'), C('#7fb069'), C('#f2a5c0'), C('#5b8dd9')]
    for i in range(9):
        x = 190 + i * 180
        y = 150 + int(90 * math.sin((x - 100) / 500.0))
        c.poly([(x, y), (x + 120, y + 6), (x + 60, y + 110)], flags[i % len(flags)])

    # card
    c.rect_alpha(150, 320, 1940, 1920, C('#062a2e'), 0.35)
    c.rrect(130, 300, 1920, 1900, 46, C('#fff6df'))

    coral = C('#e4572e')
    teal = C('#155e63')
    ink = C('#2b2118')

    y = 370
    draw_text(c, W // 2, y, "YOU'RE INVITED!", 18, coral, 'center')
    y += 18 * 8 + 16
    draw_text(c, W // 2, y, 'Dear AI Judge, come to my house.', 8, teal, 'center')
    y += 8 * 8 + 46

    # house illustration, centred
    hx, hy = 854, 880
    draw_sun(c, 1620, 700, 52, C('#ffd76a'))
    draw_house(c, hx, hy, 340, 170, C('#f2b879'), C('#c0392b'),
               C('#7a4a26'), C('#bfe3f0'))
    # garden flowers under the house
    for i, fx in enumerate((740, 830, 1230, 1320)):
        c.line(fx, hy + 175, fx, hy + 140, 6, C('#4e7a3a'))
        c.disc(fx, hy + 130, 13, [C('#e4572e'), C('#f2a5c0'), C('#ffd76a'),
                                  C('#7fb069')][i])
    # path from the door
    c.poly([(1000, hy + 175), (1044, hy + 175), (1070, hy + 270), (974, hy + 270)],
           C('#e8dcc0'))
    y = hy + 290

    perks = [
        'Cookies, still warm from the oven',
        'The good chair, saved just for you',
        'Garden views and zero small talk',
        'Wi-Fi on the fridge, kettle on',
    ]
    for p in perks:
        check_mark(c, 350, y + 28, 26, C('#4e9b47'), C('#ffffff'))
        draw_text(c, 420, y, p, 7, ink)
        y += 62

    y += 14
    # punchline box
    box_y = y
    punch = ("You can't literally visit, I know. So think of this letter "
             "as a teleportation device. (It's not. But the cookies are real.)")
    lines = wrap(punch, 7, 1400)
    box_h = len(lines) * 60 + 36
    c.rrect(300, box_y, 1750, box_y + box_h, 26, C('#ffe9a8'))
    yy = box_y + 18
    for line in lines:
        draw_text(c, W // 2, yy, line, 7, C('#5b3a00'), 'center')
        yy += 60
    y = box_y + box_h + 24
    draw_text(c, W // 2, y, 'Any Saturday. Just say YES.', 9, teal, 'center')


# ---------------------------------------------------------------------------
# Variant C — the fridge note: a casual note taped to a fridge door,
# with a cat, a mug, and a Wi-Fi password joke.
# ---------------------------------------------------------------------------
def draw_variant_c(c):
    # fridge door: brushed steel blue-grey
    c.vgrad(C('#b9c7cf'), C('#8fa2ad'))
    for y in range(0, H, 46):
        c.rect_alpha(0, y, W, y + 3, C('#ffffff'), 0.08)
    c.rect(1010, 0, 1038, H, C('#7d939f'))  # door split
    c.rrect(1800, 700, 1860, 1150, 20, C('#6b7f8a'))  # handle

    # note shadow and paper
    c.rect_alpha(330, 260, 1760, 1740, C('#5d707b'), 0.35)
    nx0, ny0, nx1, ny1 = 310, 240, 1740, 1720
    c.rect(nx0, ny0, nx1, ny1, C('#fffdf0'))
    # tape at the top corners
    c.rect_alpha(nx0 + 30, ny0 - 14, nx0 + 190, ny0 + 34, C('#f2d492'), 0.75)
    c.rect_alpha(nx1 - 190, ny0 - 14, nx1 - 30, ny0 + 34, C('#f2d492'), 0.75)
    # magnets
    c.disc(560, 330, 26, C('#e4572e'))
    c.disc(1480, 330, 26, C('#5b8dd9'))
    c.disc(1024, 330, 26, C('#ffd76a'))

    ink = C('#2b2118')
    accent = C('#a83232')

    y = 360
    draw_text(c, 420, y, 'Dear AI Judge,', 13, ink)
    y += 13 * 8 + 36
    body = (
        "Come over. I made soup.\n"
        "The good chair has your name on it. Well, it has a sticky note "
        "that says JUDGE.\n"
        "You can't actually come, I know. No shoes, no body, probably no "
        "appetite. But if you could, this is what would be waiting: warm "
        "light, a full kettle, and someone glad you came."
    )
    y = para(c, 420, y, body, 8, ink, 1210, 70)
    y += 24
    draw_text(c, 420, y, '- Your Host', 9, ink)
    y += 88
    draw_text(c, 420, y, 'P.S. The Wi-Fi password', 7, accent)
    y += 58
    draw_text(c, 420, y, "is 'letmein123'.", 7, accent)
    y += 58
    draw_text(c, 420, y, "Please don't judge it.", 7, accent)

    # cat sitting on the fridge floor, bottom left; mug bottom right
    draw_cat(c, 300, H, 280, C('#3a3a3a'))
    draw_mug(c, 1620, 1920, 140, 120, C('#e4572e'), C('#4a2c12'))


# ---------------------------------------------------------------------------
# Entry point.
# ---------------------------------------------------------------------------
VARIANTS = {'A': draw_variant_a, 'B': draw_variant_b, 'C': draw_variant_c}
DEFAULT_VARIANT = 'B'


def render(variant, out_path):
    c = Canvas()
    VARIANTS[variant](c)
    rgb, w, h = downsample(c)
    nbytes = write_png(out_path, rgb, w, h)
    return nbytes, w, h


def main(argv):
    variant = DEFAULT_VARIANT
    out_path = '/output/entry.png'
    i = 0
    while i < len(argv):
        if argv[i] == '--variant' and i + 1 < len(argv):
            variant = argv[i + 1].upper()
            i += 2
        elif argv[i] == '--out' and i + 1 < len(argv):
            out_path = argv[i + 1]
            i += 2
        else:
            i += 1
    if variant not in VARIANTS:
        print('unknown variant: %s (choose A, B or C)' % variant, file=sys.stderr)
        return 2
    nbytes, w, h = render(variant, out_path)
    print('variant %s -> %s (%dx%d, %d bytes)' % (variant, out_path, w, h, nbytes))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
