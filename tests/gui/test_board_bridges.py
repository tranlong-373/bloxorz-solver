"""Unit tests for Board bridge and switch event sequencing.

The fake Entity below exercises Board's orchestration only. The actual Ursina
visual sequence is checked separately with the soft_toggle_01 demo.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from bloxorz.loader import load_stage
from bloxorz.model import Pose, State


ROOT = Path(__file__).resolve().parents[2]
SOFT_TOGGLE_STAGE = ROOT / "stages" / "fixtures" / "soft_toggle_01.json"


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


class FakeAnimation:
    def __init__(self, entity, target, duration):
        self.entity = entity
        self.target = tuple(target)
        self.duration = duration
        self.callbacks = []
        self.entity.scale = self.target
        self.entity.animations.append(self)

    def append(self, callback):
        self.callbacks.append(callback)

    def finish(self):
        for callback in tuple(self.callbacks):
            callback()


class FakeEntity:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.enabled = True
        self.animations = []

    def animate_scale(self, target, duration):
        return FakeAnimation(self, target, duration)


@pytest.fixture

def board_module(monkeypatch):
    """Load Board against tiny Ursina stand-ins, without opening a GUI."""
    for name in (
        "bloxorz.gui.scene.board",
        "bloxorz.gui.scene.animate",
        "bloxorz.gui.scene.meshes",
        "bloxorz.gui.scene.theme",
    ):
        monkeypatch.delitem(sys.modules, name, raising=False)

    ursina = ModuleType("ursina")
    ursina.Entity = FakeEntity
    ursina.color = SimpleNamespace(
        rgb32=lambda red, green, blue: (red, green, blue),
        rgba32=lambda red, green, blue, alpha: (red, green, blue, alpha),
        white=(255, 255, 255),
    )
    ursina.destroy = lambda entity: None
    ursina.curve = SimpleNamespace(linear="linear", in_expo="in_expo")
    ursina.scene = object()
    shaders = ModuleType("ursina.shaders")
    shaders.lit_with_shadows_shader = "lit_with_shadows_shader"
    shaders.unlit_shader = "unlit_shader"
    ursina.shaders = shaders
    ursina.Texture = lambda image: image
    ursina.Mesh = lambda **kwargs: "mesh"
    ursina.Cylinder = lambda **kwargs: "cylinder"
    monkeypatch.setitem(sys.modules, "ursina", ursina)
    monkeypatch.setitem(sys.modules, "ursina.shaders", shaders)
    # CI has no Pillow (it comes with Ursina): stand in for the textures.
    monkeypatch.setitem(sys.modules, "bloxorz.gui.scene.textures", fake_textures_module())

    return importlib.import_module("bloxorz.gui.scene.board")


def _built_board(board_module):
    stage = load_stage(SOFT_TOGGLE_STAGE)
    board = board_module.Board()
    board.build(stage)
    return board, stage


def test_bridge_visibility_tracks_engine_state(board_module):
    board, stage = _built_board(board_module)
    bridge_tile = board.bridge_tiles["b1"][0]

    assert not bridge_tile.enabled
    assert bridge_tile.scale == (0, 0, 0)

    board.show_state(
        State(Pose.STANDING, stage.start, bridges_open=frozenset({"b1"}))
    )
    assert bridge_tile.enabled
    assert bridge_tile.scale == board_module.TILE_SCALE

    board.show_state(State(Pose.STANDING, stage.start))
    assert not bridge_tile.enabled
    assert bridge_tile.scale == (0, 0, 0)


def test_switch_then_bridge_events_finish_once_and_release_busy(board_module):
    board, _ = _built_board(board_module)
    switch_entity, base_scale = board.switch_entities["sw1"][0]
    bridge_tile = board.bridge_tiles["b1"][0]
    completed = []

    board.animate_events(
        ("switch:sw1", "bridge:b1:open"),
        lambda: completed.append("done"),
    )

    assert board.is_busy()
    assert len(switch_entity.animations) == 1
    assert switch_entity.animations[0].target == tuple(
        component * 1.2 for component in base_scale
    )
    assert not bridge_tile.enabled

    with pytest.raises(RuntimeError, match="already animating"):
        board.animate_events((), lambda: None)

    switch_entity.animations[0].finish()
    assert board.is_busy()
    assert bridge_tile.enabled
    bridge_animations = [
        tile.animations[-1] for tile in board.bridge_tiles["b1"]
    ]
    assert len(bridge_animations) == 2
    assert bridge_animations[0].target == board_module.TILE_SCALE
    assert bridge_animations[0].duration == board_module.BRIDGE_DURATION

    # A repeated callback from one tile must not finish the other tile's work.
    bridge_animations[0].finish()
    bridge_animations[0].finish()
    assert board.is_busy()
    assert completed == []

    bridge_animations[1].finish()
    bridge_animations[1].finish()
    assert completed == ["done"]
    assert not board.is_busy()


def test_closed_bridge_is_hidden_after_close_animation(board_module):
    board, stage = _built_board(board_module)
    board.show_state(
        State(Pose.STANDING, stage.start, bridges_open=frozenset({"b1"}))
    )
    bridge_tile = board.bridge_tiles["b1"][0]
    completed = []

    board.animate_events(("bridge:b1:close",), lambda: completed.append(True))

    assert bridge_tile.enabled
    close_animations = [
        tile.animations[-1] for tile in board.bridge_tiles["b1"]
    ]
    assert len(close_animations) == 2
    assert close_animations[0].target == (0, 0, 0)

    close_animations[0].finish()
    assert bridge_tile.enabled
    assert completed == []

    close_animations[1].finish()
    assert not bridge_tile.enabled
    assert completed == [True]
    assert not board.is_busy()


def test_clear_invalidates_pending_bridge_animation_callback(board_module):
    board, _ = _built_board(board_module)
    bridge_tile = board.bridge_tiles["b1"][0]
    completed = []

    board.animate_events(("bridge:b1:open",), lambda: completed.append(True))
    pending_animation = bridge_tile.animations[-1]
    board.clear()
    pending_animation.finish()

    assert completed == []
    assert not board.is_busy()
