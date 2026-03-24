from typing import List

import numpy as np
import plotly.graph_objects as go
from plotly.colors import qualitative as pcolors


def is_large_temp(te_val, raw_err):
    return (te_val == 0 and raw_err > 0) or (raw_err > te_val * 2)


def is_large_dens(n_val, raw_err):
    return (n_val == 0 and raw_err > 0) or (raw_err > n_val * 1.1)


def prepare_fiber_data(fibers):
    """
    Подготовить и кэшировать данные по каждому волокну один раз,
    чтобы потом не дергать getattr в циклах многократно.
    """
    prepared = []
    for fiber in fibers:
        prepared.append(
            {
                "fiber": fiber,
                "z_cm": getattr(fiber, "z_cm", None),
                "temperatures": getattr(fiber, "temperatures", None),
                "density": getattr(fiber, "density", None),
                "errors_T": getattr(fiber, "errors_T", None) or [],
                "errors_n": getattr(fiber, "errors_n", None) or [],
            }
        )
    return prepared


def collect_time_data(
        prep_item, selected_idxs, combiscope_times, value_key, error_key, is_large_func
):
    values = prep_item[value_key]
    if not values:
        return None
    errors = prep_item[error_key]
    data = {"good": [[], [], [], []], "bad": [[], [], [], []]}  # x, y, err_up, err_down
    for idx, t_time in zip(selected_idxs, combiscope_times):
        if idx < len(values):
            try:
                val = float(values[idx])
            except Exception:
                continue
            raw_err = abs(float(errors[idx])) if idx < len(errors) else 0.0
            err_up = raw_err
            err_down = min(raw_err, val)
            key = "bad" if is_large_func(val, raw_err) else "good"
            data[key][0].append(t_time)
            data[key][1].append(val)
            data[key][2].append(err_up)
            data[key][3].append(err_down)
    return data


def collect_z_data(prepared_fibers, idx, value_key, error_key, is_large_func):
    data = {"good": [[], [], [], []], "bad": [[], [], [], []]}
    for item in prepared_fibers:
        values = item[value_key]
        if values and idx < len(values):
            try:
                val = float(values[idx])
            except Exception:
                continue
            errors = item[error_key]
            raw_err = abs(float(errors[idx])) if idx < len(errors) else 0.0
            err_up = raw_err
            err_down = min(raw_err, val)
            key = "bad" if is_large_func(val, raw_err) else "good"
            data[key][0].append(item["z_cm"])
            data[key][1].append(val)
            data[key][2].append(err_up)
            data[key][3].append(err_down)
    return data


def collect_pe_t_data(prep_item, selected_idxs, combiscope_times):
    temps = prep_item["temperatures"]
    dens = prep_item["density"]
    if not temps or not dens:
        return None
    errors_T = prep_item["errors_T"]
    errors_n = prep_item["errors_n"]
    data = {"good": [[], [], [], []], "bad": [[], [], [], []]}
    for idx, t_time in zip(selected_idxs, combiscope_times):
        if idx < len(temps) and idx < len(dens):
            try:
                te_val = float(temps[idx])
                n_val = float(dens[idx])
            except Exception:
                continue
            p_val = n_val * te_val
            raw_err_T = abs(float(errors_T[idx])) if idx < len(errors_T) else 0.0
            raw_err_n = abs(float(errors_n[idx])) if idx < len(errors_n) else 0.0
            if te_val == 0.0:
                rel_T = float("inf") if raw_err_T > 0 else 0.0
            else:
                rel_T = raw_err_T / te_val
            if n_val == 0.0:
                rel_n = float("inf") if raw_err_n > 0 else 0.0
            else:
                rel_n = raw_err_n / n_val
            rel_p = rel_T + rel_n
            err_up = abs(p_val * rel_p)
            err_down = min(err_up, p_val)
            is_large = (p_val == 0 and (raw_err_T > 0 or raw_err_n > 0)) or (
                    rel_p > 1.0
            )
            key = "bad" if is_large else "good"
            data[key][0].append(t_time)
            data[key][1].append(p_val)
            data[key][2].append(err_up)
            data[key][3].append(err_down)
    return data


