"""Procedural textures for the space theme: no image files or licenses needed.

Owner: VT3 | Task: 3.4.
"""

import math
import random
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter
from ursina import Texture

STONE_VARIANTS = 4


def _stone_image(seed, size=128):
    """Grayscale speckled stone with pits; a soft dark rim at the edges."""
    rng = random.Random(seed)
    image = Image.new("L", (size, size))
    image.putdata([rng.randint(165, 215) for _ in range(size * size)])
    image = image.filter(ImageFilter.GaussianBlur(1.3))

    # Broad light/dark blotches so the slab is not uniformly grey.
    blotches = Image.new("L", (size, size), 128)
    draw = ImageDraw.Draw(blotches)
    for _ in range(7):
        x, y, radius = rng.randrange(size), rng.randrange(size), rng.randint(14, 34)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=rng.randint(100, 160))
    blotches = blotches.filter(ImageFilter.GaussianBlur(12))
    image = ImageChops.add(image, blotches, scale=1.0, offset=-128)

    draw = ImageDraw.Draw(image)
    for _ in range(rng.randint(10, 18)):
        x, y = rng.randint(10, size - 10), rng.randint(10, size - 10)
        radius = rng.randint(2, 6)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=rng.randint(105, 140))
        # A light lip on the lower edge makes the pit read as a dent.
        draw.arc((x - radius, y - radius + 1, x + radius, y + radius + 1), 20, 160, fill=225)
    image = image.filter(ImageFilter.GaussianBlur(0.7))

    draw = ImageDraw.Draw(image)
    for inset, shade in ((0, 95), (1, 120), (2, 145)):
        draw.rectangle((inset, inset, size - 1 - inset, size - 1 - inset), outline=shade)
    return image


@lru_cache(maxsize=None)
def stone_texture(variant=0):
    """One of STONE_VARIANTS grayscale stones; each tile's color tints it."""
    return Texture(_stone_image(seed=7 + variant).convert("RGB"))


@lru_cache(maxsize=None)
def fragile_texture():
    """Stone split by dark cracks, for fragile tiles."""
    size = 128
    rng = random.Random(23)
    image = _stone_image(seed=5, size=size)
    draw = ImageDraw.Draw(image)
    for _ in range(4):
        x, y = rng.randint(20, size - 20), rng.randint(20, size - 20)
        angle = rng.uniform(0, 2 * math.pi)
        for _ in range(rng.randint(5, 9)):
            angle += rng.uniform(-0.8, 0.8)
            step = rng.randint(8, 16)
            nx = min(size - 4, max(4, x + step * math.cos(angle)))
            ny = min(size - 4, max(4, y + step * math.sin(angle)))
            draw.line((x, y, nx, ny), fill=55, width=2)
            draw.line((x + 1, y + 1, nx + 1, ny + 1), fill=215, width=1)
            x, y = nx, ny
    return Texture(image.convert("RGB"))


@lru_cache(maxsize=None)
def bridge_texture():
    """Metal panel with a bright frame and a center seam, for bridges."""
    size = 128
    image = Image.new("L", (size, size))
    image.putdata([150 + (x + y) % 9 for y in range(size) for x in range(size)])
    draw = ImageDraw.Draw(image)
    for inset, shade in ((0, 255), (1, 255), (2, 235), (5, 120), (6, 105)):
        draw.rectangle((inset, inset, size - 1 - inset, size - 1 - inset), outline=shade)
    draw.line((size // 2, 10, size // 2, size - 11), fill=110, width=2)
    for x, y in ((12, 12), (size - 13, 12), (12, size - 13), (size - 13, size - 13)):
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=230)
    return Texture(image.convert("RGB"))


@lru_cache(maxsize=None)
def starfield_texture():
    """Deep space: faint blue/violet nebulae, dense stars, a few glowing ones."""
    width, height = 2048, 1024
    rng = random.Random(11)

    nebula = Image.new("RGB", (width, height), (2, 3, 9))
    draw = ImageDraw.Draw(nebula)
    for _ in range(9):
        x, y = rng.randrange(width), rng.randrange(height // 4, 3 * height // 4)
        rx, ry = rng.randint(180, 420), rng.randint(70, 180)
        tone = rng.choice([(18, 26, 60), (34, 18, 58), (10, 34, 52)])
        draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=tone)
    nebula = nebula.filter(ImageFilter.GaussianBlur(90))

    glow = Image.new("RGB", (width, height), (0, 0, 0))
    stars = Image.new("RGB", (width, height), (0, 0, 0))
    glow_draw, star_draw = ImageDraw.Draw(glow), ImageDraw.Draw(stars)
    for _ in range(6000):
        x, y = rng.randrange(width), rng.randrange(height)
        bright = int(255 * rng.random() ** 2.2)
        if bright < 30:
            continue
        tint = (bright - rng.randint(0, 35), bright - rng.randint(0, 20), bright)
        star_draw.point((x, y), fill=tint)
        if bright > 230 and rng.random() < 0.2:
            glow_draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(80, 110, 210))
    glow = glow.filter(ImageFilter.GaussianBlur(1.5))
    image = ImageChops.add(ImageChops.add(nebula, glow), stars)
    return Texture(image)


def _radial(size, profile):
    """White RGBA image whose alpha follows profile(distance 0..1 from center)."""
    image = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    pixels = image.load()
    half = size / 2
    for y in range(size):
        for x in range(size):
            alpha = int(255 * max(0.0, min(1.0, profile(math.hypot(x - half, y - half) / half))))
            if alpha:
                pixels[x, y] = (255, 255, 255, alpha)
    return image


@lru_cache(maxsize=None)
def portal_ring_texture():
    """Glowing ring on transparency; the goal tints it."""
    def profile(d):
        ring = math.exp(-(((d - 0.72) / 0.07) ** 2))
        halo = 0.35 * math.exp(-(((d - 0.72) / 0.28) ** 2))
        return ring + halo

    return Texture(_radial(256, profile))


@lru_cache(maxsize=None)
def glow_disk_texture():
    """Soft round glow fading to transparent (floor light under the block)."""
    return Texture(_radial(128, lambda d: 0.85 * (1 - d) ** 1.4 if d < 1 else 0))
