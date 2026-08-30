"""
solver/plot.py — plotly-based C3 porkchop slice plot.

Writes plots/c3_floor_slice.html.
No matplotlib. Plotly only (CONVENTIONS.md: plotting is plotly).

Grid axes (revised for Fig. 1 reproduction):
  x-axis: departure date (2018-2032)
  y-axis: duration in years (5-30)
  Two markers: global floor (physical_launch_edge or interior) and 2027 column.
  Reference lines: Lyra 703 km²/s² floor, Lyra 1400 km²/s² 2027 point.
"""

from __future__ import annotations

import os
import numpy as np
from astropy.time import Time
import plotly.graph_objects as go


def plot_c3_slice(
    grid_result,
    output_path: str = "plots/c3_floor_slice.html",
    retrieval_date: str = "",
    c3_floor_published: float = 703.0,
    c3_2027_published: float = 1400.0,
    c3_floor_edge_type: str = "",
    c3_2027_val: float = None,
    c3_2027_dep_iso: str = "",
    c3_2027_tof_yr: float = None,
) -> str:
    """
    Plot the C3 porkchop slice (Fig. 1 reproduction) and write to HTML.

    Returns the path written.
    Marks global floor and 2027 column minimum as separate markers.
    Draws reference lines at Lyra's 703 and 1400 km²/s².
    """
    c3_grid  = grid_result.c3_grid        # (n_dep, n_tof)
    dep_jds  = grid_result.departure_jds  # (n_dep,)
    tof_days = grid_result.tof_days       # (n_tof,)

    # Convert departure JDs to ISO strings (date only)
    dep_isos = [Time(jd, format="jd", scale="tdb").iso[:10] for jd in dep_jds]
    # Convert TOF axis to years
    tof_yrs = tof_days / 365.25

    # Clamp C3 for display
    c3_display = np.where(c3_grid > 5000, np.nan, c3_grid)

    if not np.any(np.isfinite(c3_display)):
        print("  WARNING: No finite C3 values in grid — cannot plot.")
        return ""

    # Floor minimum
    min_val, min_dep_jd, min_tof_days = grid_result.c3_minimum
    min_dep_iso = Time(min_dep_jd, format="jd", scale="tdb").iso[:10]
    min_tof_yr  = min_tof_days / 365.25
    is_physical = (c3_floor_edge_type == "physical_launch_edge")
    floor_color = "lime" if is_physical else "orange"
    floor_note  = " (physical edge)" if is_physical else " (duration boundary — SUSPECT)"

    title = (
        f"C3 porkchop — ECLIPJ2000 heliocentric — patched-conic — "
        f"retrieved {retrieval_date}"
    )

    fig = go.Figure()

    fig.add_trace(go.Contour(
        z=c3_display.T,
        x=dep_isos,
        y=tof_yrs,
        colorscale="Viridis_r",
        contours=dict(start=0, end=5000, size=200),
        colorbar=dict(title="C3 (km²/s²)"),
        name="C3",
        hovertemplate="Departure: %{x}<br>Duration: %{y:.1f} yr<br>C3: %{z:.1f} km²/s²<extra></extra>",
    ))

    # Mark global floor
    fig.add_trace(go.Scatter(
        x=[min_dep_iso],
        y=[min_tof_yr],
        mode="markers+text",
        marker=dict(size=14, color=floor_color, symbol="star"),
        text=[f"  Floor: {min_val:.0f} km²/s²{floor_note}"],
        textposition="middle right",
        name=f"Floor {min_val:.0f} km²/s²",
        hovertemplate=(
            f"Floor: {min_val:.1f} km²/s²<br>{min_dep_iso}<br>"
            f"TOF: {min_tof_yr:.1f} yr{floor_note}<extra></extra>"
        ),
    ))

    # Mark 2027 column minimum at ~15yr if provided
    if c3_2027_val is not None and c3_2027_dep_iso and c3_2027_tof_yr is not None:
        fig.add_trace(go.Scatter(
            x=[c3_2027_dep_iso],
            y=[c3_2027_tof_yr],
            mode="markers+text",
            marker=dict(size=12, color="red", symbol="diamond"),
            text=[f"  2027: {c3_2027_val:.0f} km²/s²"],
            textposition="middle right",
            name=f"2027 col {c3_2027_val:.0f} km²/s²",
        ))

    # Reference line: Lyra 703 floor
    fig.add_hline(
        y=min_tof_yr, line_dash="dot", line_color="lime",
        annotation_text=f"Floor min TOF: {min_tof_yr:.0f} yr",
        annotation_position="bottom right",
    )

    # Annotation: Lyra reference values
    fig.add_annotation(
        x=dep_isos[0], y=float(tof_yrs[0]),
        text=(
            f"Lyra floor: {c3_floor_published:.0f} km²/s²<br>"
            f"Lyra 2027:  {c3_2027_published:.0f} km²/s²<br>"
            f"Hein et al. 2019"
        ),
        showarrow=False,
        bgcolor="white",
        bordercolor="gray",
        font=dict(size=10),
        xanchor="left",
    )

    fig.update_layout(
        title=title,
        xaxis_title="Departure date",
        yaxis_title="Mission duration (years)",
        xaxis=dict(tickangle=-45),
        height=600,
        width=950,
    )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.write_html(output_path)

    print(f"\nPlot written to {output_path}")
    print(f"Floor: {min_val:.2f} km²/s² at {min_dep_iso}, TOF {min_tof_yr:.1f} yr [{c3_floor_edge_type}]")
    if c3_2027_val is not None:
        print(f"2027 col (~15yr): {c3_2027_val:.2f} km²/s² at {c3_2027_dep_iso}")
    print(f"Lyra references: floor {c3_floor_published} km²/s², 2027 {c3_2027_published} km²/s²")

    return output_path


