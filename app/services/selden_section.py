import math


def spect_dens_selden(
    temperature: float, wl_grid: list, theta_deg: float, lambda_0: float
) -> list:
    # деление на lambda_0 - нормировка интеграла при переходе к нужной длине волны

    m_e = 9.1e-31
    c_light = 3e8
    q_elec = 1.6e-19

    alphaT = m_e * c_light * c_light / (2 * q_elec)
    theta = theta_deg * math.pi / 180.0
    alpha = alphaT / temperature
    section = []
    for wl in wl_grid:
        x = (wl / lambda_0) - 1
        a_loc = math.pow(1 + x, 3) * math.sqrt(
            2 * (1 - math.cos(theta)) * (1 + x) + math.pow(x, 2)
        )
        b_loc = math.sqrt(1 + x * x / (2 * (1 - math.cos(theta)) * (1 + x))) - 1
        c_loc = math.sqrt(alpha / math.pi) * (
            1 - (15 / (16 * alpha)) + 345 / (512 * alpha * alpha)
        )
        section.append(
            (c_loc / a_loc) * math.exp(-2 * alpha * b_loc) / (lambda_0 * 1e-9)
        )  # to meters
    return section
