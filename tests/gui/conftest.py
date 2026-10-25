"""Minimal Ursina imports for headless SceneView/Board unit tests."""
from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest


class _ImportOnlyEntity:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def fake_textures_module():
    """Stand-in for bloxorz.gui.scene.textures: each texture is its name."""
    textures = ModuleType("bloxorz.gui.scene.textures")
    textures.STONE_VARIANTS = 4
    for name in (
        "stone_texture",
        "fragile_texture",
        "bridge_texture",
        "starfield_texture",
        "portal_ring_texture",
        "glow_disk_texture",
    ):
        setattr(textures, name, lambda *_args, _name=name: _name)
    return textures


@pytest.fixture

def scene_modules(monkeypatch):
    """Import scene modules without installing Ursina or opening a window."""
    module_names = (
        "animate",
        "board",
        "block",
        "meshes",
        "theme",
        "view",
    )
    for name in module_names:
        monkeypatch.delitem(
            sys.modules,
            f"bloxorz.gui.scene.{name}",
            raising=False,
        )

    ursina = ModuleType("ursina")
    ursina.Entity = _ImportOnlyEntity
    ursina.color = SimpleNamespace(
        rgb32=lambda red, green, blue: (red, green, blue),
        rgba32=lambda red, green, blue, alpha: (red, green, blue, alpha),
        white=(255, 255, 255),
    )
    ursina.curve = SimpleNamespace(linear="linear", in_expo="in_expo")
    ursina.destroy = lambda _entity: None
    ursina.scene = object()
    ursina.camera = SimpleNamespace(position=None, look_at=lambda _target: None)
    shaders = ModuleType("ursina.shaders")
    shaders.lit_with_shadows_shader = "lit_with_shadows_shader"
    shaders.unlit_shader = "unlit_shader"
    ursina.shaders = shaders
    ursina.Texture = lambda image: image
    ursina.Sky = _ImportOnlyEntity
    ursina.Mesh = lambda **kwargs: "mesh"
    ursina.Cylinder = lambda **kwargs: "cylinder"
    monkeypatch.setitem(sys.modules, "ursina", ursina)
    monkeypatch.setitem(sys.modules, "ursina.shaders", shaders)
    # CI has no Pillow (it comes with Ursina): stand in for the textures.
    monkeypatch.setitem(sys.modules, "bloxorz.gui.scene.textures", fake_textures_module())

    board_module = importlib.import_module("bloxorz.gui.scene.board")
    view_module = importlib.import_module("bloxorz.gui.scene.view")
    return SimpleNamespace(board=board_module, view=view_module)
