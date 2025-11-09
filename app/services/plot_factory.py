import plotly.graph_objects as go
import numpy as np


def make_interactive_plots(fibers, combiscope_times):
    """
    Построение 4 интерактивных графиков:
      1. Te(t)
      2. ne(t)
      3. Te(z) — профиль по Z для разных моментов времени
      4. ne(z) — профиль по Z для разных моментов времени
    Возвращает список HTML-дивов для вставки в шаблон.
    """

    combiscope_times = np.array(combiscope_times, dtype=float)
    mask = (combiscope_times >= 140) & (combiscope_times <= 210)
    combiscope_times = combiscope_times[mask]
    if len(combiscope_times) == 0:
        return ["<p>Нет данных в диапазоне 140–210 мс</p>"]

    # 1. Te(t)
    fig_T_t = go.Figure()
    for fiber in fibers:
        if not fiber.temperatures:
            continue
        n_shots = min(len(combiscope_times), len(fiber.temperatures))
        fig_T_t.add_trace(go.Scatter(
            x=combiscope_times[:n_shots],
            y=[float(t) for t in fiber.temperatures[:n_shots]],
            error_y=dict(type='data', array=[float(e) for e in fiber.errors_T[:n_shots]], visible=True),
            mode="markers+lines",
            name=f"F{fiber.fiber_number} (z={fiber.z_cm:.1f}см)"
        ))
    fig_T_t.update_layout(
        title="Tₑ(t)",
        xaxis_title="t (ms)",
        yaxis_title="Tₑ (eV)",
        yaxis=dict(range=[0, None]),  # от 0
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(size=9)),
        height=550,
        margin=dict(l=60, r=40, t=70, b=80)
    )

    # 2. ne(t)
    fig_n_t = go.Figure()
    for fiber in fibers:
        if not fiber.density:
            continue
        n_shots = min(len(combiscope_times), len(fiber.density))
        fig_n_t.add_trace(go.Scatter(
            x=combiscope_times[:n_shots],
            y=[float(n) for n in fiber.density[:n_shots]],
            error_y=dict(type='data', array=[float(e) for e in fiber.errors_n[:n_shots]], visible=True),
            mode="markers+lines",
            name=f"F{fiber.fiber_number} (z={fiber.z_cm:.1f}см)"
        ))
    fig_n_t.update_layout(
        title="nₑ(t)",
        xaxis_title="t (ms)",
        yaxis_title="nₑ (m⁻³)",
        yaxis=dict(range=[0, None]),
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(size=9)),
        height=550,
        margin=dict(l=60, r=40, t=70, b=80)
    )

    # 3. Te(z)
    fig_T_z = go.Figure()
    n_points = min(len(fiber.temperatures) for fiber in fibers if fiber.temperatures)
    for i in range(n_points):
        if i >= len(combiscope_times):
            break
        z_vals, t_vals, err_vals = [], [], []
        for fiber in fibers:
            if len(fiber.temperatures) > i:
                z_vals.append(fiber.z_cm)
                t_vals.append(float(fiber.temperatures[i]))
                err_vals.append(float(fiber.errors_T[i]) if fiber.errors_T else 0.0)
        fig_T_z.add_trace(go.Scatter(
            x=z_vals,
            y=t_vals,
            error_y=dict(type='data', array=err_vals, visible=True),
            mode="lines+markers",
            name=f"{combiscope_times[i]:.1f} мс"
        ))
    fig_T_z.update_layout(
        title="Tₑ(Z)",
        xaxis_title="Z (cm)",
        yaxis_title="Tₑ (eV)",
        yaxis=dict(range=[0, None]),
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(size=9)),
        height=650,
        margin=dict(l=60, r=40, t=70, b=80)
    )

    # 4. ne(z)
    fig_n_z = go.Figure()
    n_points = min(len(fiber.density) for fiber in fibers if fiber.density)
    for i in range(n_points):
        if i >= len(combiscope_times):
            break
        z_vals, n_vals, err_vals = [], [], []
        for fiber in fibers:
            if len(fiber.density) > i:
                z_vals.append(fiber.z_cm)
                n_vals.append(float(fiber.density[i]))
                err_vals.append(float(fiber.errors_n[i]) if fiber.errors_n else 0.0)
        fig_n_z.add_trace(go.Scatter(
            x=z_vals,
            y=n_vals,
            error_y=dict(type='data', array=err_vals, visible=True),
            mode="lines+markers",
            name=f"{combiscope_times[i]:.1f} мс"
        ))
    fig_n_z.update_layout(
        title="nₑ(Z)",
        xaxis_title="Z (cm)",
        yaxis_title="nₑ (m⁻³)",
        yaxis=dict(range=[0, None]),
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(size=9)),
        height=650,
        margin=dict(l=60, r=40, t=70, b=80)
    )

    return [
        fig_T_t.to_html(full_html=False, include_plotlyjs='cdn'),
        fig_n_t.to_html(full_html=False, include_plotlyjs=False),
        fig_T_z.to_html(full_html=False, include_plotlyjs=False),
        fig_n_z.to_html(full_html=False, include_plotlyjs=False),
    ]
