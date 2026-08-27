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
