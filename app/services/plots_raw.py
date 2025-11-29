import plotly.graph_objects as go


def make_raw_signals_plot(polychromator, channel: int, from_shot: int, to_shot, combiscope_times):
    """
    Строит сырые сигналы выбранного полихроматора и канала.
    """
    signals = polychromator.signals
    times = polychromator.signals_time
    if channel >= len(signals):
        return f"<p>Канал {channel} не найден в полихроматоре {polychromator.poly_name}</p>"

    n_shots = len(signals[channel])

    if isinstance(to_shot, str) and to_shot.lower() == "all":
        to_shot = n_shots
    else:
        try:
            to_shot = min(int(to_shot), n_shots)
        except ValueError:
            return f"<p>Некорректное значение До шота: {to_shot}</p>"

    from_shot = max(int(from_shot), 0)
    if from_shot >= to_shot:
        return f"<p>Некорректный диапазон шотов: {from_shot}–{to_shot}</p>"

    fig = go.Figure()

    for shot in range(from_shot, to_shot):
        if shot >= len(signals[channel]):
            break
        signal = signals[channel][shot]
        fig.add_trace(go.Scatter(
            x=times[shot][:len(signal)],
            y=signal,
            mode="lines",
            #name=f"Shot {shot}",
            name=f"Shot {combiscope_times[shot]:.1f} ms",
        ))

    fig.update_layout(
        title=f"Сырые сигналы — {polychromator.poly_name}, канал {channel}",
        xaxis_title="Time (ns)",
        yaxis_title="Volts (mV)",
        template="plotly_white",
        height=700,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=9),
        )
    )
    fig.update_layout(xaxis_range=[20, 70])

    return fig.to_html(full_html=False, include_plotlyjs='cdn')
