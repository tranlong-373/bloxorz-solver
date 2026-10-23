"""Standalone demonstration for Bloxorz scene animations.

Owner: VT3 | Tasks: 3.1, 3.2.

Run:
    python -m bloxorz.gui.scene.demo stages/fixtures/basic_01.json

Controls:
    Arrow keys: Move the block
    R: Reset the demo
    F: Test falling
    B: Test fragile break (load fragile_01.json)
    T: Run 10 consecutive rolls
    G: Run 10 rolls ending at Goal
    W: Preview the win animation
    1/2/3: Preview block poses
"""

import sys

from ursina import (
    AmbientLight,
    DirectionalLight,
    Text,
    Ursina,
    camera,
    window,
)

from bloxorz.engine.rules import ROLL, Outcome, is_goal, step
from bloxorz.loader import load_stage
from bloxorz.model import Action, Direction, Pose, State

from .view import SceneView


stage = None
scene_view = None
current_state = None
auto_running = False
has_fallen = False
has_won = False


def test_ten_rolls(to_goal=False):
    """Run 10 Engine-validated rolls sequentially."""
    global current_state, auto_running

    if auto_running or scene_view.is_busy():
        print("Another animation is running")
        return

    if has_fallen or has_won:
        print("Press R to reset first")
        return

    if stage.id != "basic_01":
        print("The T/G tests use basic_01.json")
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

    print("START:", "10-roll GOAL test" if to_goal else "10-roll test")

    def run_next():
        nonlocal completed
        global current_state, auto_running, has_won

        if completed == len(actions):
            print("TEST COMPLETED: 10/10 rolls")
            print("Final State:", current_state)

            if not to_goal:
                auto_running = False
                return

            # Verify that the Engine recognizes the final Goal.
            if not is_goal(stage, current_state):
                auto_running = False
                print("TEST FAILED: Final State is not Goal")
                return

            print("GOAL reached! Starting win animation.")

            def win_finished():
                global auto_running, has_won

                has_won = True
                auto_running = False
                print("GOAL TEST PASSED: 10 rolls + win")
                print("Press R to reset.")

            scene_view.show_win(on_done=win_finished)
            return

        direction = actions[completed]
        before = current_state
        action = Action(direction)

        # Only demo.py calls Engine.
        result = step(stage, before, action)

        if result.outcome != Outcome.MOVED or result.state is None:
            auto_running = False
            print(
                f"TEST FAILED at step {completed + 1}:",
                result.reason,
            )
            return

        def finished():
            nonlocal completed
            global current_state

            current_state = result.state
            completed += 1

            print(
                f"Step {completed}/10:",
                direction.name,
                current_state.pose.name,
                current_state.pos,
            )

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
    global current_state, has_fallen, has_won

    if scene_view.is_busy() or auto_running:
        print("Cannot reset during animation")
        return

    current_state = State(
        pose=Pose.STANDING,
        pos=stage.start,
        bridges_open=stage.initial_bridges_open(),
    )

    scene_view.board.reset_fragile()
    scene_view.show_state(current_state)
    has_fallen = False
    has_won = False

    print("Demo reset:", current_state.pos)


def test_win():
    """Preview win animation at the goal tile."""
    global current_state, has_won

    if scene_view.is_busy() or auto_running:
        print("Cannot preview win during animation")
        return

    if has_fallen or has_won:
        print("Press R to reset first")
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
        print("Win animation completed. Press R to reset.")

    scene_view.show_win(on_done=finished)


def _fragile_cell_for_move(before, action):
    """Get the landing cell from the Engine transition table for demo display."""
    if before.pose is None:
        raise ValueError("Fragile break requires the intact block")

    new_pose, dr, dc = ROLL[(before.pose, action.direction)]
    if new_pose is not Pose.STANDING:
        raise ValueError("Engine reported fragile break for a non-standing move")

    cell = (before.pos[0] + dr, before.pos[1] + dc)
    if stage.cell(cell) != "F":
        raise ValueError(f"Engine reported fragile break outside F: {cell}")
    return cell


