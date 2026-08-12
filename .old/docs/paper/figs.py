"""Figures for the paper. Vector PDF, print-first, validated palette."""
import json, pathlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

R = pathlib.Path("/home/brandonin/Documents/symbolic-ai-old-A")
OUT = pathlib.Path("/tmp/paper/figs"); OUT.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#d9d8d4"

plt.rcParams.update({
    "figure.dpi": 200, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
    "font.size": 8.5, "axes.labelsize": 8.5, "axes.titlesize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "axes.edgecolor": GRID, "axes.linewidth": 0.8, "axes.labelcolor": INK,
    "text.color": INK, "xtick.color": INK2, "ytick.color": INK2,
    "xtick.major.width": 0.8, "ytick.major.width": 0.8,
    "grid.color": GRID, "grid.linewidth": 0.6,
    "legend.frameon": False, "figure.facecolor": "white", "axes.facecolor": "white",
})


def despine(ax, keep=("left", "bottom")):
    for s in ("top", "right", "left", "bottom"):
        ax.spines[s].set_visible(s in keep)


# ---------------------------------------------------------------- Fig 2
def fig_scaling():
    d = json.loads((R / "results/symbolic_suite.json").read_text())
    cells = d["gridworld_scaling"]["cells"]
    xs = [c["size"] for c in cells]
    series = [("induced world model (26 params)", "world_model-001", BLUE, "o"),
              ("induced rule list (42 params)", "relational-001", AQUA, "s"),
              ("transformer (13.97M params)", "symbolic-ai-old-A", ORANGE, "^")]
    fig, ax = plt.subplots(figsize=(4.9, 2.9))
    ax.grid(axis="y", zorder=0)
    ax.set_axisbelow(True)
    for label, key, c, m in series:
        ys = [cells[i]["arms"][key]["success"] for i in range(len(cells))]
        ax.plot(xs, ys, color=c, lw=2, marker=m, ms=5, mec="white", mew=1.0,
                label=label, zorder=3, clip_on=False)
        ax.annotate(f"{ys[-1]:.2f}", (xs[-1], ys[-1]), textcoords="offset points",
                    xytext=(7, -1), color=c, fontsize=8, weight="bold")
    ax.axvspan(4.4, 5.6, color=GRID, alpha=0.45, lw=0, zorder=1)
    ax.text(5, 1.06, "induced here", ha="center", fontsize=7.5, color=INK2)
    ax.set_xlim(4.4, 22.5); ax.set_ylim(0, 1.05)
    ax.set_xticks(xs); ax.set_yticks([0, .25, .5, .75, 1.0])
    ax.set_xlabel("grid size (side length)"); ax.set_ylabel("success rate")
    ax.legend(loc="lower left", bbox_to_anchor=(0.16, 0.06), labelspacing=0.35)
    despine(ax)
    fig.savefig(OUT / "scaling.pdf"); fig.savefig(OUT / "scaling.png", dpi=200)


# ---------------------------------------------------------------- Fig 3
def fig_bimodality():
    d = json.loads((R / "results/curriculum_full.json").read_text())
    rows = [r for r in d["lessons"] if isinstance(r.get("arms", {}).get("random-001", {}).get("acc"), float)]
    def margins(arm):
        v = [r["arms"][arm]["acc"] - r["arms"]["random-001"]["acc"]
             for r in rows if isinstance(r["arms"].get(arm, {}).get("acc"), float)]
        return sorted(v, reverse=True)
    q, rel = margins("qsynth-001"), margins("relational-001")
    fig, ax = plt.subplots(figsize=(4.9, 2.9))
    ax.grid(axis="y", zorder=0); ax.set_axisbelow(True)
    ax.plot(range(1, len(q) + 1), q, color=BLUE, lw=2, label="query-program induction", zorder=3)
    ax.plot(range(1, len(rel) + 1), rel, color=AQUA, lw=2, label="rule-list induction", zorder=3)
    ax.axhline(0, color=INK2, lw=0.8, ls=(0, (3, 3)), zorder=2)
    n_exact = sum(1 for r in rows if isinstance(r["arms"].get("qsynth-001", {}).get("acc"), float)
                  and r["arms"]["qsynth-001"]["acc"] >= 0.90)
    ax.axvline(n_exact, color=BLUE, lw=0.8, ls=(0, (2, 2)), zorder=2)
    ax.annotate(f"{n_exact} solved exactly", (n_exact, 0.80), xytext=(10, 0),
                textcoords="offset points", fontsize=7.5, color=BLUE)
    ax.text(len(q) * 0.62, 0.05, "chance", fontsize=7.5, color=INK2, va="bottom")
    ax.set_xlim(1, len(q)); ax.set_ylim(-0.12, 0.92)
    ax.set_xlabel("lessons, ranked"); ax.set_ylabel("accuracy above chance")
    ax.legend(loc="upper right", labelspacing=0.35)
    despine(ax)
    fig.savefig(OUT / "bimodality.pdf"); fig.savefig(OUT / "bimodality.png", dpi=200)


