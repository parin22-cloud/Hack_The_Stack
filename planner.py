import csv
import io
import math
import os
import sys


# Closest port first. Edinburgh is the farthest.
DESTINATIONS = [
    "Anchorage",
    "Brisbane",
    "Copenhagen",
    "Dunkirk",
    "Edinburgh",
]

DEST_INDEX = {}
for _i, _name in enumerate(DESTINATIONS):
    DEST_INDEX[_name] = _i

YARD_STACKS = 10
YARD_HEIGHT = 10
MAX_CONTAINERS = 80
BOAT_LENGTH = 8  # bays, bow at x = 0 (left)
BOAT_WIDTH = 5
BOAT_HEIGHT = 3


class Container:
    def __init__(self, id, weight, dest, stack, height):
        self.id = id
        self.weight = weight
        self.dest = dest
        self.stack = stack
        self.height = height  # 0 is the bottom of the stack


class Dock:
    def __init__(self, containers):
        self.stacks = [[] for _ in range(YARD_STACKS)]
        grouped = [[] for _ in range(YARD_STACKS)]
        for container in containers:
            grouped[container.stack].append(container)
        for stack_index, group in enumerate(grouped):
            group.sort(key=lambda container: container.height)
            self.stacks[stack_index] = group

    def copy_stacks(self):
        copied = []
        for stack in self.stacks:
            copied.append(list(stack))
        return copied


class Boat:
    def __init__(self):
        self.columns = {}
        for x in range(BOAT_LENGTH):
            for y in range(BOAT_WIDTH):
                self.columns[(x, y)] = []

    @staticmethod
    def center_distance(x, y):
        # How far this column is from the middle of the ship, with no floats.
        # 8 bays, so the middle sits between bay 3 and bay 4. 5 rows, middle is row 2.
        return (2 * x - 7) ** 2 + (2 * y - 4) ** 2


class Planner:
    def __init__(self, containers):
        self.containers = containers

    def solve(self):
        validate(self.containers)
        self.columns = {}
        if len(self.containers) == 0:
            moves = []
            Simulator(self.containers).check(moves)
            return moves

        columns = plan_columns(self.containers)
        ship_level = {}
        for pos, column in columns.items():
            for level, container in enumerate(column):
                ship_level[container.id] = level

        self.columns = columns
        dock = Dock(self.containers)
        stacks = dock.copy_stacks()
        moves = sort_yard(stacks, ship_level)
        moves.extend(load_boat(stacks, columns))
        Simulator(self.containers).check(moves)
        return moves

    @staticmethod
    def format_moves(moves):
        """Yard moves are 3>1. Loads are 3>s(4|2): stack 3 onto bay 4, row 2."""
        result = []
        for kind, *data in moves:
            if kind == "D":
                src, dst = data
                result.append(f"{src + 1}>{dst + 1}")
            elif kind == "L":
                # Height is whatever is already in that column. The file only names bay and row.
                src, (x, y, _level) = data
                result.append(f"{src + 1}>S({x + 1}|{y + 1})")
            else:
                raise ValueError(f"Unknown move {kind!r}")
        return result


