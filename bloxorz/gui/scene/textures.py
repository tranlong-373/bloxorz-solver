"""Procedural textures for the space theme: no image files or licenses needed.

Owner: VT3 | Task: 3.4.
"""

import math
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter
from ursina import Texture


@lru_cache(maxsize=None)
def stone_texture():
    """Grey speckled stone with pits and a darker bevelled rim.

    Grayscale so each tile's color tints it (floor, fragile, bridge).
    """
    size = 128
    rng = random.Random(7)
    image = Image.new("L", (size, size))
    image.putdata([rng.randint(175, 215) for _ in range(size * size)])
    image = image.filter(ImageFilter.GaussianBlur(1.2))

    draw = ImageDraw.Draw(image)
    for _ in range(16):
        x, y = rng.randint(12, size - 12), rng.randint(12, size - 12)
        radius = rng.randint(2, 6)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=rng.randint(120, 150))
    image = image.filter(ImageFilter.GaussianBlur(0.8))

    # Bevel: light inner rim on top/left, dark outer rim all around.
    draw = ImageDraw.Draw(image)
    for inset, shade in ((0, 70), (1, 90), (2, 115), (3, 140)):
        draw.rectangle((inset, inset, size - 1 - inset, size - 1 - inset), outline=shade)
    draw.line((5, 5, size - 6, 5), fill=235)
    draw.line((5, 5, 5, size - 6), fill=235)
    return Texture(image.convert("RGB"))


@lru_cache(maxsize=None)
def starfield_texture():
    """Deep blue-black sky with scattered stars for the sky dome."""
    width, height = 2048, 1024
    rng = random.Random(11)
    image = Image.new("RGB", (width, height), (3, 5, 12))
    draw = ImageDraw.Draw(image)
    for _ in range(2600):
        x, y = rng.randrange(width), rng.randrange(height)
        bright = rng.randint(80, 255)
        tint = (bright - rng.randint(0, 40), bright - rng.randint(0, 25), bright)
        if rng.random() < 0.08:
            draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill=tint)
        else:
            draw.point((x, y), fill=tint)
    return Texture(image)


@lru_cache(maxsize=None)
def portal_ring_texture():
    """White glowing ring on transparency; the goal tints it."""
    size = 256
    image = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    pixels = image.load()
    center, ring_radius, width = size / 2, size * 0.36, size * 0.035
    for y in range(size):
        for x in range(size):
            distance = math.hypot(x - center, y - center)
            glow = math.exp(-(((distance - ring_radius) / width) ** 2))
            halo = 0.35 * math.exp(-(((distance - ring_radius) / (width * 4)) ** 2))
            alpha = min(255, int(255 * (glow + halo)))
            if alpha:
                pixels[x, y] = (255, 255, 255, alpha)
    return Texture(image)