# ---------------------------------------------------------------- Fig 4
def fig_capabilities():
    d = json.loads((R / "results/curriculum_full.json").read_text())
    caps = d["summary"]["capabilities"]
    rows = [(c, v["qsynth-001"] - v["random-001"]) for c, v in caps.items()
            if isinstance(v.get("qsynth-001"), float) and isinstance(v.get("random-001"), float)
            and c != "(unlabelled)"]
    counts = {}
    for r in d["lessons"]:
        for c in r.get("capabilities") or []:
            counts[c] = counts.get(c, 0) + 1
    # among the capabilities at chance, show the most represented ones rather
    # than an arbitrary alphabetical slice
    zero = sorted([r for r in rows if r[1] <= 0.02], key=lambda t: -counts.get(t[0], 0))[:6]
    top = sorted(rows, key=lambda t: t[1])[-8:]
    rows = sorted(zero, key=lambda t: t[1]) + top
    labels = [c.replace("_", " ") for c, _ in rows]
    vals = [v for _, v in rows]
    fig, ax = plt.subplots(figsize=(4.9, 3.5))
    ax.grid(axis="x", zorder=0); ax.set_axisbelow(True)
    colors = [BLUE if v > 0.02 else ORANGE for v in vals]
    ax.barh(range(len(vals)), vals, color=colors, height=0.62, zorder=3)
    for i, v in enumerate(vals):
        ax.text(v + 0.008, i, f"{v:+.2f}", va="center", fontsize=7.5,
                color=BLUE if v > 0.02 else ORANGE)
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels)
    ax.set_xlim(-0.01, 0.46); ax.set_xlabel("mean accuracy above chance")
    ax.axvline(0, color=INK2, lw=0.8)
    despine(ax, keep=("bottom",))
    ax.tick_params(axis="y", length=0)
    fig.savefig(OUT / "capabilities.pdf"); fig.savefig(OUT / "capabilities.png", dpi=200)


# ---------------------------------------------------------------- Fig 5
def fig_mechanisms():
    # measured before/after, each recorded in the commit that introduced it
    data = [("unification", "PositionMatch", 0.53, 1.00),
            ("translation", "Align", 0.07, 1.00),
            ("expression eval", "TreeEval", 0.21, 1.00),
            ("knowledge refactoring", "PerCandidate", 0.25, 1.00),
            ("value learning", "PerCandidate", 0.10, 0.88),
            ("counting quantifier", "Count(q)", 0.57, 0.90),
            ("context-free language", "Fold", 0.55, 1.00),
            ("parse depth", "Fold", 0.00, 1.00),
            ("next symbol", "SuccessorLookup", 0.16, 1.00)]
    data.sort(key=lambda t: t[3] - t[2])
    fig, ax = plt.subplots(figsize=(4.9, 3.2))
    ax.grid(axis="x", zorder=0); ax.set_axisbelow(True)
    for i, (les, mech, a, b) in enumerate(data):
        ax.plot([a, b], [i, i], color=GRID, lw=2.2, zorder=2, solid_capstyle="round")
        ax.plot(a, i, "o", color=ORANGE, ms=6, mec="white", mew=1.0, zorder=3)
        ax.plot(b, i, "o", color=BLUE, ms=6, mec="white", mew=1.0, zorder=3)
        ax.text(b + 0.025, i, mech, va="center", fontsize=7.2, color=INK2)
    ax.set_yticks(range(len(data)))
    ax.set_yticklabels([d[0] for d in data])
    ax.set_xlim(-0.03, 1.32); ax.set_xticks([0, .25, .5, .75, 1.0])
    ax.set_xlabel("accuracy on held-out episodes")
    ax.plot([], [], "o", color=ORANGE, ms=6, label="before")
    ax.plot([], [], "o", color=BLUE, ms=6, label="after")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, labelspacing=0.35,
              columnspacing=1.4, handletextpad=0.4)
    despine(ax, keep=("bottom",))
    ax.tick_params(axis="y", length=0)
    fig.savefig(OUT / "mechanisms.pdf"); fig.savefig(OUT / "mechanisms.png", dpi=200)


for f in (fig_scaling, fig_bimodality, fig_capabilities, fig_mechanisms):
    f(); print("ok:", f.__name__)
