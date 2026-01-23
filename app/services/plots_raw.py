import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.colors import qualitative

try:
    DEFAULT_COLORS = qualitative.Plotly
except Exception:
    DEFAULT_COLORS = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ]


def make_raw_signals_plot(polychromator, channels=None, from_shot: int = 0, to_shot=None, combiscope_times=None):
    """
    Строит сырые сигналы выбранного полихроматора для списка каналов.
    Рисует каналы вертикально (один над другим) с общей интерактивной легендой,
    где элементы легенды — времена выстрелов (combiscope_times).

    Изменения:
    - Все трассы одного шота (всех каналов) рисуются одним цветом.
    - Подпись X-оси видна только у нижнего сабплота и подтянута вверх (меньший отступ).
    - Немного опущена легенда и увеличен нижний отступ, чтобы легенда не наезжала на подпись оси X.
    """
    signals = polychromator.signals
    times = polychromator.signals_time

    if combiscope_times is not None:
        try:
            if len(combiscope_times) == 0 or combiscope_times[0] != 0.0:
                combiscope_times.insert(0, 0.0)
        except Exception:
            pass

    if channels is None:
        channels = [0, 1]

    if isinstance(channels, int):
        channels = [channels]


    valid_channels = []
    for ch in channels:
        if isinstance(ch, int) and 0 <= ch < len(signals):
            valid_channels.append(int(ch))
    if not valid_channels:
        return f"<p>Ни один из каналов {channels} не найден в полихроматоре {polychromator.poly_name}</p>"


    n_shots = len(signals[valid_channels[0]])

    if isinstance(to_shot, str) and to_shot.lower() == "all":
        to_shot = n_shots
    else:
        try:
            to_shot = min(int(to_shot) if to_shot is not None else n_shots, n_shots)
        except (ValueError, TypeError):
            return f"<p>Некорректное значение До шота: {to_shot}</p>"

    from_shot = max(int(from_shot), 0)
    if from_shot >= to_shot:
        return f"<p>Некорректный диапазон шотов: {from_shot}–{to_shot}</p>"

    n_rows = len(valid_channels)
    fig = make_subplots(rows=n_rows, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        subplot_titles=[f"Канал {ch}" for ch in valid_channels])

    colors = DEFAULT_COLORS
    n_colors = len(colors)
    for shot in range(from_shot, to_shot):
        shot_label = (f"Shot {combiscope_times[shot]:.1f} ms"
                      if combiscope_times is not None and shot < len(combiscope_times)
                      else f"Shot {shot}")
        legend_group = f"shot{shot}"
        color = colors[(shot - from_shot) % n_colors]

        for idx, ch in enumerate(valid_channels):
            if shot >= len(signals[ch]):
                continue
            signal = signals[ch][shot]
            x = times[shot][:len(signal)]

            fig.add_trace(go.Scatter(
                x=x,
                y=signal,
                mode="lines",
                name=shot_label,
                legendgroup=legend_group,
                showlegend=(idx == 0),
                line=dict(color=color, width=1.6),
                hovertemplate=(
                    "Time: %{x} ns<br>"
                    "Voltage: %{y} mV<br>"
                    f"Shot: {shot_label}<br>"
                    f"Channel: {ch}"
                ),
            ), row=idx + 1, col=1)

            fig.update_yaxes(title_text="Volts (mV)", row=idx + 1, col=1)

    try:
        fig.update_xaxes(title_text="", row=1, col=1)
        fig.update_xaxes(title_text="Time (ns)", row=n_rows, col=1, title_standoff=6)
    except Exception:
        pass

    fig.update_layout(
        title=f"Сырые сигналы — {polychromator.poly_name} (каналы: {', '.join(map(str, valid_channels))})",
        template="plotly_white",
        height=380 * n_rows,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.18,  #
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        margin=dict(b=90)
    )
    try:
        fig.update_xaxes(range=[20, 70])
    except Exception:
        pass

    return fig.to_html(full_html=False, include_plotlyjs='cdn')
