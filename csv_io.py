import csv
from models import NUM_STACKS, DESTINATION_ORDER, empty_dock, split_text, get_weights, compute_cutoffs, classify, make_container

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

    counts = {}                                  

    for column in range(1, NUM_STACKS+1):
        for row in range(len(dock[column])):
            dest = dock[column][row][0]                          
            weight = dock[column][row][1]                         
            wclass = classify(weight, cutoffs)  
            dock[column][row] = make_container(dest, weight, counts, wclass)  
    return dock, cutoffs


if __name__ == "__main__":
    dock, cutoffs = load_dock("Test Cases/random1.csv")
    print(cutoffs)
    for stack_num in dock:
        print(stack_num, dock[stack_num])