class Simulator:
    # Replays the move list on a fresh yard and boat.
    # It does not read the planner's private column choices except
    # what the moves themselves say.
    def __init__(self, containers):
        self.containers = containers

    def check(self, moves):
        validate(self.containers)
        dock = Dock(self.containers)
        stacks = dock.copy_stacks()
        boat = Boat()
        phase = "D"
        seen_load = False

        for move in moves:
            kind = move[0]
            if kind == "D":
                if phase != "D":
                    raise RuntimeError("Dock move after loading has started.")
                src = move[1]
                dst = move[2]
                self._move_top(stacks, src, dst)
            elif kind == "L":
                if not seen_load:
                    self._check_yard(stacks, moves)
                    seen_load = True
                    phase = "L"
                src = move[1]
                x, y, level = move[2]
                container = self._take_top(stacks, src)
                self._put_on_boat(boat, container, x, y, level)
            else:
                raise RuntimeError("Unknown move " + str(move))

        for stack in stacks:
            if len(stack) != 0:
                raise RuntimeError("Yard is not empty at the end.")
        aboard = 0
        for column in boat.columns.values():
            aboard += len(column)
        if aboard != len(self.containers):
            raise RuntimeError("Not every container made it onto the ship.")

    def _check_yard(self, stacks, moves):
        # Ship level of each container, discovered by replaying loads on a copy.
        # Bottoms of the ship (level 0) have to sit on top of the yard stacks,
        # because the crane takes the top first.
        trial = []
        for stack in stacks:
            trial.append(list(stack))
        level_of = {}
        for move in moves:
            if move[0] != "L":
                continue
            src = move[1]
            level = move[2][2]
            if len(trial[src]) == 0:
                raise RuntimeError("Load from an empty stack.")
            container = trial[src].pop()
            level_of[container.id] = level
        for stack in stacks:
            for height in range(1, len(stack)):
                upper = level_of[stack[height].id]
                lower = level_of[stack[height - 1].id]
                if upper > lower:
                    raise RuntimeError("Yard is not in load order before loading.")

    def _move_top(self, stacks, src, dst):
        if src < 0 or src >= YARD_STACKS or dst < 0 or dst >= YARD_STACKS:
            raise RuntimeError("Dock move leaves the yard.")
        if src == dst:
            raise RuntimeError("Dock move stays on the same stack.")
        if len(stacks[src]) == 0:
            raise RuntimeError("Dock move from an empty stack.")
        if len(stacks[dst]) >= YARD_HEIGHT:
            raise RuntimeError("Dock move onto a full stack.")
        stacks[dst].append(stacks[src].pop())

    def _take_top(self, stacks, src):
        if src < 0 or src >= YARD_STACKS:
            raise RuntimeError("Load from outside the yard.")
        if len(stacks[src]) == 0:
            raise RuntimeError("Load from an empty stack.")
        return stacks[src].pop()

    def _put_on_boat(self, boat, container, x, y, level):
        if x < 0 or x >= BOAT_LENGTH or y < 0 or y >= BOAT_WIDTH:
            raise RuntimeError("Load is outside the boat.")
        if level < 0 or level >= BOAT_HEIGHT:
            raise RuntimeError("Load level is outside the boat.")
        column = boat.columns[(x, y)]
        if len(column) != level:
            raise RuntimeError("Load does not land on the current top of the column.")
        if level > 0:
            below = column[level - 1]
            if DEST_INDEX[below.dest] < DEST_INDEX[container.dest]:
                raise RuntimeError("A nearer container is underneath a farther one.")
        column.append(container)


def validate(containers):
    if len(containers) > MAX_CONTAINERS:
        raise ValueError(
            "Too many containers (" + str(len(containers)) + "). The limit is 80."
        )
    seen_ids = set()
    seen_cells = set()
    for container in containers:
        if container.id in seen_ids:
            raise ValueError("Duplicate container id " + str(container.id) + ".")
        seen_ids.add(container.id)
        if container.dest not in DEST_INDEX:
            raise ValueError(
                "Destination '" + str(container.dest) + "' is not a known port."
            )
        if isinstance(container.weight, bool) or not isinstance(container.weight, (int, float)):
            raise ValueError("Weight must be a number.")
        if math.isnan(container.weight) or container.weight < 0:
            raise ValueError("Weight must be zero or positive, not " + str(container.weight) + ".")
        if container.stack < 0 or container.stack >= YARD_STACKS:
            raise ValueError(
                "Stack " + str(container.stack) + " is outside the yard of 10 stacks."
            )
        if container.height < 0 or container.height >= YARD_HEIGHT:
            raise ValueError(
                "Height " + str(container.height) + " is outside a stack of height 10."
            )
        cell = (container.stack, container.height)
        if cell in seen_cells:
            raise ValueError(
                "Two containers share stack "
                + str(container.stack + 1)
                + ", height "
                + str(container.height + 1)
                + "."
            )
        seen_cells.add(cell)
    for stack_index in range(YARD_STACKS):
        heights = []
        for container in containers:
            if container.stack == stack_index:
                heights.append(container.height)
        heights.sort()
        for expected, height in enumerate(heights):
            if height != expected:
                raise ValueError(
                    "Stack " + str(stack_index + 1) + " has a gap. Pack from the bottom."
                )


