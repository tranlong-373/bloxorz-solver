
from ursina import *

# Task 3.0 - VT3: Thu Ursina trong sandbox
#
# Quy uoc: x = cot, z = -hang, mat san y = 0
# RIGHT: +90 do quanh truc Z
# LEFT:  -90 do quanh truc Z
# UP:    +90 do quanh truc X
# DOWN:  -90 do quanh truc X

app = Ursina()

SIZE = 6
DURATION = 0.25

# Tao ban choi 6x6
for row in range(SIZE):
    for col in range(SIZE):
        Entity(
            model="cube",
            position=(col, -0.1, -row),
            scale=(0.95, 0.2, 0.95),
            color=color.gray
        )

# Trang thai ban dau
r = 2
c = 2
pose = "standing"
busy = False

block = Entity(
    model="cube",
    position=(2, 1, -2),
    scale=(1, 2, 1),
    color=color.azure
)

# Camera
camera.position = (2.5, 9, -11)
camera.look_at((2.5, 0, -2.5))


def place_block():
    """Dat khoi vao toa do chinh xac theo tu the."""
    block.rotation = (0, 0, 0)

    if pose == "standing":
        block.position = (c, 1, -r)
        block.scale = (1, 2, 1)

    elif pose == "horizontal":
        block.position = (c + 0.5, 0.5, -r)
        block.scale = (2, 1, 1)

    elif pose == "vertical":
        block.position = (c, 0.5, -(r + 0.5))
        block.scale = (1, 1, 2)


def next_state(direction):
    """Bang 12 chuyen tu the theo quy uoc nhom."""
    if pose == "standing":
        if direction == "right":
            return r, c + 1, "horizontal"
        if direction == "left":
            return r, c - 2, "horizontal"
        if direction == "up":
            return r - 2, c, "vertical"
        if direction == "down":
            return r + 1, c, "vertical"

    elif pose == "horizontal":
        if direction == "right":
            return r, c + 2, "standing"
        if direction == "left":
            return r, c - 1, "standing"
        if direction == "up":
            return r - 1, c, "horizontal"
        if direction == "down":
            return r + 1, c, "horizontal"

    elif pose == "vertical":
        if direction == "right":
            return r, c + 1, "vertical"
        if direction == "left":
            return r, c - 1, "vertical"
        if direction == "up":
            return r - 1, c, "standing"
        if direction == "down":
            return r + 2, c, "standing"


def inside_board(new_r, new_c, new_pose):
    """Kiem tra khoi co nam tron trong ban 6x6."""
    width = 2 if new_pose == "horizontal" else 1
    height = 2 if new_pose == "vertical" else 1

    return (
        new_r >= 0
        and new_c >= 0
        and new_r + height <= SIZE
        and new_c + width <= SIZE
    )


def roll(direction):
    global r, c, pose, busy

    if busy:
        return

    target = next_state(direction)

    if target is None:
        return

    new_r, new_c, new_pose = target

    if not inside_board(new_r, new_c, new_pose):
        print("Khong the lan ra ngoai ban")
        return

    busy = True

    # Tim canh day lam diem tua
    
    # Xac dinh canh day lam pivot
    px = block.x
    pz = block.z

    if direction == "right":
        px += block.scale_x / 2
        axis = "rotation_z"
        angle = 90

    elif direction == "left":
        px -= block.scale_x / 2
        axis = "rotation_z"
        angle = -90

    elif direction == "up":
        pz += block.scale_z / 2
        axis = "rotation_x"
        angle = 90

    elif direction == "down":
        pz -= block.scale_z / 2
        axis = "rotation_x"
        angle = -90


    # Tao pivot tai canh day
    pivot = Entity(
        position=(px, 0, pz)
    )

    # Gan block vao pivot
    block.world_parent = pivot

    # Quay quanh canh day
    pivot.animate(
        axis,
        angle,
        duration=DURATION,
        curve=curve.linear
    )

    def finish():
        global r, c, pose, busy

        block.world_parent = scene
        destroy(pivot)

        # Cap nhat trang thai
        r = new_r
        c = new_c
        pose = new_pose

        # Dat lai vi tri chinh xac
        place_block()

        busy = False

        print(f"State: ({r}, {c}), {pose}")

    invoke(finish, delay=DURATION + 0.01)


def input(key):
    if busy:
        return

    directions = {
        "right arrow": "right",
        "left arrow": "left",
        "up arrow": "up",
        "down arrow": "down"
    }

    if key in directions:
        roll(directions[key])


app.run()
