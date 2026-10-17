#Inputs, the dock dictionary, and column number
#Manipulates the dock dictionary to rearrange the containers in each column (change the indexes), outputs the commands as a comma-seperated string

def column_sorting(dock, column_number):
  if column_number not in dock or not dock[column_number]:
    return ""

  commands = []
  other_columns = [col for col in range(10) if col != column_number]
  dispersed_cols = []

  # Phase 1: Disperse containers from the source to the other columns
  for target_col in other_columns:
    if dock[column_number]:
      container = dock[column_number].pop()
      dock[target_col].append(container)
      # Format as source>destination
      commands.append(f"{column_number}>{target_col}")
      dispersed_cols.append(target_col)

  # Phase 2: Bring them back one by one in sorted order
  while dispersed_cols:
    best_col = min(dispersed_cols, key=lambda col: dock[col][-1])
    container = dock[best_col].pop()
    dock[column_number].append(container)
    # Format as source>destination
    commands.append(f"{best_col}>{column_number}")
    dispersed_cols.remove(best_col)

  # Join all commands into a single string separated by commas
  return ", ".join(commands)