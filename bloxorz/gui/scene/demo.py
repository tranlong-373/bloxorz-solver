"""Standalone demonstration for Bloxorz scene animations.

Owner: VT3 | Tasks: 3.1, 3.2, 3.3a, 3.3b, 3.3c.

Run:
    python -m bloxorz.gui.scene.demo stages/fixtures/basic_01.json
    python -m bloxorz.gui.scene.demo stages/original/stage_20.json  (C key)
    python -m bloxorz.gui.scene.demo stages/bench/g4_01.json  (split/merge)

Controls:
    Arrow keys: Move the block
    R: Reset the demo
    F: Test falling
    L: Test lying safely across F
    B: Test fragile break
    C: Test a switch closing the bridge under the block
    Tab: Switch the controlled cube while split (VT4 maps Space in the app)
    T: Run 10 consecutive rolls
    G: Run 10 rolls ending at Goal
    W: Preview the win animation
    1/2/3: Preview block poses
"""

import sys
from collections import deque

from ursina import (
    AmbientLight,
    DirectionalLight,
    Text,
    Ursina,
    window,
)

from bloxorz.engine.rules import Outcome, footprint, is_goal, step
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction, Pose, State

from .view import SceneView


stage = None
scene_view = None
current_state = None
auto_running = False
has_fallen = False
has_won = False
selected_pos = None  # demo only: the split cube the arrow keys move
status_text = None


def set_status(message):
    """Show control feedback in both the terminal and demo window."""
    print(message)
    if status_text is not None:
        status_text.text = message


def test_ten_rolls(to_goal=False):
    """Run 10 Engine-validated rolls sequentially."""
    global current_state, auto_running

    if auto_running or scene_view.is_busy():
        set_status("Animation is still running")
        return

    if has_fallen or has_won:
        set_status("Press R to reset first")
        return

    if stage.id != "basic_01":
        set_status("T/G demo requires stages/fixtures/basic_01.json")
        return

    # Reset to the initial State.
    current_state = State(
        pose=Pose.STANDING,
        pos=stage.start,
        bridges_open=stage.initial_bridges_open(),
    )
    scene_view.show_state(current_state)

    # T/G: Test both rotation axes and all three block poses.
    # T returns to the start; G ends at Goal.
    # First 8 moves exercise both rotation axes and VERTICAL pose.
    actions = [
        Direction.RIGHT,
        Direction.UP,
        Direction.RIGHT,
        Direction.DOWN,
        Direction.UP,
        Direction.LEFT,
        Direction.DOWN,
        Direction.LEFT,
        Direction.RIGHT,
    ]

    # T returns to the start; G finishes standing on Goal.
    actions.append(Direction.RIGHT if to_goal else Direction.LEFT)


    auto_running = True
    completed = 0

    set_status("G: running 10 rolls to Goal" if to_goal else "T: running 10 rolls")

    def run_next():
        nonlocal completed
        global current_state, auto_running, has_won

        if completed == len(actions):
            set_status(
                "G: 10 rolls complete" if to_goal else "T: complete, 10/10 rolls"
            )

            if not to_goal:
                auto_running = False
                return

            # Verify that the Engine recognizes the final Goal.
            if not is_goal(stage, current_state):
                auto_running = False
                set_status("G: failed, final position is not Goal")
                return

            set_status("Goal reached; playing win animation")

            def win_finished():
                global auto_running, has_won

                has_won = True
                auto_running = False
                set_status("G: passed, 10 rolls + win. Press R.")

            scene_view.show_win(on_done=win_finished)
            return

        direction = actions[completed]
        before = current_state
        action = Action(direction)

        # Only demo.py calls Engine.
        result = step(stage, before, action)

        if result.outcome != Outcome.MOVED or result.state is None:
            auto_running = False
            set_status(f"Test failed at step {completed + 1}: {result.reason}")
            return

        def finished():
            nonlocal completed
            global current_state

            current_state = result.state
            completed += 1

            set_status(f"Step {completed}/10: {direction.name}")

            # The next move starts only after on_done().
            run_next()

        scene_view.animate_step(
            before,
            action,
            result,
            on_done=finished,
        )

    run_next()


