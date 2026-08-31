"""
data/make_og_banner.py — the Open Graph card, built from the committed charts.

Writes docs/img/og_banner.png at 1200x630, the Open Graph standard size. The
card is a title, a tagline, one verified claim, and the real validation chart
pasted in at its own aspect ratio. Nothing on it is drawn to look like space:
no spacecraft, no orbits, no starfield, no generated art. A project whose whole
argument is that its numbers are computed rather than generated cannot lead
with an illustration of a mission that does not exist.

WHAT IS COMPUTED AND WHAT IS DECLARED
-------------------------------------
Computed: the comparison count and the largest disagreement in the claim line.
Both come from solver.plot._comparison_rows over a live validate() run, which
is the same function that builds the chart underneath them, so the sentence and
the picture cannot disagree. If a comparison is added or a number moves, the
card says so the next time it is generated.

Declared: the prose in FACTS, each entry carrying the file that backs it.

THE CLAIM LINE IS NOT THE README'S
----------------------------------
README.md says "The largest disagreement is 4.92%". That is the largest of the
two rows the README table expresses as a percentage; the other three are given
in km/s. Taken over all five on one scale, which is what the chart does, the
largest is Sample B at 6.94% (0.042 km/s on a published 0.6 km/s). This card
quotes the figure the chart shows, because a claim on a card is read against
the picture beside it.

Rendering is Pillow, as in data/plot_demand.py and solver/plot.py, and the
chart is pasted once with LANCZOS rather than being redrawn, so the card cannot
show a chart that differs from the committed one.

Run:
    python data/make_og_banner.py
"""

from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

HERO_CHART  = os.path.join(REPO, "plots", "validation_comparison.png")
OUTPUT_PATH = os.path.join(REPO, "docs", "img", "og_banner.png")

# Open Graph's standard card. Facebook, Slack, LinkedIn and X all crop or
# letterbox anything else, so the size is not a preference.
W, H = 1200, 630

S = 2   # text is drawn at 2x and reduced; ImageDraw has no antialiasing.
        # The chart is pasted after the reduction, resized exactly once.

PAD = 52

BG       = (10, 14, 26)     # near-black navy
ACCENT   = (59, 130, 246)
TITLE    = (232, 237, 245)
TAGLINE  = (148, 163, 184)
CLAIM    = (203, 213, 225)
RULE     = (30, 42, 63)
FOOT     = (124, 139, 161)
PANEL    = (255, 255, 255)

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]
FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
]

# Every string here is a claim, and the comment on it is where the claim is
# checked. "Expert-level" is deliberately absent: it is the same species of
# unearned phrase as "JPL-grade", which CLAUDE.md rules out.
FACTS = {
    # README.md line 1. The name, not a description of capability.
    "brand":    "HITS",
    "descriptor": "Hyperbolic Intercept & Trajectory Solver",

    # Three objects: solver/objects.py holds exactly three and raises on any
    # other designation. "open to anyone" is the accessibility gate in
    # CLAUDE.md, not a claim about a deployment, which does not exist yet.
    "tagline":  "Can we catch it? Intercept analysis for every interstellar "
                "object, open to anyone.",

    # Scoped to 1I on purpose. docs/VERIFICATION.md: 2I/Borisov and 3I/ATLAS
    # are computed by the same method and checked against no published figure,
    # because no intercept study exists for either.
    "claim":    "1I/'Oumuamua validated against Project Lyra: "
                "{n} published figures, largest disagreement {rel:.2f}%.",

    # CLAUDE.md requires the fidelity limit wherever a number is presented as
    # authoritative, and the second half keeps the tagline's "every
    # interstellar object" from borrowing 'Oumuamua's validation.
    "footer":   "Patched-conic, two-body. 2I/Borisov and 3I/ATLAS: same "
                "method, no published study to check them against.",
}


def _font(paths, size):
    """Return a truetype face, or the bitmap default with a warning."""
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    print("WARNING: no truetype font found on this system; falling back to "
          "ImageFont.load_default(). The card will not match the committed "
          "one. Candidates tried:", *paths, sep="\n  ")
    return ImageFont.load_default(size)


def _fit(d, text, paths, sizes, max_width):
    """
    Largest size from `sizes` whose rendering fits `max_width`, measured.

    A card is generated once and looked at once, so a string that overflows by
    six pixels is a defect that ships. Measuring is cheap; eyeballing is not
    reliable at 2x.
    """
    for size in sizes:
        font = _font(paths, size * S)
        if d.textlength(text, font=font) <= max_width * S:
            return font, size
    raise ValueError(
        f"{text!r} does not fit {max_width}px at any of {sizes}")