def parse_csv(text):
    if text.strip() == "":
        return []
    rows = list(csv.reader(io.StringIO(text)))
    while len(rows) > 0 and _row_empty(rows[-1]):
        rows.pop()
    if len(rows) > YARD_STACKS:
        raise ValueError("The yard only has 10 stacks.")
    containers = []
    next_id = 0
    for stack_index, row in enumerate(rows):
        seen_empty = False
        height = 0
        for cell in row:
            token = cell.strip()
            if token == "":
                seen_empty = True
                continue
            if seen_empty:
                raise ValueError(
                    "Row " + str(stack_index + 1) + " has a gap. Pack each stack from the left."
                )
            if height >= YARD_HEIGHT:
                raise ValueError(
                    "Stack " + str(stack_index + 1) + " is taller than 10."
                )
            dest, weight = _split_cell(token, stack_index + 1)
            containers.append(Container(next_id, weight, dest, stack_index, height))
            next_id += 1
            height += 1
    validate(containers)
    return containers


def _row_empty(row):
    for cell in row:
        if cell.strip() != "":
            return False
    return True


def _split_cell(text, row_number):
    if "-" not in text:
        raise ValueError(
            "Row " + str(row_number) + ": could not read '" + text
            + "'. Expected Destination-Weight."
        )
    dest, weight_text = text.rsplit("-", 1)
    dest = dest.strip()
    if dest not in DEST_INDEX:
        raise ValueError(
            "Row " + str(row_number) + ": destination '" + dest + "' is not a known port."
        )
    try:
        weight = float(weight_text.strip())
    except ValueError:
        raise ValueError(
            "Row " + str(row_number) + ": weight must be a number, got '"
            + weight_text.strip() + "'."
        )
    if math.isnan(weight) or weight < 0:
        raise ValueError(
            "Row " + str(row_number) + ": weight must be zero or positive, got '"
            + weight_text.strip() + "'."
        )
    return dest, weight


def _deck_cells():
    cells = []
    for y in range(BOAT_WIDTH):
        for x in range(BOAT_LENGTH):
            cells.append((x, y))
    # Checkerboard first, so the second layer lands all over the deck
    # instead of piling up on the left and stopping.
    cells.sort(key=lambda pos: ((pos[0] + pos[1]) % 2, pos[1], pos[0]))
    return cells


def plan_columns(containers):
    # Fill the floor of the whole ship before anyone gets a second box,
    # then the second level, then the third. Farther ports stay underneath.
    spots = BOAT_LENGTH * BOAT_WIDTH
    cells = _deck_cells()
    count = len(containers)
    layers = count // spots
    extra = count % spots
    heights = {}
    if layers == 0:
        for pos in cells[:count]:
            heights[pos] = 1
    else:
        for pos in cells:
            heights[pos] = layers
        for pos in cells[:extra]:
            heights[pos] += 1

    ordered = sorted(
        containers,
        key=lambda container: (-DEST_INDEX[container.dest], -container.weight, container.id),
    )
    columns = {}
    index = 0
    for level in range(BOAT_HEIGHT):
        slots = []
        for pos, height in heights.items():
            if height > level:
                slots.append(pos)
        # Heavier boxes on this level sit closer to the middle. The level is still full.
        slots.sort(key=lambda pos: (Boat.center_distance(pos[0], pos[1]), pos[0], pos[1]))
        batch = ordered[index:index + len(slots)]
        index += len(slots)
        batch.sort(key=lambda container: (-container.weight, container.id))
        for container, pos in zip(batch, slots):
            columns.setdefault(pos, []).append(container)
    return columns


def _yard_ready(stacks, ship_level):
    for stack in stacks:
        for height in range(1, len(stack)):
            if ship_level[stack[height].id] > ship_level[stack[height - 1].id]:
                return False
    return True