def _show_engine_fall(before, action, result, on_done):
    """Show an Engine-rejected fall, collapsing F first when reported."""
    if result.reason == "fragile_broke":
        cell = _fragile_cell_for_move(before, action)
        scene_view.board.break_fragile(
            cell,
            on_done=lambda: scene_view.show_fall(
                before,
                action,
                on_done=on_done,
            ),
        )
        return

    scene_view.show_fall(before, action, on_done=on_done)


def test_fragile_break():
    """Use an Engine-validated move that stands upright on an F tile."""
    global current_state, has_fallen

    if scene_view.is_busy() or auto_running:
        print("Cannot test fragile break during animation")
        return
    if has_fallen or has_won:
        print("Press R to reset first")
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
        print("No Engine-valid fragile-break position on this stage")
        return

    before, result = candidate
    current_state = before
    scene_view.show_state(before)

    def fall_finished():
        global has_fallen
        has_fallen = True
        print("Fragile tile broke and the block fell. Press R to reset.")

    _show_engine_fall(before, action, result, fall_finished)


def input(key):
    global current_state, has_fallen

    # R: reset the demo after a fall.
    if key == "r":
        reset_demo()
        return

    if key == "f":
        if stage.id != "basic_01":
            print("F test is configured for basic_01.json")
            return

        if auto_running or scene_view.is_busy():
            print("Cannot test fall during animation")
            return

        reset_demo()
        key = "up arrow"

    if key == "w":
        test_win()
        return

    if has_won:
        print("Win animation completed. Press R to reset.")
        return

    # Block further movement after the fall.
    if has_fallen:
        print("Block has fallen. Press R to reset.")
        return

    if key == "b":
        test_fragile_break()
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

    if key in directions:
        if scene_view.is_busy():
            print("Animation is still running")
            return

        before = current_state
        action = Action(directions[key])
        result = step(stage, before, action)

        # Engine decides why the move fell; Scene only presents that result.
        if result.outcome is Outcome.ILLEGAL and result.reason in {
            "fell",
            "fragile_broke",
        }:
            print("Fall detected:", action.direction, result.reason)

            def fall_finished():
                global has_fallen

                has_fallen = True
                print("Fall animation completed. Press R to reset.")

            _show_engine_fall(before, action, result, fall_finished)
            return

        if result.outcome != Outcome.MOVED or result.state is None:
            print("Move rejected:", result.reason)
            return

        def finished():
            global current_state, has_won

            # Update State only after the roll animation finishes.
            current_state = result.state

            print(
                "Roll finished:",
                current_state.pos,
                current_state.pose.name,
            )

            # The Engine provides a separate goal check.
            if is_goal(stage, current_state):
                print("GOAL reached! Starting win animation.")

                def win_finished():
                    global has_won

                    has_won = True
                    print("REAL WIN COMPLETED. Press R to reset.")

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
        print("Displaying:", poses[key].name)


def main():
    global stage, scene_view, current_state

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

    scene_view.load_stage(stage, initial_state)
    # Camera chỉ dùng cho demo Task 3.2.
    # Không thay đổi góc camera chính thức trong SceneView.
    center_x = (stage.cols - 1) / 2
    center_z = -(stage.rows - 1) / 2
    size = max(stage.rows, stage.cols, 4)

    camera.position = (
        center_x,
        size * 2.8,
        center_z - size * 2.2,
    )

    camera.look_at((center_x, 0, center_z))

    Text(
        text=(
            "Arrows: Move | T: 10 rolls | G: 10 + Goal\n"
            "F: Fall | B: Fragile break | W: Preview Win | "
            "R: Reset | 1/2/3: Pose"
        ),
        position=(-0.85, 0.45),
        scale=0.75,
    )

    print("Loaded stage:", stage.id)
    print("Press 1, 2 or 3 to change block pose.")
    app.run()


if __name__ == "__main__":
    main()