def reset_demo():
    """Restore the initial stage State after a fall or win."""
    global current_state, has_fallen, has_won, selected_pos

    if scene_view.is_busy() or auto_running:
        set_status("Cannot reset while an animation is running")
        return

    current_state = State(
        pose=Pose.STANDING,
        pos=stage.start,
        bridges_open=stage.initial_bridges_open(),
    )

    selected_pos = None
    scene_view.board.reset_fragile()
    scene_view.show_state(current_state)
    has_fallen = False
    has_won = False

    set_status(f"Demo reset: {current_state.pos}")


def _select_cube(index):
    """Mark split cube index (0/1) of current_state as controlled."""
    global selected_pos
    selected_pos = (current_state.pos, current_state.cube2)[index]
    scene_view.set_selected(index)


def _selected_index(state):
    cubes = (state.pos, state.cube2)
    return cubes.index(selected_pos) if selected_pos in cubes else 0


def _describe(state):
    if state.pose is None:
        return f"split cubes at {state.pos} and {state.cube2}"
    return f"{state.pose.name} at {state.pos}"


def test_win():
    """Preview win animation at the goal tile."""
    global current_state, has_won

    if scene_view.is_busy() or auto_running:
        set_status("Cannot preview win during animation")
        return

    if has_fallen or has_won:
        set_status("Press R to reset first")
        return

    # Use the goal position only for an animation preview.
    current_state = State(
        pose=Pose.STANDING,
        pos=stage.goal,
        bridges_open=stage.initial_bridges_open(),
    )

    scene_view.show_state(current_state)

    def finished():
        global has_won
        has_won = True
        set_status("Win animation completed. Press R to reset.")

    scene_view.show_win(on_done=finished)


def test_fragile_break():
    """Use an Engine-validated move that stands upright on an F tile."""
    global current_state, has_fallen

    if scene_view.is_busy() or auto_running:
        set_status("Cannot test fragile break during animation")
        return
    if has_fallen or has_won:
        set_status("Press R to reset first")
        return

    action = Action(Direction.LEFT)
    candidate = None
    for r, row in enumerate(stage.grid):
        for c, symbol in enumerate(row):
            if symbol != "F":
                continue

            before_cells = ((r, c + 1), (r, c + 2))
            bridges_open = stage.initial_bridges_open()
            supported = all(
                (
                    stage.bridge_at.get(cell) in bridges_open
                    if stage.bridge_at.get(cell) is not None
                    else stage.cell(cell) != "."
                )
                for cell in before_cells
            )
            if not supported:
                continue

            before = State(
                pose=Pose.HORIZONTAL,
                pos=(r, c + 1),
                bridges_open=bridges_open,
            )
            result = step(stage, before, action)
            if result.reason == "fragile_broke":
                candidate = (before, result)
                break
        if candidate is not None:
            break

    if candidate is None:
        set_status("No Engine-valid fragile-break position on this stage")
        return

    before, result = candidate
    current_state = before
    scene_view.show_state(before)

    def fall_finished():
        global has_fallen
        has_fallen = True
        set_status("Fragile tile broke; block fell. Press R to reset.")

    scene_view.show_illegal_step(before, action, result, on_done=fall_finished)