def collect_pe_z_data(prepared_fibers, idx):
    data = {"good": [[], [], [], []], "bad": [[], [], [], []]}
    for item in prepared_fibers:
        temps = item["temperatures"]
        dens = item["density"]
        if temps and dens and idx < len(temps) and idx < len(dens):
            try:
                te_val = float(temps[idx])
                n_val = float(dens[idx])
            except Exception:
                continue
            p_val = n_val * te_val
            errors_T = item["errors_T"]
            errors_n = item["errors_n"]
            raw_err_T = abs(float(errors_T[idx])) if idx < len(errors_T) else 0.0
            raw_err_n = abs(float(errors_n[idx])) if idx < len(errors_n) else 0.0
            if te_val == 0.0:
                rel_T = float("inf") if raw_err_T > 0 else 0.0
            else:
                rel_T = raw_err_T / te_val
            if n_val == 0.0:
                rel_n = float("inf") if raw_err_n > 0 else 0.0
            else:
                rel_n = raw_err_n / n_val
            rel_p = rel_T + rel_n
            err_up = abs(p_val * rel_p)
            err_down = min(err_up, p_val)
            is_large = (p_val == 0 and (raw_err_T > 0 or raw_err_n > 0)) or (
                    rel_p > 1.0
            )
            key = "bad" if is_large else "good"
            data[key][0].append(item["z_cm"])
            data[key][1].append(p_val)
            data[key][2].append(err_up)
            data[key][3].append(err_down)
    return data


def add_traces(
        fig,
        data,
        color,
        name,
        legend_group,
        mode,
        line_dash_good="solid",
        line_dash_bad="dash",
        marker_symbol_good="circle",
        marker_symbol_bad="x",
        marker_size_good=5,
        marker_size_bad=9,
        bad_line_width=2,
        showlegend_good=True,
        showlegend_bad=False,
        visible_good=True,
        visible_bad=False,
):
    good = data["good"]
    bad = data["bad"]
    if good[0]:
        fig.add_trace(
            go.Scatter(
                x=good[0],
                y=good[1],
                error_y=dict(
                    type="data", array=good[2], arrayminus=good[3], visible=True
                ),
                mode=mode,
                line=dict(color=color, dash=line_dash_good),
                marker=dict(
                    symbol=marker_symbol_good, size=marker_size_good, color=color
                ),
                name=name,
                legendgroup=legend_group,
                showlegend=showlegend_good,
                visible=visible_good,
            )
        )
        if bad[0]:
            fig.add_trace(
                go.Scatter(
                    x=bad[0],
                    y=bad[1],
                    error_y=dict(
                        type="data", array=bad[2], arrayminus=bad[3], visible=True
                    ),
                    mode=mode,
                    line=dict(color=color, dash=line_dash_bad),
                    marker=dict(
                        symbol=marker_symbol_bad,
                        size=marker_size_bad,
                        line=dict(width=bad_line_width),
                        color=color,
                    ),
                    name=name,
                    legendgroup=legend_group,
                    showlegend=showlegend_bad,
                    visible=visible_bad,
                )
            )
    else:
        if bad[0]:
            fig.add_trace(
                go.Scatter(
                    x=bad[0],
                    y=bad[1],
                    error_y=dict(
                        type="data", array=bad[2], arrayminus=bad[3], visible=True
                    ),
                    mode=mode,
                    line=dict(color=color, dash=line_dash_bad),
                    marker=dict(
                        symbol=marker_symbol_bad,
                        size=marker_size_bad,
                        line=dict(width=bad_line_width),
                        color=color,
                    ),
                    name=name,
                    legendgroup=legend_group,
                    showlegend=showlegend_good,
                    visible=visible_bad,
                )
            )


