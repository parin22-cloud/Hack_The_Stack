import json
import os

from flask import Flask, render_template, request, send_from_directory

from planner import Planner, parse_csv, view_data, write_moves_csv

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True
HERE = os.path.dirname(os.path.abspath(__file__))


def save_upload(upload):
    raw = upload.read()
    text = raw.decode("utf-8-sig")
    name = os.path.basename(upload.filename)
    if name.strip() == "":
        name = "containers.csv"
    folder = os.path.join(HERE, "uploads")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name), "wb") as handle:
        handle.write(raw)
    return text, name


@app.route("/hero.jpg")
def hero_image():
    for name in os.listdir(HERE):
        if name.lower().endswith(".jpg"):
            return send_from_directory(HERE, name)
    return "Hero image was not found.", 404


@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    saved_name = None
    layout_json = None
    moves = None
    moves_name = None
    posted = request.method == "POST"

    if posted:
        text, saved_name = save_upload(request.files.get("csv"))
        try:
            containers = parse_csv(text)
            planner = Planner(containers)
            plan = planner.solve()
            moves = Planner.format_moves(plan)
            yard, ship = view_data(containers, planner.columns)
            layout_json = json.dumps({"yard": yard, "ship": ship})
            stem = os.path.splitext(saved_name)[0]
            moves_name = stem + "-moves.csv"
            write_moves_csv(os.path.join(HERE, moves_name), moves)
        except Exception as exc:
            error = str(exc).strip() or exc.__class__.__name__

    return render_template(
        "index.html",
        error=error,
        saved_name=saved_name,
        layout_json=layout_json,
        moves_name=moves_name,
        posted=posted,
    )


if __name__ == "__main__":
    # debug stays off so a missed error is not printed as a traceback page.
    app.run(debug=False)
