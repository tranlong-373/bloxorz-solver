from types import SimpleNamespace

from bloxorz.model import Action, Direction


def test_fragile_fall_orders_roll_break_drop_and_callback(monkeypatch, scene_modules):
    events = []
    view_module = scene_modules.view
    scene_view = view_module.SceneView

    def break_fragile(cell, on_done):
        events.append(("break", cell))
        on_done()
        on_done()

    scene = scene_view.__new__(scene_view)
    scene.board = SimpleNamespace(is_busy=lambda: False, break_fragile=break_fragile)
    scene.block = SimpleNamespace(entity=object())
    scene._busy = False
    scene._animation_id = 4
    scene._state = None

    def show_state(state):
        scene._state = state
        events.append(("state", state))

    scene.show_state = show_state
    scene.is_busy = scene_view.is_busy.__get__(scene)

    def roll(_block, _direction, on_done):
        events.append("roll")
        on_done()
        on_done()

    def drop(_block, on_done):
        events.append("drop")
        on_done()
        on_done()

    monkeypatch.setattr(view_module, "play_roll", roll)
    monkeypatch.setattr(view_module, "play_drop", drop)

    scene.show_fragile_fall(
        before="old-state",
        action=Action(Direction.LEFT),
        cell=(1, 2),
        on_done=lambda: events.append("done"),
    )

    assert events == [
        ("state", "old-state"),
        "roll",
        ("break", (1, 2)),
        "drop",
        "done",
    ]
    assert not scene.is_busy()


def test_stale_fragile_roll_does_not_start_tile_animation(monkeypatch, scene_modules):
    events = []
    view_module = scene_modules.view
    scene_view = view_module.SceneView
    scene = scene_view.__new__(scene_view)
    scene.board = SimpleNamespace(
        is_busy=lambda: False,
        break_fragile=lambda *_args, **_kwargs: events.append("break"),
    )
    scene.block = SimpleNamespace(entity=object())
    scene._busy = False
    scene._animation_id = 4
    scene._state = None
    scene.show_state = lambda state: (
        setattr(scene, "_state", state),
        events.append(state),
    )
    scene.is_busy = scene_view.is_busy.__get__(scene)

    roll_finished = []
    monkeypatch.setattr(
        view_module,
        "play_roll",
        lambda _block, _direction, on_done: roll_finished.append(on_done),
    )
    monkeypatch.setattr(view_module, "play_drop", lambda *_args: None)

    scene.show_fragile_fall(
        "old-state",
        Action(Direction.LEFT),
        (1, 2),
        lambda: events.append("done"),
    )
    scene._animation_id += 1
    scene._state = "new-state"
    roll_finished[0]()

    assert "break" not in events
    assert "done" not in events
    assert events[-1] == "new-state"
    assert not scene._busy