def make_interactive_plots(fibers, combiscope_times) -> List[str]:
    """
    Построение интерактивных графиков:

      1. Tₑ(t)
      2. nₑ(t)
      3. P(t) = nₑ * Tₑ
      4. Tₑ(z)
      5. nₑ(z)
      6. P(z) = nₑ * Tₑ

    """
    PALETTE = pcolors.Plotly

    combiscope_times_arr = np.array(combiscope_times, dtype=float)
    mask = (combiscope_times_arr >= 140) & (combiscope_times_arr <= 211)
    selected_idxs = np.where(mask)[0].tolist()
    combiscope_times = combiscope_times_arr[mask]

    if len(combiscope_times) == 0:
        return ["<p>Нет данных в диапазоне 150–220 мс</p>"]

    LEGEND_CONFIG_HOR = dict(
        orientation="h",
        x=0.5,
        xanchor="center",
        y=-0.08,
        yanchor="top",
        font=dict(size=10),
        tracegroupgap=0,
    )

    TEMP_FIG_HEIGHT = 420
    PROFILE_FIG_HEIGHT = 480
    COMPACT_BOTTOM_MARGIN = 100

    prepared_fibers = prepare_fiber_data(fibers)

    # 1. T_e(t)
    fig_T_t = go.Figure()
    for f_idx, item in enumerate(prepared_fibers):
        data = collect_time_data(
            item,
            selected_idxs,
            combiscope_times,
            "temperatures",
            "errors_T",
            is_large_temp,
        )
        if data is None:
            continue
        color = PALETTE[f_idx % len(PALETTE)]
        base_name = f"{item['z_cm']:.1f} cm"
        legend_group = base_name
        add_traces(fig_T_t, data, color, base_name, legend_group, "markers+lines")

    fig_T_t.update_layout(
        title="Tₑ(t)",
        xaxis_title="t (ms)",
        xaxis=dict(automargin=True, title_standoff=4),
        yaxis_title="Tₑ (eV)",
        yaxis=dict(range=[0, None], automargin=True),
        template="plotly_white",
        legend=LEGEND_CONFIG_HOR,
        height=TEMP_FIG_HEIGHT,
        margin=dict(l=60, r=20, t=60, b=COMPACT_BOTTOM_MARGIN),
    )

    # 2. n_e(t)
    fig_n_t = go.Figure()
    for f_idx, item in enumerate(prepared_fibers):
        data = collect_time_data(
            item, selected_idxs, combiscope_times, "density", "errors_n", is_large_dens
        )
        if data is None:
            continue
        color = PALETTE[f_idx % len(PALETTE)]
        base_name = f"{item['z_cm']:.1f} cm"
        legend_group = base_name
        add_traces(fig_n_t, data, color, base_name, legend_group, "markers+lines")

    fig_n_t.update_layout(
        title="nₑ(t)",
        xaxis_title="t (ms)",
        xaxis=dict(automargin=True, title_standoff=4),
        yaxis_title="nₑ (m⁻³)",
        yaxis=dict(rangemode="tozero", automargin=True),
        template="plotly_white",
        legend=LEGEND_CONFIG_HOR,
        height=TEMP_FIG_HEIGHT,
        margin=dict(l=60, r=20, t=60, b=COMPACT_BOTTOM_MARGIN),
    )

    # 3. P(t) = n * T
    fig_P_t = go.Figure()
    for f_idx, item in enumerate(prepared_fibers):
        data = collect_pe_t_data(item, selected_idxs, combiscope_times)
        if data is None:
            continue
        color = PALETTE[f_idx % len(PALETTE)]
        base_name = f"{item['z_cm']:.1f} cm"
        legend_group = base_name
        add_traces(fig_P_t, data, color, base_name, legend_group, "markers+lines")

    fig_P_t.update_layout(
        title="P(t) = nₑ·Tₑ",
        xaxis_title="t (ms)",
        xaxis=dict(automargin=True, title_standoff=4),
        yaxis_title="nₑ·Tₑ (m⁻³·eV)",
        yaxis=dict(range=[0, None], automargin=True),
        template="plotly_white",
        legend=LEGEND_CONFIG_HOR,
        height=TEMP_FIG_HEIGHT,
        margin=dict(l=60, r=20, t=60, b=COMPACT_BOTTOM_MARGIN),
    )

    # 4. T_e(z) — profiles
    fig_T_z = go.Figure()
    for time_idx, (idx, time_val) in enumerate(zip(selected_idxs, combiscope_times)):
        data = collect_z_data(
            prepared_fibers, idx, "temperatures", "errors_T", is_large_temp
        )
        color = PALETTE[time_idx % len(PALETTE)]
        time_name = f"{time_val:.1f} ms"
        legend_group = time_name
        add_traces(fig_T_z, data, color, time_name, legend_group, "lines+markers")

    fig_T_z.update_layout(
        title="Tₑ(Z)",
        xaxis_title="Z (cm)",
        xaxis=dict(automargin=True, title_standoff=4),
        yaxis_title="Tₑ (eV)",
        yaxis=dict(range=[0, None], automargin=True),
        template="plotly_white",
        legend=LEGEND_CONFIG_HOR,
        height=PROFILE_FIG_HEIGHT,
        margin=dict(l=60, r=20, t=60, b=COMPACT_BOTTOM_MARGIN),
    )

    # 5. n_e(z)
    fig_n_z = go.Figure()
    for time_idx, (idx, time_val) in enumerate(zip(selected_idxs, combiscope_times)):
        data = collect_z_data(
            prepared_fibers, idx, "density", "errors_n", is_large_dens
        )
        color = PALETTE[time_idx % len(PALETTE)]
        time_name = f"{time_val:.1f} ms"
        legend_group = time_name
        add_traces(fig_n_z, data, color, time_name, legend_group, "lines+markers")

    fig_n_z.update_layout(
        title="nₑ(Z)",
        xaxis_title="Z (cm)",
        xaxis=dict(automargin=True, title_standoff=4),
        yaxis_title="nₑ (m⁻³)",
        yaxis=dict(rangemode="tozero", automargin=True),
        template="plotly_white",
        legend=LEGEND_CONFIG_HOR,
        height=PROFILE_FIG_HEIGHT,
        margin=dict(l=60, r=20, t=60, b=COMPACT_BOTTOM_MARGIN),
    )

    # 6. P(z) = n * T
    fig_P_z = go.Figure()
    for time_idx, (idx, time_val) in enumerate(zip(selected_idxs, combiscope_times)):
        data = collect_pe_z_data(prepared_fibers, idx)
        color = PALETTE[time_idx % len(PALETTE)]
        time_name = f"{time_val:.1f} ms"
        legend_group = time_name
        add_traces(fig_P_z, data, color, time_name, legend_group, "lines+markers")

    fig_P_z.update_layout(
        title="P(Z) = nₑ·Tₑ",
        xaxis_title="Z (cm)",
        xaxis=dict(automargin=True, title_standoff=4),
        yaxis_title="nₑ·Tₑ (м⁻³·eV)",
        yaxis=dict(rangemode="tozero", automargin=True),
        template="plotly_white",
        legend=LEGEND_CONFIG_HOR,
        height=PROFILE_FIG_HEIGHT,
        margin=dict(l=60, r=20, t=60, b=COMPACT_BOTTOM_MARGIN),
    )

    return [
        fig_T_t.to_html(full_html=False, include_plotlyjs="cdn"),
        fig_n_t.to_html(full_html=False, include_plotlyjs=False),
        fig_P_t.to_html(full_html=False, include_plotlyjs=False),
        fig_T_z.to_html(full_html=False, include_plotlyjs=False),
        fig_n_z.to_html(full_html=False, include_plotlyjs=False),
        fig_P_z.to_html(full_html=False, include_plotlyjs=False),
    ]


