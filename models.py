DESTINATION_ORDER = {
    "anchorage": "A",
    "brisbane": "B",
    "copenhagen": "C",
    "dunkirk": "D",
    "edinburgh": "E",
}

LIGHT, MEDIUM, HEAVY = 1, 2, 3
NUM_STACKS, MAX_HEIGHT  = 10,10

def split_text(text):
    parts = text.split("-")
    parts[0] = DESTINATION_ORDER[parts[0].strip().lower()]
    parts[1] = int(parts[1]) 
    return parts[0] , parts[1]

def empty_dock():
    dock = {}
    for n in range(1,NUM_STACKS+1):
        dock[n] = []

    return dock

def move (dock, source, destination):
    if len(dock[source]) == 0:
        raise ValueError(f"Column {source} is empty")
    if len(dock[destination]) >= MAX_HEIGHT:
        raise ValueError(f"Column {destination} is full")
    if source == destination:
        raise ValueError("Can't move a container to the same column")

    c = dock[source].pop()
    dock[destination].append(c)

def get_weights(dock):
    weights = []
    for column in range(1,NUM_STACKS+1):
        for row in range(len(dock[column])):
            weights.append(dock[column][row][1])

    return weights

def compute_cutoffs(weights):
    s = sorted(weights)
    n = len(s)

    light_max = s[n // 3 - 1] 
    heavy_min = s[2 * n // 3] 
    
    return light_max, heavy_min
    
def classify(weight, cutoffs):
    light_max, heavy_min = cutoffs
    if weight <= light_max:
        return LIGHT
    elif weight >= heavy_min:
        return HEAVY
    else: 
        return MEDIUM