def _find_bridge_closed_move():
    """Search Engine-reachable intact states for a bridge_closed move."""
    start = State(
        pose=Pose.STANDING,
        pos=stage.start,
        bridges_open=stage.initial_bridges_open(),
    )
    seen = {start}
    queue = deque([start])
    while queue:
        before = queue.popleft()
        # Explore split states too, but only show intact-block cases (3.3b).
        if before.pose is None:
            actions = [Action(d, cube=cube) for d in Direction for cube in (0, 1)]
        else:
            actions = [Action(d) for d in Direction]
        for action in actions:
            result = step(stage, before, action)
            if result.reason == "bridge_closed" and before.pose is not None:
                return before, action, result
            if result.outcome is Outcome.MOVED and result.state not in seen:
                seen.add(result.state)
                queue.append(result.state)
    return None


def test_bridge_closed():
    """Show switch -> bridge closes -> block falls, as reported by Engine."""
    global current_state

    if scene_view.is_busy() or auto_running:
        set_status("Cannot test bridge closing during animation")
        return
    if has_fallen or has_won:
        set_status("Press R to reset first")
        return

    candidate = _find_bridge_closed_move()
    if candidate is None:
        set_status("No intact-block bridge_closed move; try stage_20.json")
        return

    before, action, result = candidate
    current_state = before
    scene_view.show_state(before)
    set_status(f"C: {action.direction.name} triggers {', '.join(result.events)}")

    def fall_finished():
        global has_fallen
        has_fallen = True
        set_status("Bridge closed under the block; it fell. Press R to reset.")

    scene_view.show_illegal_step(before, action, result, on_done=fall_finished)


def test_fragile_safe_crossing():
    """Show a legal lying move across F without breaking the tile."""
    global current_state

    if scene_view.is_busy() or auto_running:
        set_status("Cannot test fragile crossing during animation")
        return
    if has_fallen or has_won:
        set_status("Press R to reset first")
        return

    before = State(
        pose=Pose.STANDING,
        pos=stage.start,
        bridges_open=stage.initial_bridges_open(),
    )
    action = Action(Direction.RIGHT)
    result = step(stage, before, action)
    if (
        result.outcome is not Outcome.MOVED
        or result.state is None
        or result.state.pose is Pose.STANDING
        or not any(stage.cell(cell) == "F" for cell in footprint(result.state))
    ):
        set_status("No safe lying move across F at the stage start")
        return

    current_state = before
    scene_view.show_state(before)

    def finished():
        global current_state
        current_state = result.state
        set_status("L: block crossed F while lying; tile stayed intact")

    scene_view.animate_step(before, action, result, on_done=finished)


