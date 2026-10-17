import csv
import io
import os
import sys


# Closest port first. A is Anchorage, E is Edinburgh.
DESTINATION_ORDER = {
    "anchorage": "A",
    "brisbane": "B",
    "copenhagen": "C",
    "dunkirk": "D",
    "edinburgh": "E",
}

NUM_STACKS, MAX_HEIGHT = 10, 10
YARD_STACKS = NUM_STACKS
YARD_HEIGHT = MAX_HEIGHT
BOAT_LENGTH = 8  # bays, bow at x = 0 (left)
BOAT_WIDTH = 5
BOAT_HEIGHT = 3

DEST_INDEX = {}
PORT_NAME = {}
for _index, (_city, _letter) in enumerate(DESTINATION_ORDER.items()):
    DEST_INDEX[_letter] = _index
    PORT_NAME[_letter] = _city.capitalize()


def split_text(text):
    parts = text.split("-")
    parts[0] = DESTINATION_ORDER[parts[0].strip().lower()]
    parts[1] = int(parts[1])
    return parts[0], parts[1]


def empty_dock():
    dock = {}
    for n in range(1, NUM_STACKS + 1):
        dock[n] = []
    return dock


def move(dock, source, destination):
    if len(dock[source]) == 0:
        raise ValueError(f"Column {source} is empty")
    if len(dock[destination]) >= MAX_HEIGHT:
        raise ValueError(f"Column {destination} is full")
    if source == destination:
        raise ValueError("Can't move a container to the same column")

    c = dock[source].pop()
    dock[destination].append(c)


def make_container(dest, weight, counts, wclass=None):
    counts[dest] = counts.get(dest, 0) + 1
    cont_id = dest + str(counts[dest])
    made = {"id": cont_id, "destination": dest, "weight": weight}
    if wclass is not None:
        made["weight_class"] = wclass
    return made


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
        self.columns = {}
        if len(self.containers) == 0:
            return []

        dock = Dock(self.containers)
        stacks = dock.copy_stacks()
        columns = plan_columns(self.containers)
        ship_level = _ship_levels(columns)
        if not _yard_ready(stacks, ship_level):
            # Same-port boxes are interchangeable for the port rule. If letting
            # the higher yard box board first makes the yard ready as it sits,
            # take that plan and skip the rebuild entirely.
            by_yard = plan_columns(self.containers, yard_first=True)
            by_yard_level = _ship_levels(by_yard)
            if _yard_ready(stacks, by_yard_level):
                columns, ship_level = by_yard, by_yard_level

        self.columns = columns
        moves = sort_yard(stacks, ship_level)
        moves.extend(load_boat(stacks, columns))
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
                src, (x, y, _level) = data
                result.append(f"{src + 1}>S({y + 1}|{x + 1})")
        return result


def parse_csv(text):
    if text.strip() == "":
        return []
    rows = list(csv.reader(io.StringIO(text)))
    while len(rows) > 0 and _row_empty(rows[-1]):
        rows.pop()
    dock = empty_dock()
    for index, row in enumerate(rows, 1):
        for cell in row:
            if not cell.strip():
                continue
            dock[index].append(split_text(cell))
    counts = {}
    containers = []
    for column in range(1, NUM_STACKS + 1):
        for height, item in enumerate(dock[column]):
            dest = item[0]
            weight = item[1]
            made = make_container(dest, weight, counts)
            containers.append(
                Container(made["id"], made["weight"], made["destination"], column - 1, height)
            )
    return containers


def _row_empty(row):
    for cell in row:
        if cell.strip() != "":
            return False
    return True


def _deck_cells():
    cells = []
    for y in range(BOAT_WIDTH):
        for x in range(BOAT_LENGTH):
            cells.append((x, y))
    # Checkerboard first, so the second layer lands all over the deck
    # instead of piling up on the left and stopping.
    cells.sort(key=lambda pos: ((pos[0] + pos[1]) % 2, pos[1], pos[0]))
    return cells


def _ship_levels(columns):
    ship_level = {}
    for pos, column in columns.items():
        for level, container in enumerate(column):
            ship_level[container.id] = level
    return ship_level


def plan_columns(containers, yard_first=False):
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

    if yard_first:
        # Within a port, the box sitting higher in the yard boards first (lower level).
        def order(container):
            return (-DEST_INDEX[container.dest], -container.height, -container.weight, container.id)
    else:
        def order(container):
            return (-DEST_INDEX[container.dest], -container.weight, container.id)
    ordered = sorted(containers, key=order)
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
    dock = empty_dock()
    for index, stack in enumerate(stacks):
        dock[index + 1] = stack

    def relocate(src, dst):
        move(dock, src + 1, dst + 1)
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
            pile.append({"dest": PORT_NAME[container.dest], "weight": container.weight})
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
                pile.append({"dest": PORT_NAME[container.dest], "weight": container.weight})
            across.append(pile)
        ship.append(across)
    return yard, ship


def write_moves_csv(path, lines):
    # One instruction per row, no header. The last row is how many moves that was.
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        for line in lines:
            writer.writerow([line])
        writer.writerow(["Moves: " + str(len(lines))])


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8-sig", newline="") as source:
        plan = Planner(parse_csv(source.read())).solve()
    lines = Planner.format_moves(plan)
    out_path = os.path.splitext(sys.argv[1])[0] + "-moves.csv"
    write_moves_csv(out_path, lines)
    print("\n".join(lines))
    print("Moves: " + str(len(lines)))
