"""A minimum plotting toolkit for the beach scene's evidence figures.

WHY THIS EXISTS. There is no matplotlib in this environment, and the standing
ruling is that every wave produces visual evidence. So this file draws axes,
polylines, bands and labels straight into a numpy RGB buffer and hands it to
PIL, which is already a dependency of `render.py`.

WHAT IT IS NOT. It is not physics and it never computes any. Everything it
draws is passed in, already in scene-linear SI units; the only arithmetic here
is data-to-pixel. The standing ruling "measure in scene-linear, never read a PNG
for physics" is kept by construction: nothing reads back out of these images.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    FONT = ImageFont.truetype(
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13)
    FONT_S = ImageFont.truetype(
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
    FONT_B = ImageFont.truetype(
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 15)
except OSError:                                   # pragma: no cover
    FONT = FONT_S = FONT_B = ImageFont.load_default()

BG = (250, 249, 246)
INK = (28, 30, 34)
GRID = (214, 212, 206)
MUTED = (120, 122, 128)


class Axes:
    """One rectangular plotting frame with linear x and y scales."""

    def __init__(self, img, box, xlim, ylim, title='', xlabel='', ylabel='',
                 y_up=True):
        self.img = img
        self.d = ImageDraw.Draw(img)
        self.x0, self.y0, self.x1, self.y1 = box          # pixels, l t r b
        self.xlim = xlim
        self.ylim = ylim
        self.y_up = y_up
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel

    # ---- data -> pixels
    def px(self, x):
        a, b = self.xlim
        return self.x0 + (np.asarray(x, float) - a) / (b - a) * (self.x1 - self.x0)

    def py(self, y):
        a, b = self.ylim
        f = (np.asarray(y, float) - a) / (b - a)
        return self.y1 - f * (self.y1 - self.y0) if self.y_up else \
            self.y0 + f * (self.y1 - self.y0)

    # ---- furniture
    def frame(self, xticks=None, yticks=None, xfmt='%g', yfmt='%g'):
        self.d.rectangle([self.x0, self.y0, self.x1, self.y1],
                         outline=INK, width=1)
        if xticks is not None:
            for t in xticks:
                px = float(self.px(t))
                self.d.line([px, self.y0, px, self.y1], fill=GRID)
                self.d.text((px, self.y1 + 4), xfmt % t, fill=MUTED,
                            font=FONT_S, anchor='ma')
        if yticks is not None:
            for t in yticks:
                py = float(self.py(t))
                self.d.line([self.x0, py, self.x1, py], fill=GRID)
                self.d.text((self.x0 - 6, py), yfmt % t, fill=MUTED,
                            font=FONT_S, anchor='rm')
        if self.title:
            self.d.text((self.x0, self.y0 - 22), self.title, fill=INK,
                        font=FONT_B, anchor='ls')
        if self.xlabel:
            self.d.text(((self.x0 + self.x1) / 2, self.y1 + 22), self.xlabel,
                        fill=INK, font=FONT, anchor='ma')
        if self.ylabel:
            tmp = Image.new('RGB', (self.y1 - self.y0, 20), BG)
            ImageDraw.Draw(tmp).text((tmp.width / 2, 10), self.ylabel, fill=INK,
                                     font=FONT, anchor='mm')
            self.img.paste(tmp.rotate(90, expand=True),
                           (self.x0 - 52, self.y0))

    # ---- marks
    def line(self, x, y, colour, width=2, dash=None, clip=True):
        px = np.atleast_1d(self.px(x))
        py = np.atleast_1d(self.py(y))
        if clip:
            # Drop the samples outside the frame rather than drawing them: a
            # curve that leaves the axes and is drawn anyway lands on the title.
            keep = ((px >= self.x0 - 1) & (px <= self.x1 + 1)
                    & (py >= self.y0 - 1) & (py <= self.y1 + 1))
            px, py = px[keep], py[keep]
        pts = [(float(a), float(b)) for a, b in zip(px, py)
               if np.isfinite(a) and np.isfinite(b)]
        if len(pts) < 2:
            return
        if dash is None:
            self.d.line(pts, fill=colour, width=width, joint='curve')
        else:
            on, off = dash
            acc = 0.0
            for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
                seg = float(np.hypot(bx - ax, by - ay))
                t = 0.0
                while t < seg:
                    step = min(on if (acc // on) % 2 == 0 else off, seg - t)
                    if (acc // on) % 2 == 0:
                        f0, f1 = t / seg, (t + step) / seg
                        self.d.line([ax + (bx - ax) * f0, ay + (by - ay) * f0,
                                     ax + (bx - ax) * f1, ay + (by - ay) * f1],
                                    fill=colour, width=width)
                    t += step
                    acc += step

    def band(self, x0, x1, colour):
        self.d.rectangle([float(self.px(x0)), self.y0,
                          float(self.px(x1)), self.y1], fill=colour)

    def fill_between(self, x, ylo, yhi, colour):
        px = np.atleast_1d(self.px(x))
        pl = np.atleast_1d(self.py(ylo))
        ph = np.atleast_1d(self.py(yhi))
        pts = ([(float(a), float(b)) for a, b in zip(px, ph)]
               + [(float(a), float(b)) for a, b in zip(px[::-1], pl[::-1])])
        if len(pts) > 2:
            self.d.polygon(pts, fill=colour)

    def marker(self, x, y, colour, r=4):
        cx, cy = float(self.px(x)), float(self.py(y))
        self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colour,
                       outline=(255, 255, 255))

    def vline(self, x, colour, width=1, dash=(6, 5)):
        self.line([x, x], list(self.ylim), colour, width, dash)

    def hline(self, y, colour, width=1, dash=(6, 5)):
        self.line(list(self.xlim), [y, y], colour, width, dash)

    def text(self, x, y, s, colour=INK, anchor='ls', font=None):
        self.d.text((float(self.px(x)), float(self.py(y))), s, fill=colour,
                    font=font or FONT_S, anchor=anchor)

    def image(self, rgb, extent=None):
        """Paste an (ny, nx, 3) uint8 array to fill the axes box."""
        w, h = self.x1 - self.x0, self.y1 - self.y0
        im = Image.fromarray(np.asarray(rgb, np.uint8)).resize(
            (int(w), int(h)), Image.NEAREST)
        self.img.paste(im, (int(self.x0), int(self.y0)))


def canvas(w, h):
    return Image.new('RGB', (int(w), int(h)), BG)


def caption(img, lines, x=40, y=None, colour=INK):
    d = ImageDraw.Draw(img)
    if y is None:
        y = img.height - 18 * len(lines) - 16
    for i, s in enumerate(lines):
        d.text((x, y + 18 * i), s, fill=colour, font=FONT_S)


def legend(ax, entries, x, y, dy=17):
    """entries: [(colour, label), ...] placed in DATA coordinates."""
    for i, (col, lab) in enumerate(entries):
        px, py = float(ax.px(x)), float(ax.py(y)) + i * dy
        ax.d.line([px, py, px + 24, py], fill=col, width=3)
        ax.d.text((px + 30, py), lab, fill=INK, font=FONT_S, anchor='lm')


def save(img, path):
    img.save(path)
    return path
