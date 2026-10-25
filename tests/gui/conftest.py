"""Minimal Ursina imports for headless SceneView/Board unit tests."""
from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace

import pytest


class _ImportOnlyEntity:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


@pytest.fixture

def scene_modules(monkeypatch):
    """Import scene modules without installing Ursina or opening a window."""
    module_names = (
        "animate",
        "board",
        "block",
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
        white=(255, 255, 255),
    )
    ursina.curve = SimpleNamespace(linear="linear", in_expo="in_expo")
    ursina.destroy = lambda _entity: None
    ursina.scene = object()
    ursina.camera = SimpleNamespace(position=None, look_at=lambda _target: None)
    shaders = ModuleType("ursina.shaders")
    shaders.lit_with_shadows_shader = "lit_with_shadows_shader"
    ursina.shaders = shaders
    monkeypatch.setitem(sys.modules, "ursina", ursina)
    monkeypatch.setitem(sys.modules, "ursina.shaders", shaders)

    board_module = importlib.import_module("bloxorz.gui.scene.board")
    view_module = importlib.import_module("bloxorz.gui.scene.view")
    return SimpleNamespace(board=board_module, view=view_module)
