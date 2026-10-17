var COLORS = {
  Anchorage: "#2f6fed",
  Brisbane: "#1f9d6a",
  Copenhagen: "#d4652f",
  Dunkirk: "#7a4de0",
  Edinburgh: "#c43b5a",
};

function colorFor(dest) {
  if (COLORS[dest]) return COLORS[dest];
  return "#5c6b7a";
}

var SHIP_LENGTH = 8;
var SHIP_WIDTH = 5;
var SHIP_HEIGHT = 3;

function makeBox(item) {
  var box = document.createElement("div");
  box.className = "box";
  box.style.backgroundColor = colorFor(item.dest);
  var name = document.createElement("b");
  name.textContent = item.dest;
  var weight = document.createElement("span");
  weight.textContent = String(item.weight);
  box.appendChild(name);
  box.appendChild(weight);
  return box;
}

function drawYard(stacks, yard, legend, prefix) {
  yard.innerHTML = "";
  if (legend) {
    legend.innerHTML = "";
  }
  var seen = {};
  for (var s = 0; s < stacks.length; s++) {
    var col = document.createElement("div");
    col.className = "stack";
    var pile = document.createElement("div");
    pile.className = "pile";
    for (var i = 0; i < stacks[s].length; i++) {
      var item = stacks[s][i];
      pile.appendChild(makeBox(item));
      if (legend && !seen[item.dest]) {
        seen[item.dest] = true;
        var swatch = document.createElement("span");
        swatch.className = "swatch";
        var chip = document.createElement("i");
        chip.style.background = colorFor(item.dest);
        swatch.appendChild(chip);
        swatch.appendChild(document.createTextNode(item.dest));
        legend.appendChild(swatch);
      }
    }
    var floor = document.createElement("div");
    floor.className = "floor";
    var label = document.createElement("div");
    label.className = "stack-name";
    label.textContent = prefix + (s + 1);
    col.appendChild(pile);
    col.appendChild(floor);
    col.appendChild(label);
    yard.appendChild(col);
  }
}

function drawShip(hold, shipYard) {
  var bay;
  var row;
  var i;
  shipYard.innerHTML = "";
  var corner = document.createElement("div");
  shipYard.appendChild(corner);
  for (bay = 0; bay < SHIP_LENGTH; bay++) {
    var acrossLabel = document.createElement("div");
    acrossLabel.className = "axis";
    acrossLabel.textContent = String(bay + 1);
    shipYard.appendChild(acrossLabel);
  }
  for (row = 0; row < SHIP_WIDTH; row++) {
    var sideLabel = document.createElement("div");
    sideLabel.className = "axis";
    sideLabel.textContent = String(row + 1);
    shipYard.appendChild(sideLabel);
    for (bay = 0; bay < SHIP_LENGTH; bay++) {
      var cell = document.createElement("div");
      cell.className = "deck-cell";
      var column = hold[bay][row];
      for (i = 0; i < column.length; i++) {
        var item = column[i];
        var chip = document.createElement("div");
        chip.className = "chip";
        chip.style.background = colorFor(item.dest);
        chip.title = item.dest + " " + item.weight;
        cell.appendChild(chip);
      }
      for (i = column.length; i < SHIP_HEIGHT; i++) {
        var empty = document.createElement("div");
        empty.className = "chip empty-slot";
        cell.appendChild(empty);
      }
      shipYard.appendChild(cell);
    }
  }
}

var fileInput = document.getElementById("csv");
fileInput.addEventListener("change", function () {
  if (fileInput.files.length > 0) {
    fileInput.form.submit();
  }
});

var layoutNode = document.getElementById("layout-data");
if (layoutNode) {
  var data = JSON.parse(layoutNode.textContent);
  drawYard(
    data.yard,
    document.getElementById("yard"),
    document.getElementById("legend"),
    "Stack ",
  );
  var shipYard = document.getElementById("ship-yard");
  if (shipYard && data.ship) {
    drawShip(data.ship, shipYard);
  }
}