def plot_validation_comparison(
    results,
    output_path: str = "plots/validation_comparison.html",
) -> str:
    """
    HITS computed against published Lyra figures, all five quantities, one plot.

    The five comparisons carry three different units and span three orders of
    magnitude, from 0.6 km/s to 1400 km²/s², so plotting the values themselves
    on shared axes would say more about magnitude than agreement. The axis is
    therefore relative difference in percent, which is unit-free and is the
    quantity the tolerances are judged on. Each row also carries its tolerance
    as a marker, so the reading is direct: a bar short of its marker agrees
    within the tolerance that was declared for it before the comparison ran.

    Every number in a row's label is a canonical manifest rendering, pulled by
    entry id, for the same reason the printed validation rows are: a figure in
    a plot that disagrees with the figure in the manifest is drift, and pulling
    both from one source makes it impossible. The two derived quantities are
    the tolerance percentages for the frame gate and the two arrival samples,
    whose tolerances are declared in km/s rather than as fractions. They are
    computed here for display and are not claims about solver output.

    Parameters
    ----------
    results : solver.validate.ValidationResults
        A completed validate() run, manifest attached.

    Returns
    -------
    The path written.
    """
    if results.manifest is None:
        raise ValueError(
            "plot_validation_comparison needs the manifest that validate() "
            "attaches; the labels are manifest renderings, not format specifiers")
    if results.c3 is None or results.arrival_a is None or results.arrival_b is None:
        raise ValueError(
            "incomplete validation results: the frame gate failed, so the "
            "downstream comparisons were skipped and there is nothing to plot")

    c = results.manifest.canonical
    fg, c3, a, b = results.frame_gate, results.c3, results.arrival_a, results.arrival_b

    rows = [
        dict(
            name="Perihelion v∞<br>(frame gate)",
            rel=abs(fg.rel_diff_pct),
            tol_pct=100.0 * fg.tolerance_km_s / fg.published_km_s,
            label=(f"HITS {c('validate.frame_gate.computed')} vs Lyra "
                   f"{c('validate.frame_gate.published')} km/s"),
            citation=fg.citation,
        ),
        dict(
            name="C3, 2027 launch",
            rel=abs(c3.c3_2027_rel_diff_pct),
            tol_pct=100.0 * c3.c3_2027_tolerance_frac,
            label=(f"HITS {c('validate.c3.y2027.computed')} vs Lyra "
                   f"{c('validate.c3.y2027.published')} km²/s²"),
            citation=c3.c3_2027_citation,
        ),
        dict(
            name="C3 floor",
            rel=abs(c3.c3_floor_rel_diff_pct),
            tol_pct=100.0 * c3.c3_floor_tolerance_frac,
            label=(f"HITS {c('validate.c3.floor.computed')} vs Lyra "
                   f"{c('validate.c3.floor.published')} km²/s²"),
            citation=c3.c3_floor_citation,
        ),
        dict(
            name="Sample A arrival v∞2",
            rel=abs(a.rel_diff_pct),
            tol_pct=100.0 * a.tolerance_km_s / a.published_km_s,
            label=(f"HITS {c('validate.arrival_a.v_inf2')} vs Lyra "
                   f"{c('validate.arrival_a.published')} km/s"),
            citation=a.citation,
        ),
        dict(
            name="Sample B arrival v∞2",
            rel=abs(b.rel_diff_pct),
            tol_pct=100.0 * b.tolerance_km_s / b.published_km_s,
            label=(f"HITS {c('validate.arrival_b.v_inf2')} vs Lyra "
                   f"{c('validate.arrival_b.published')} km/s"),
            citation=b.citation,
        ),
    ]
    rows.reverse()   # plotly draws the first category at the bottom

    names = [r["name"] for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=names,
        x=[r["rel"] for r in rows],
        orientation="h",
        marker_color="#2c7fb8",
        name="difference from published",
        text=[f"{r['rel']:.2f}%" for r in rows],
        textposition="outside",
        customdata=[[r["label"], r["citation"]] for r in rows],
        hovertemplate="%{customdata[0]}<br>difference %{x:.2f}%<br>%{customdata[1]}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        y=names,
        x=[r["tol_pct"] for r in rows],
        mode="markers",
        marker=dict(symbol="line-ns", size=22, line=dict(width=3, color="#d95f02")),
        name="declared tolerance",
        hovertemplate="tolerance %{x:.1f}%<extra></extra>",
    ))

    # Labels in one column outside the axis, so the eye compares bar lengths
    # rather than tracking text that moves with the data.
    for r in rows:
        fig.add_annotation(
            x=63.0, y=r["name"],
            text=r["label"], showarrow=False, xanchor="left",
            font=dict(size=11, color="#444"),
        )

    fig.update_layout(
        title=(
            "HITS against published Project Lyra figures<br>"
            "<sub>Hein et al. 2019, Acta Astronautica 161, 552-561. "
            f"Ephemerides retrieved {results.retrieval_date[:10]}. "
            "Patched-conic, 2-body: no n-body integration, no non-gravitational "
            "forces.</sub>"
        ),
        xaxis_title="difference from published value (%), lower is closer",
        height=520, width=1050,
        margin=dict(l=170, r=330, t=110, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        plot_bgcolor="white",
    )
    fig.update_xaxes(range=[0, 62], gridcolor="#eee", zeroline=False)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.write_html(output_path)

    print(f"\nComparison plot written to {output_path}")
    for r in reversed(rows):
        print(f"  {r['name'].replace('<br>', ' '):28s} "
              f"diff {r['rel']:6.2f}%  tolerance {r['tol_pct']:6.2f}%  {r['label']}")
    return output_path
