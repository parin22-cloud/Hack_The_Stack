import csv
from models import NUM_STACKS, DESTINATION_ORDER, empty_dock, split_text, get_weights, compute_cutoffs

def read_rows(path):
    with open(path , newline = "") as f:
        rows = list(csv.reader(f)) 

    while len(rows) < NUM_STACKS:
        rows.append([])

    return rows

def build_dock(rows):
    dock = empty_dock()
    for index, row in enumerate(rows,1):
        for cell in row:
            if not cell.strip():
                continue

            item = split_text(cell)

            dock[index].append(item)

    return dock

def load_dock(path):
    rows = read_rows(path)
    dock = build_dock(rows)
    weights = get_weights(dock)
    cutoffs = compute_cutoffs(weights)

    return dock , cutoffs