def plot_separatrix_to_html(sep_data: dict, interactive: bool = False) -> str:
    x_range = [0.0, 0.58]
    y_range = [-0.55, 0.4]

    width = 900
    height = 700

    fig = go.Figure()

    if sep_data.get("body"):
        fig.add_trace(
            go.Scatter(
                x=sep_data["body"]["R"],
                y=sep_data["body"]["Z"],
                mode="lines",
                name="body",
                line=dict(color="black"),
            )
        )
    if sep_data.get("leg_1"):
        fig.add_trace(
            go.Scatter(
                x=sep_data["leg_1"]["R"],
                y=sep_data["leg_1"]["Z"],
                mode="lines",
                name="leg 1",
                line=dict(color="black"),
            )
        )
    if sep_data.get("leg_2"):
        fig.add_trace(
            go.Scatter(
                x=sep_data["leg_2"]["R"],
                y=sep_data["leg_2"]["Z"],
                mode="lines",
                name="leg 2",
                line=dict(color="black"),
            )
        )

    fig.update_layout(
        title=f"Separatrix t={int(sep_data.get('requested_time_ms', 0))} ms",
        xaxis_title="R [м]",
        yaxis_title="Z [м]",
        width=width,
        height=height,
        autosize=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=60, r=20, t=60, b=40),
        uirevision="fixed_axes_do_not_change",
        showlegend=False,
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="#e6e6e6",
        range=x_range,
        autorange=False,
        fixedrange=True,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#e6e6e6",
        range=y_range,
        autorange=False,
        fixedrange=True,
    )

    config = {
        "staticPlot": not interactive,
        "responsive": False,
        "displayModeBar": bool(interactive),
    }

    return fig.to_html(full_html=False, include_plotlyjs="cdn", config=config)