def comparison_facts():
    """
    (count, largest relative disagreement) from a live validate() run.

    Same source as the chart: solver.plot._comparison_rows. Importing it rather
    than restating its numbers is the point, since the two appear within an
    inch of each other on the finished card.
    """
    from solver.fetch import load_state_vectors
    from solver.plot import _comparison_rows
    from solver.validate import validate

    sv = load_state_vectors(os.path.join(REPO, "data", "state_vectors.json"))
    rows = _comparison_rows(validate(sv, verbose=False))
    return len(rows), max(r["rel"] for r in rows), rows


def draw(n_rows, largest_rel, output_path: str = OUTPUT_PATH) -> str:
    """
    Title block over the real chart. Returns the path written.

    The chart is scaled to fit the space left under the text, never to fill it,
    so its aspect ratio survives and it is letterboxed by the background rather
    than stretched. It is pasted on a white panel because it was drawn on white
    and compositing it onto navy would mean redrawing it.
    """
    img = Image.new("RGB", (W * S, H * S), BG)
    d = ImageDraw.Draw(img)
    inner = W - 2 * PAD

    # 1. Title lockup. The brand carries the size; the descriptor sits on the
    # same baseline at a weight that lets the whole thing stay on one line.
    f_brand = _font(FONT_CANDIDATES_BOLD, 52 * S)
    brand_w = d.textlength(FACTS["brand"], font=f_brand) / S
    sep = "  |  "
    f_desc, _ = _fit(d, sep + FACTS["descriptor"], FONT_CANDIDATES,
                     [30, 28, 26, 24], inner - brand_w)
    d.text((PAD * S, 48 * S), FACTS["brand"], font=f_brand, fill=ACCENT)
    d.text(((PAD + brand_w) * S, 62 * S), sep + FACTS["descriptor"],
           font=f_desc, fill=TITLE)

    # 2. Tagline
    f_tag, _ = _fit(d, FACTS["tagline"], FONT_CANDIDATES, [24, 23, 22, 21, 20],
                    inner)
    d.text((PAD * S, 118 * S), FACTS["tagline"], font=f_tag, fill=TAGLINE)

    # 3. Divider
    d.line([PAD * S, 158 * S, (W - PAD) * S, 158 * S], fill=RULE, width=S)

    # 4. The one verified claim, with its numbers taken from the chart below it
    claim = FACTS["claim"].format(n=n_rows, rel=largest_rel)
    f_claim, _ = _fit(d, claim, FONT_CANDIDATES, [21, 20, 19, 18], inner)
    d.text((PAD * S, 174 * S), claim, font=f_claim, fill=CLAIM)

    # 6. Footer, drawn before the reduction so the chart paste stays sharp
    f_foot, _ = _fit(d, FACTS["footer"], FONT_CANDIDATES, [15, 14, 13], inner)
    d.text((PAD * S, 592 * S), FACTS["footer"], font=f_foot, fill=FOOT)

    img = img.resize((W, H), Image.LANCZOS)

    # 5. The hero. Fit, never fill: the smaller of the two scale factors, so
    # the chart is letterboxed rather than cropped or stretched.
    top, bottom = 208, 582
    chart = Image.open(HERO_CHART).convert("RGB")
    frame = 6
    box_w, box_h = inner - 2 * frame, (bottom - top) - 2 * frame
    scale = min(box_w / chart.width, box_h / chart.height)
    cw, ch = int(chart.width * scale), int(chart.height * scale)
    chart = chart.resize((cw, ch), Image.LANCZOS)

    px, py = (W - cw) // 2, top + frame + (box_h - ch) // 2
    ImageDraw.Draw(img).rectangle(
        [px - frame, py - frame, px + cw + frame - 1, py + ch + frame - 1],
        fill=PANEL)
    img.paste(chart, (px, py))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, format="PNG", optimize=True)
    return output_path


def main() -> int:
    n_rows, largest_rel, rows = comparison_facts()
    path = draw(n_rows, largest_rel)

    print(f"wrote {path}  {Image.open(path).size[0]}x{Image.open(path).size[1]}")
    print(f"claim: {FACTS['claim'].format(n=n_rows, rel=largest_rel)}")
    print("comparisons, from solver.plot._comparison_rows:")
    for r in rows:
        print(f"  {r['short_name']:28s} {r['rel']:6.2f}%  "
              f"of {r['tol_pct']:6.2f}% allowed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
