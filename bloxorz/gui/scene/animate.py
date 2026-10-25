"""Animation helpers for rolling, falling, and winning.

Owner: VT3 | Tasks: 3.2, 3.3a, 3.3b, 3.3c.
"""

from ursina import Entity, curve, destroy, scene

from bloxorz.model import Direction


ROLL_DURATION = 0.25
BRIDGE_DURATION = 0.3
FRAGILE_BREAK_DURATION = 0.3
SPLIT_DURATION = 0.25


def play_fragile_break(tile, on_finished):
    """Collapse a fragile floor tile after Engine reports it broken."""
    animation = tile.animate_scale(
        (tile.scale_x, 0.01, tile.scale_z),
        duration=FRAGILE_BREAK_DURATION,
        curve=curve.in_quad,
    )
    animation.append(on_finished)


def play_roll(block, direction: Direction, on_finished):
    """Roll the block 90 degrees around the ground edge."""

    x, z = block.world_x, block.world_z
    half_x = block.world_scale_x / 2
    half_z = block.world_scale_z / 2

    if direction == Direction.RIGHT:
        pivot_position = (x + half_x, 0, z)
        rotation_axis = "rotation_z"
        angle = 90

    elif direction == Direction.LEFT:
        pivot_position = (x - half_x, 0, z)
        rotation_axis = "rotation_z"
        angle = -90

    elif direction == Direction.UP:
        pivot_position = (x, 0, z + half_z)
        rotation_axis = "rotation_x"
        angle = 90

    elif direction == Direction.DOWN:
        pivot_position = (x, 0, z - half_z)
        rotation_axis = "rotation_x"
        angle = -90

    else:
        raise ValueError(f"Unsupported direction: {direction}")

    pivot = Entity(position=pivot_position)
    block.world_parent = pivot

    def finish():
        block.world_parent = scene
        destroy(pivot)

        on_finished()

    # Use the animation's own sequence for completion.
    roll_animation = pivot.animate(
        rotation_axis,
        angle,
        duration=ROLL_DURATION,
        curve=curve.linear,
    )

    roll_animation.append(finish)


# Fall animation: roll over the edge, then drop.
FALL_DURATION = 0.8
FALL_ROLL_DURATION = 0.30
FALL_DROP_DURATION = FALL_DURATION - FALL_ROLL_DURATION
FALL_TARGET_Y = -10.0


def play_fall(block, direction: Direction, on_finished):
    """Roll toward an unsupported area, then fall."""

    x, z = block.world_x, block.world_z
    half_x = block.world_scale_x / 2
    half_z = block.world_scale_z / 2

    if direction == Direction.RIGHT:
        pivot_position = (x + half_x, 0, z)
        rotation_axis = "rotation_z"
        angle = 90

    elif direction == Direction.LEFT:
        pivot_position = (x - half_x, 0, z)
        rotation_axis = "rotation_z"
        angle = -90

    elif direction == Direction.UP:
        pivot_position = (x, 0, z + half_z)
        rotation_axis = "rotation_x"
        angle = 90

    elif direction == Direction.DOWN:
        pivot_position = (x, 0, z - half_z)
        rotation_axis = "rotation_x"
        angle = -90

    else:
        raise ValueError(f"Unsupported direction: {direction}")

    pivot = Entity(position=pivot_position)
    block.world_parent = pivot

    def finish():
        block.y = FALL_TARGET_Y
        print("FALL: drop completed at", block.world_position)
        on_finished()

    def start_drop():
        # Ensure the roll ends at precisely 90 degrees.
        setattr(pivot, rotation_axis, angle)

        # Preserve the rolled position before dropping.
        block.world_parent = scene
        destroy(pivot)

        print("FALL: roll completed at", block.world_position)

        drop_animation = block.animate_y(
            FALL_TARGET_Y,
            duration=FALL_DROP_DURATION,
            curve=curve.in_expo,
        )
        drop_animation.append(finish)

    roll_animation = pivot.animate(
        rotation_axis,
        angle,
        duration=FALL_ROLL_DURATION,
        curve=curve.linear,
    )
    roll_animation.append(start_drop)


def play_drop(block, on_finished):
    """Drop vertically after the block has landed on a broken fragile tile."""
    drop_animation = block.animate_y(
        FALL_TARGET_Y,
        duration=FALL_DROP_DURATION,
        curve=curve.in_expo,
    )

    def finish():
        block.y = FALL_TARGET_Y
        on_finished()

    drop_animation.append(finish)


def play_split(cubes, on_finished):
    """Grow the two cubes at the Engine's split targets, then finish once."""
    remaining = len(cubes)

    def callback_for_one_cube():
        finished = False

        def one_done():
            nonlocal remaining, finished
            # A repeated callback from the same cube must not count twice.
            if finished:
                return
            finished = True
            remaining -= 1
            if remaining == 0:
                on_finished()

        return one_done

    for cube in cubes:
        target = tuple(cube.scale)
        cube.scale = (0, 0, 0)
        animation = cube.animate_scale(
            target,
            duration=SPLIT_DURATION,
            curve=curve.linear,
        )
        animation.append(callback_for_one_cube())


WIN_DURATION = 0.6
WIN_DROP_DISTANCE = 2.0


def play_win(block, on_finished):
    """Sink the block into the goal hole."""

    start_y = block.y
    target_y = start_y - WIN_DROP_DISTANCE

    def finish():
        block.y = target_y
        on_finished()

    win_animation = block.animate_y(
        target_y,
        duration=WIN_DURATION,
        curve=curve.linear,
    )
    win_animation.append(finish)