def input(key):
    global current_state, has_fallen

    # R: reset the demo after a fall.
    if key == "r":
        reset_demo()
        return

    if key == "f":
        if stage.id != "basic_01":
            set_status("F test requires stages/fixtures/basic_01.json")
            return

        if auto_running or scene_view.is_busy():
            set_status("Cannot test fall during animation")
            return

        reset_demo()
        key = "up arrow"

    if key == "w":
        test_win()
        return

    if has_won:
        set_status("Win animation completed. Press R to reset.")
        return

    # Block further movement after the fall.
    if has_fallen:
        set_status("Block has fallen. Press R to reset.")
        return

    if key == "b":
        test_fragile_break()
        return

    if key == "c":
        test_bridge_closed()
        return

    if key == "l":
        test_fragile_safe_crossing()
        return

    # T: run the 10-roll animation test.
    if key == "t":
        test_ten_rolls()
        return

    if key == "g":
        test_ten_rolls(to_goal=True)
        return

    # Ignore manual input during the automatic test.
    if auto_running:
        return

    directions = {
        "right arrow": Direction.RIGHT,
        "left arrow": Direction.LEFT,
        "up arrow": Direction.UP,
        "down arrow": Direction.DOWN,
        "space": Direction.RIGHT,
    }

    # Tab: switch the controlled cube while split.
    if key == "tab":
        if current_state.pose is None and not scene_view.is_busy():
            index = 1 - _selected_index(current_state)
            _select_cube(index)
            set_status(f"Tab: controlling cube at {selected_pos}")
        return

    if key in directions:
        if scene_view.is_busy():
            set_status("Animation is still running")
            return

        before = current_state
        cube = _selected_index(before) if before.pose is None else None
        action = Action(directions[key], cube=cube)
        result = step(stage, before, action)

        # Engine decides why the move fell; Scene only presents that result.
        if result.outcome is Outcome.ILLEGAL:
            set_status(f"Fall detected: {action.direction.name} ({result.reason})")

            def fall_finished():
                global has_fallen

                has_fallen = True
                set_status("Fall animation completed. Press R to reset.")

            scene_view.show_illegal_step(before, action, result, on_done=fall_finished)
            return

        if result.outcome != Outcome.MOVED or result.state is None:
            set_status(f"Move rejected: {result.reason}")
            return

        def finished():
            global current_state, has_won, selected_pos

            # Update State only after the roll animation finishes.
            current_state = result.state

            if current_state.pose is None:
                if before.pose is not None:
                    selected_pos = current_state.pos
                elif selected_pos == (before.pos, before.cube2)[cube]:
                    # The controlled cube moved; follow it to its new cell.
                    stationary = (before.pos, before.cube2)[1 - cube]
                    cells = (current_state.pos, current_state.cube2)
                    selected_pos = cells[1] if cells[0] == stationary else cells[0]
                _select_cube(_selected_index(current_state))
            else:
                selected_pos = None

            set_status(f"Roll finished: {_describe(current_state)}")

            # The Engine provides a separate goal check.
            if is_goal(stage, current_state):
                set_status("Goal reached; playing win animation")

                def win_finished():
                    global has_won

                    has_won = True
                    set_status("Win completed. Press R to reset.")

                scene_view.show_win(on_done=win_finished)

        scene_view.animate_step(
            before,
            action,
            result,
            on_done=finished,
        )
        return

    # 1/2/3: display block poses for testing.
    poses = {
        "1": Pose.STANDING,
        "2": Pose.HORIZONTAL,
        "3": Pose.VERTICAL,
    }

    if key in poses and not scene_view.is_busy():
        sample_state = State(
            pose=poses[key],
            pos=stage.start,
            bridges_open=stage.initial_bridges_open(),
        )

        current_state = sample_state
        scene_view.show_state(sample_state)
        set_status(f"Displaying pose: {poses[key].name}")


def main():
    global stage, scene_view, current_state, status_text

    if len(sys.argv) != 2:
        print(
            "Usage: python -m bloxorz.gui.scene.demo "
            "stages/fixtures/basic_01.json"
        )
        return

    # Load an actual stage using VT4's loader.
    stage = load_stage(sys.argv[1])

    # The standalone demo owns the Ursina application.
    app = Ursina()
    AmbientLight(color=(0.65, 0.65, 0.65, 1))

    sun = DirectionalLight()
    sun.look_at((1, -2, -1))
    window.title = f"Bloxorz Scene Demo - {stage.id}"

    scene_view = SceneView()

    initial_state = State(
        pose=Pose.STANDING,
        pos=stage.start,
        bridges_open=stage.initial_bridges_open(),
    )

    current_state = initial_state

    # SceneView frames the official camera; the demo uses it as is.
    scene_view.load_stage(stage, initial_state)

    Text(
        text=(
            "Arrows: Move | T: 10 rolls | G: 10 + Goal\n"
            "F: Fall | L: Lie across F | B: Fragile break\n"
            "C: Bridge closes | Tab: Switch cube\n"
            "W: Preview Win | R: Reset | 1/2/3: Pose"
        ),
        position=(-0.85, 0.45),
        scale=0.75,
    )

    status_text = Text(
        text="Ready | T/G require basic_01.json",
        position=(-0.85, 0.355),
        scale=0.7,
        color=(1, 0.85, 0.35, 1),
    )

    print("Loaded stage:", stage.id)
    print("Press 1, 2 or 3 to change block pose.")
    app.run()


if __name__ == "__main__":
    main()