def sort_yard(stacks, ship_level):
    # The crane only grabs the top box. Stuff that boards first (the floor of
    # each ship column) has to be sitting on top in the yard. If it already is,
    # leave the stacks alone.
    if _yard_ready(stacks, ship_level):
        return []

    moves = []

    def relocate(src, dst):
        if len(stacks[src]) == 0:
            raise RuntimeError("Sort moved an empty stack.")
        if len(stacks[dst]) >= YARD_HEIGHT:
            raise RuntimeError("Sort ran out of room.")
        stacks[dst].append(stacks[src].pop())
        moves.append(("D", src, dst))

    def locate(container):
        for stack_index, stack in enumerate(stacks):
            for height, item in enumerate(stack):
                if item is container:
                    return stack_index, height
        raise RuntimeError("Lost a container during the yard sort.")

    containers = []
    for stack in stacks:
        containers.extend(stack)
    # Place ship-top tiers first so they become the bottom of a yard stack.
    containers.sort(key=lambda container: (-ship_level[container.id], container.id))

    # Keep the last stacks as parking. Everything else gets rebuilt, floor first.
    home_count = (len(containers) + YARD_HEIGHT - 1) // YARD_HEIGHT
    if home_count > YARD_STACKS - 1:
        home_count = YARD_STACKS - 1

    def park(src, banned):
        choices = []
        for stack_index in range(YARD_STACKS):
            if stack_index == src or stack_index in banned:
                continue
            if len(stacks[stack_index]) < YARD_HEIGHT:
                choices.append(stack_index)
        if len(choices) == 0:
            raise RuntimeError("No open cell while sorting the yard.")
        # Park on the high stacks so the low ones stay free to rebuild.
        choices.sort(key=lambda stack_index: (len(stacks[stack_index]), -stack_index))
        relocate(src, choices[0])

    cursor = 0
    for home in range(home_count):
        finished = set(range(home))
        while len(stacks[home]) > 0:
            park(home, finished)
        chunk_end = cursor + YARD_HEIGHT
        if chunk_end > len(containers):
            chunk_end = len(containers)
        while cursor < chunk_end:
            container = containers[cursor]
            src, height = locate(container)
            while height < len(stacks[src]) - 1:
                park(src, finished | set([home]))
                src, height = locate(container)
            if src != home:
                relocate(src, home)
            cursor += 1
    return moves


def load_boat(stacks, columns):
    # Fill every column's floor before anyone's second box, or that box is floating.
    # We can only take whatever is currently on top. Among those, the middle
    # of the ship goes first.
    by_level = {0: [], 1: [], 2: []}
    slot_of = {}
    for pos, column in columns.items():
        for level, container in enumerate(column):
            by_level[level].append(container)
            slot_of[container.id] = (pos[0], pos[1], level)

    def prefer(container):
        x, y, level = slot_of[container.id]
        return (Boat.center_distance(x, y), x, y, container.id)

    moves = []
    for level in (0, 1, 2):
        pending = {}
        for container in by_level[level]:
            pending[container.id] = container
        while len(pending) > 0:
            tops = []
            for stack_index, stack in enumerate(stacks):
                if len(stack) > 0 and stack[-1].id in pending:
                    tops.append((stack_index, stack[-1]))
            if len(tops) == 0:
                raise RuntimeError("A container due to load is buried in the yard.")
            tops.sort(key=lambda item: prefer(item[1]))
            stack_index, container = tops[0]
            stacks[stack_index].pop()
            moves.append(("L", stack_index, slot_of[container.id]))
            del pending[container.id]
    return moves


def view_data(containers, columns):
    # One picture of the yard and one of the ship, both built from the plan
    # the page is about to draw. Bottom box first in every pile.
    dock = Dock(containers)
    yard = []
    for stack in dock.stacks:
        pile = []
        for container in stack:
            pile.append({"dest": container.dest, "weight": container.weight})
        yard.append(pile)
    while len(yard) > 0 and len(yard[-1]) == 0:
        yard.pop()

    ship = []
    for bay in range(BOAT_LENGTH):
        across = []
        for row in range(BOAT_WIDTH):
            column = columns.get((bay, row), [])
            pile = []
            for container in column:
                pile.append({"dest": container.dest, "weight": container.weight})
            across.append(pile)
        ship.append(across)
    return yard, ship


def write_moves_csv(path, lines):
    # One instruction per row, no header. Same text the page shows.
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        for line in lines:
            writer.writerow([line])


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8-sig", newline="") as source:
        plan = Planner(parse_csv(source.read())).solve()
    lines = Planner.format_moves(plan)
    out_path = os.path.splitext(sys.argv[1])[0] + "-moves.csv"
    write_moves_csv(out_path, lines)
    print("\n".join(lines))
