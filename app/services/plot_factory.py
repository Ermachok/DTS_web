import plotly.graph_objects as go
import numpy as np
from plotly.colors import qualitative as pcolors


def make_interactive_plots(fibers, combiscope_times):
    """
    Построение 4 интерактивных графиков:
      1. Te(t)
      2. ne(t)
      3. Te(z) — профиль по Z для разных моментов времени
      4. ne(z) — профиль по Z для разных моментов времени

    Изменения:
    - Для временных графиков (Te(t), ne(t)) в легенде используется только позиция Z (пример: "38.6 cm").
    - Для профилей (Te(z), ne(z)) легенда остаётся по времени.
    - Уменьшены отступы и станд‑оффы, legend располагается под графиком (несколько строк при необходимости).
    - "high error" трейсы принадлежат той же legendgroup и по умолчанию скрыты (visible=False), не создают отдельной записи в легенде.
    - Нижняя часть погрешности (arrayminus) обрезается, чтобы y - err_down >= 0.
    """

    PALETTE = pcolors.Plotly

    # Преобразуем входные времена в массив и запомним оригинальные индексы,
    # которые попадают в желаемый диапазон.
    combiscope_times_arr = np.array(combiscope_times, dtype=float)
    mask = (combiscope_times_arr >= 150) & (combiscope_times_arr <= 220)
    selected_idxs = np.where(mask)[0].tolist()
    combiscope_times = combiscope_times_arr[mask]

    if len(combiscope_times) == 0:
        return ["<p>Нет данных в диапазоне 150–220 мс</p>"]

    # Легенда под графиком, центрированная; Plotly сам переносит элементы на 2-3 строки при нехватке места
    LEGEND_CONFIG_HOR = dict(
        orientation="h",
        x=0.5,
        xanchor="center",
        y=-0.18,  # ближе к графику, чтобы уменьшить зазор
        yanchor="top",
        font=dict(size=10),
        tracegroupgap=0
    )

    BAD_MARKER_SYMBOL = 'x'
    BAD_MARKER_SIZE = 10
    BAD_MARKER_LINE_WIDTH = 2

    # -------------------------------------------------------
    # 1. Te(t) — временные серии, легенда показывает только Z
    fig_T_t = go.Figure()
    for f_idx, fiber in enumerate(fibers):
        temps = getattr(fiber, "temperatures", None)
        if not temps:
            continue

        color = PALETTE[f_idx % len(PALETTE)]
        # короткая подпись для легенды: только позиция Z
        base_name = f"{fiber.z_cm:.1f} cm"
        legend_group = base_name

        x_good, y_good, err_up_good, err_down_good = [], [], [], []
        x_bad, y_bad, err_up_bad, err_down_bad = [], [], [], []

        for idx, t_time in zip(selected_idxs, combiscope_times):
            if idx < len(temps):
                try:
                    t_val = float(temps[idx])
                except Exception:
                    continue
                errors_T = getattr(fiber, "errors_T", None) or []
                raw_err = abs(float(errors_T[idx])) if idx < len(errors_T) else 0.0
                err_up = raw_err
                err_down = min(raw_err, t_val)
                is_large = (t_val == 0 and raw_err > 0) or (raw_err > t_val)
                if is_large:
                    x_bad.append(t_time)
                    y_bad.append(t_val)
                    err_up_bad.append(err_up)
                    err_down_bad.append(err_down)
                else:
                    x_good.append(t_time)
                    y_good.append(t_val)
                    err_up_good.append(err_up)
                    err_down_good.append(err_down)

        if x_good:
            fig_T_t.add_trace(go.Scatter(
                x=x_good,
                y=y_good,
                error_y=dict(type='data', array=err_up_good, arrayminus=err_down_good, visible=True),
                mode="markers+lines",
                line=dict(color=color, dash='solid'),
                marker=dict(symbol='circle', size=6, color=color),
                name=base_name,
                legendgroup=legend_group,
                showlegend=True,
                visible=True
            ))
            if x_bad:
                # bad — тот же цвет, но скрыты по умолчанию и не в легенде
                fig_T_t.add_trace(go.Scatter(
                    x=x_bad,
                    y=y_bad,
                    error_y=dict(type='data', array=err_up_bad, arrayminus=err_down_bad, visible=True),
                    mode="markers+lines",
                    line=dict(color=color, dash='dash'),
                    marker=dict(symbol=BAD_MARKER_SYMBOL, size=BAD_MARKER_SIZE, line=dict(width=BAD_MARKER_LINE_WIDTH),
                                color=color),
                    name=base_name,
                    legendgroup=legend_group,
                    showlegend=False,
                    visible=False
                ))
        else:
            # нет "хороших" точек — показываем "bad" как основную запись в легенде,
            # но по умолчанию скрытой (visible=False), чтобы легенда присутствовала
            if x_bad:
                fig_T_t.add_trace(go.Scatter(
                    x=x_bad,
                    y=y_bad,
                    error_y=dict(type='data', array=err_up_bad, arrayminus=err_down_bad, visible=True),
                    mode="markers+lines",
                    line=dict(color=color, dash='dash'),
                    marker=dict(symbol=BAD_MARKER_SYMBOL, size=BAD_MARKER_SIZE, line=dict(width=BAD_MARKER_LINE_WIDTH),
                                color=color),
                    name=base_name,
                    legendgroup=legend_group,
                    showlegend=True,
                    visible=False
                ))

    fig_T_t.update_layout(
        title="Tₑ(t)",
        xaxis_title="t (ms)",
        xaxis=dict(automargin=True, title_standoff=8),
        yaxis_title="Tₑ (eV)",
        yaxis=dict(range=[0, None], automargin=True),
        template="plotly_white",
        legend=LEGEND_CONFIG_HOR,
        height=550,
        margin=dict(l=60, r=20, t=70, b=120)  # нижний отступ уменьшён относительно предыдущей версии
    )

    # -------------------------------------------------------
    # 2. ne(t) — временные серии, легенда показывает только Z
    fig_n_t = go.Figure()
    for f_idx, fiber in enumerate(fibers):
        dens = getattr(fiber, "density", None)
        if not dens:
            continue

        color = PALETTE[f_idx % len(PALETTE)]
        base_name = f"{fiber.z_cm:.1f} cm"
        legend_group = base_name

        x_good, y_good, err_up_good, err_down_good = [], [], [], []
        x_bad, y_bad, err_up_bad, err_down_bad = [], [], [], []

        for idx, t_time in zip(selected_idxs, combiscope_times):
            if idx < len(dens):
                try:
                    n_val = float(dens[idx])
                except Exception:
                    continue
                errors_n = getattr(fiber, "errors_n", None) or []
                raw_err = abs(float(errors_n[idx])) if idx < len(errors_n) else 0.0
                err_up = raw_err
                err_down = min(raw_err, n_val)
                is_large = (n_val == 0 and raw_err > 0) or (raw_err > n_val)
                if is_large:
                    x_bad.append(t_time)
                    y_bad.append(n_val)
                    err_up_bad.append(err_up)
                    err_down_bad.append(err_down)
                else:
                    x_good.append(t_time)
                    y_good.append(n_val)
                    err_up_good.append(err_up)
                    err_down_good.append(err_down)

        if x_good:
            fig_n_t.add_trace(go.Scatter(
                x=x_good,
                y=y_good,
                error_y=dict(type='data', array=err_up_good, arrayminus=err_down_good, visible=True),
                mode="markers+lines",
                line=dict(color=color, dash='solid'),
                marker=dict(symbol='circle', size=6, color=color),
                name=base_name,
                legendgroup=legend_group,
                showlegend=True,
                visible=True
            ))
            if x_bad:
                fig_n_t.add_trace(go.Scatter(
                    x=x_bad,
                    y=y_bad,
                    error_y=dict(type='data', array=err_up_bad, arrayminus=err_down_bad, visible=True),
                    mode="markers+lines",
                    line=dict(color=color, dash='dash'),
                    marker=dict(symbol=BAD_MARKER_SYMBOL, size=BAD_MARKER_SIZE, line=dict(width=BAD_MARKER_LINE_WIDTH),
                                color=color),
                    name=base_name,
                    legendgroup=legend_group,
                    showlegend=False,
                    visible=False
                ))
        else:
            if x_bad:
                fig_n_t.add_trace(go.Scatter(
                    x=x_bad,
                    y=y_bad,
                    error_y=dict(type='data', array=err_up_bad, arrayminus=err_down_bad, visible=True),
                    mode="markers+lines",
                    line=dict(color=color, dash='dash'),
                    marker=dict(symbol=BAD_MARKER_SYMBOL, size=BAD_MARKER_SIZE, line=dict(width=BAD_MARKER_LINE_WIDTH),
                                color=color),
                    name=base_name,
                    legendgroup=legend_group,
                    showlegend=True,
                    visible=False
                ))

    fig_n_t.update_layout(
        title="nₑ(t)",
        xaxis_title="t (ms)",
        xaxis=dict(automargin=True, title_standoff=8),
        yaxis_title="nₑ (m⁻³)",
        yaxis=dict(rangemode='tozero', automargin=True),
        template="plotly_white",
        legend=LEGEND_CONFIG_HOR,
        height=550,
        margin=dict(l=60, r=20, t=70, b=120)
    )

    # -------------------------------------------------------
    # 3. Te(z) — профиль по Z, легенда по временам (оставляем как было)
    fig_T_z = go.Figure()
    for time_idx, (idx, time_val) in enumerate(zip(selected_idxs, combiscope_times)):
        color = PALETTE[time_idx % len(PALETTE)]
        time_name = f"{time_val:.1f} ms"
        legend_group = time_name

        z_good, t_good, err_up_good, err_down_good = [], [], [], []
        z_bad, t_bad, err_up_bad, err_down_bad = [], [], [], []

        for fiber in fibers:
            temps = getattr(fiber, "temperatures", None)
            if temps and idx < len(temps):
                try:
                    t_val = float(temps[idx])
                except Exception:
                    continue
                errors_T = getattr(fiber, "errors_T", None) or []
                raw_err = abs(float(errors_T[idx])) if idx < len(errors_T) else 0.0
                err_up = raw_err
                err_down = min(raw_err, t_val)
                is_large = (t_val == 0 and raw_err > 0) or (raw_err > t_val)
                if is_large:
                    z_bad.append(fiber.z_cm)
                    t_bad.append(t_val)
                    err_up_bad.append(err_up)
                    err_down_bad.append(err_down)
                else:
                    z_good.append(fiber.z_cm)
                    t_good.append(t_val)
                    err_up_good.append(err_up)
                    err_down_good.append(err_down)

        if z_good:
            fig_T_z.add_trace(go.Scatter(
                x=z_good,
                y=t_good,
                error_y=dict(type='data', array=err_up_good, arrayminus=err_down_good, visible=True),
                mode="lines+markers",
                line=dict(color=color, dash='solid'),
                marker=dict(symbol='circle', size=6, color=color),
                name=time_name,
                legendgroup=legend_group,
                showlegend=True,
                visible=True
            ))
            if z_bad:
                fig_T_z.add_trace(go.Scatter(
                    x=z_bad,
                    y=t_bad,
                    error_y=dict(type='data', array=err_up_bad, arrayminus=err_down_bad, visible=True),
                    mode="lines+markers",
                    line=dict(color=color, dash='dash'),
                    marker=dict(symbol=BAD_MARKER_SYMBOL, size=BAD_MARKER_SIZE, line=dict(width=BAD_MARKER_LINE_WIDTH),
                                color=color),
                    name=time_name,
                    legendgroup=legend_group,
                    showlegend=False,
                    visible=False
                ))
        else:
            if z_bad:
                fig_T_z.add_trace(go.Scatter(
                    x=z_bad,
                    y=t_bad,
                    error_y=dict(type='data', array=err_up_bad, arrayminus=err_down_bad, visible=True),
                    mode="lines+markers",
                    line=dict(color=color, dash='dash'),
                    marker=dict(symbol=BAD_MARKER_SYMBOL, size=BAD_MARKER_SIZE, line=dict(width=BAD_MARKER_LINE_WIDTH),
                                color=color),
                    name=time_name,
                    legendgroup=legend_group,
                    showlegend=True,
                    visible=False
                ))

    fig_T_z.update_layout(
        title="Tₑ(Z)",
        xaxis_title="Z (cm)",
        xaxis=dict(automargin=True, title_standoff=6),
        yaxis_title="Tₑ (eV)",
        yaxis=dict(range=[0, None], automargin=True),
        template="plotly_white",
        legend=LEGEND_CONFIG_HOR,
        height=650,
        margin=dict(l=60, r=20, t=70, b=120)
    )

    # -------------------------------------------------------
    # 4. ne(z)
    fig_n_z = go.Figure()
    for time_idx, (idx, time_val) in enumerate(zip(selected_idxs, combiscope_times)):
        color = PALETTE[time_idx % len(PALETTE)]
        time_name = f"{time_val:.1f} ms"
        legend_group = time_name

        z_good, n_good, err_up_good, err_down_good = [], [], [], []
        z_bad, n_bad, err_up_bad, err_down_bad = [], [], [], []

        for fiber in fibers:
            dens = getattr(fiber, "density", None)
            if dens and idx < len(dens):
                try:
                    n_val = float(dens[idx])
                except Exception:
                    continue
                errors_n = getattr(fiber, "errors_n", None) or []
                raw_err = abs(float(errors_n[idx])) if idx < len(errors_n) else 0.0
                err_up = raw_err
                err_down = min(raw_err, n_val)
                is_large = (n_val == 0 and raw_err > 0) or (raw_err > n_val)
                if is_large:
                    z_bad.append(fiber.z_cm)
                    n_bad.append(n_val)
                    err_up_bad.append(err_up)
                    err_down_bad.append(err_down)
                else:
                    z_good.append(fiber.z_cm)
                    n_good.append(n_val)
                    err_up_good.append(err_up)
                    err_down_good.append(err_down)

        if z_good:
            fig_n_z.add_trace(go.Scatter(
                x=z_good,
                y=n_good,
                error_y=dict(type='data', array=err_up_good, arrayminus=err_down_good, visible=True),
                mode="lines+markers",
                line=dict(color=color, dash='solid'),
                marker=dict(symbol='circle', size=6, color=color),
                name=time_name,
                legendgroup=legend_group,
                showlegend=True,
                visible=True
            ))
            if z_bad:
                fig_n_z.add_trace(go.Scatter(
                    x=z_bad,
                    y=n_bad,
                    error_y=dict(type='data', array=err_up_bad, arrayminus=err_down_bad, visible=True),
                    mode="lines+markers",
                    line=dict(color=color, dash='dash'),
                    marker=dict(symbol=BAD_MARKER_SYMBOL, size=BAD_MARKER_SIZE, line=dict(width=BAD_MARKER_LINE_WIDTH),
                                color=color),
                    name=time_name,
                    legendgroup=legend_group,
                    showlegend=False,
                    visible=False
                ))
        else:
            if z_bad:
                fig_n_z.add_trace(go.Scatter(
                    x=z_bad,
                    y=n_bad,
                    error_y=dict(type='data', array=err_up_bad, arrayminus=err_down_bad, visible=True),
                    mode="lines+markers",
                    line=dict(color=color, dash='dash'),
                    marker=dict(symbol=BAD_MARKER_SYMBOL, size=BAD_MARKER_SIZE, line=dict(width=BAD_MARKER_LINE_WIDTH),
                                color=color),
                    name=time_name,
                    legendgroup=legend_group,
                    showlegend=True,
                    visible=False
                ))

    fig_n_z.update_layout(
        title="nₑ(Z)",
        xaxis_title="Z (cm)",
        xaxis=dict(automargin=True, title_standoff=6),
        yaxis_title="nₑ (m⁻³)",
        yaxis=dict(rangemode='tozero', automargin=True),
        template="plotly_white",
        legend=LEGEND_CONFIG_HOR,
        height=650,
        margin=dict(l=60, r=20, t=70, b=120)
    )

    return [
        fig_T_t.to_html(full_html=False, include_plotlyjs='cdn'),
        fig_n_t.to_html(full_html=False, include_plotlyjs=False),
        fig_T_z.to_html(full_html=False, include_plotlyjs=False),
        fig_n_z.to_html(full_html=False, include_plotlyjs=False),
    ]
