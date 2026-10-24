from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture

def fragile_board(monkeypatch, scene_modules):
    board = scene_modules.board.Board()
    cell = (1, 2)
    defaults = ((2, -0.1, -1), (0.95, 0.2, 0.95))
    tile = SimpleNamespace(position=defaults[0], scale=defaults[1])
    board.fragile_tiles[cell] = tile
    board._fragile_defaults[cell] = defaults

    animations = []
    monkeypatch.setattr(
        scene_modules.board,
        "play_fragile_break",
        lambda target, on_done: animations.append(on_done),
    )
    return board, cell, tile, animations


def test_break_fragile_locks_board_and_calls_callback_once(fragile_board):
    board, cell, _, animations = fragile_board
    on_done = Mock()

    board.break_fragile(cell, on_done)

    assert board.is_busy()
    with pytest.raises(RuntimeError, match="already animating"):
        board.break_fragile(cell, Mock())
    with pytest.raises(RuntimeError, match="during animation"):
        board.reset_fragile()

    animations[0]()
    animations[0]()

    assert on_done.call_count == 1
    assert not board.is_busy()


def test_reset_fragile_restores_tile_after_break(fragile_board):
    board, cell, tile, animations = fragile_board
    board.break_fragile(cell, Mock())
    animations[0]()

    tile.position = (99, 99, 99)
    tile.scale = (0.95, 0.01, 0.95)
    board.reset_fragile()

    assert tile.position == (2, -0.1, -1)
    assert tile.scale == (0.95, 0.2, 0.95)
    assert cell not in board._broken_fragile
