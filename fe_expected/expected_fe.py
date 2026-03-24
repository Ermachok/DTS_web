from typing import List, Tuple, Dict
import bisect
import math
import json

H_PLANCK = 6.62607015e-34  # J s
C_LIGHT = 299_792_458  # m / s
E_CHARGE = 1.602176634e-19  # C

# Default detector amplification
DEFAULT_GAIN = 100


def read_avalanche_amper(file_path: str) -> Tuple[List[float], List[float]]:
    """
    Read avalanche datasheet containing wavelength and amplitude (current/amplitude).
    The file is expected to contain two comma-separated columns: wavelength (nm), amplitude (unit).
    Lines that cannot be parsed to two floats are skipped.

    Returns:
        (wavelengths_nm, amplitudes)
    """
    wavelengths: List[float] = []
    amplitudes: List[float] = []

    with open(file_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 2:
                continue
            try:
                wl = float(parts[0])
                amp = float(parts[1])
            except ValueError:
                # skip header or malformed lines
                continue
            wavelengths.append(wl)
            amplitudes.append(amp)

    return wavelengths, amplitudes


def read_avalanche_and_compute_phe(
    file_path: str,
    gain: float = DEFAULT_GAIN,
    h_planck: float = H_PLANCK,
    c_light: float = C_LIGHT,
    e_charge: float = E_CHARGE,
) -> Tuple[List[float], List[float]]:
    """
    Read avalanche datasheet and compute quantum yield in phe per photon (without amplification).

    The conversion factor applied is:
        phe = amplitude * (h * c * 1e9) / (e_charge * gain) / wavelength_nm

    Arguments:
        file_path: CSV with columns wavelength_nm, amplitude
        gain: amplification factor used in measurement (default DEFAULT_GAIN)
        h_planck, c_light, e_charge: physical constants (override for testing)

    Returns:
        (wavelengths_nm, phe_per_photon)
    """
    wavelengths, amplitudes = read_avalanche_amper(file_path)
    coef = (
        h_planck * c_light * 1e9 / (e_charge * gain)
    )  # 1e9 to convert m->nm factor used in formula
    phe = [amp * coef / wl for amp, wl in zip(amplitudes, wavelengths)]
    return wavelengths, phe


def read_filters_file(
    file_path: str, transpose: bool = False
) -> Tuple[List[float], List[List[float]]]:
    """
    Read filters CSV file. Expected format: each row starts with wavelength (nm) then one or more
    transmission columns (comma separated). Non-parsable lines are skipped.

    If transpose is False (default) returns:
        wavelengths_nm, [ [t1_row1, t2_row1, ...], [t1_row2, t2_row2, ...], ... ]
    If transpose is True returns:
        wavelengths_nm, [ [filter1_transmissions_over_wl], [filter2_transmissions_over_wl], ... ]
    """
    wavelengths: List[float] = []
    transmissions_rows: List[List[float]] = []

    with open(file_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",") if p.strip() != ""]
            if len(parts) < 2:
                continue
            try:
                wl = float(parts[0])
                trans = [float(x) for x in parts[1:]]
            except ValueError:
                # skip header / malformed rows
                continue
            wavelengths.append(wl)
            transmissions_rows.append(trans)

    if not transpose:
        return wavelengths, transmissions_rows

    # transpose rows -> list per filter
    if not transmissions_rows:
        return wavelengths, []

    n_filters = len(transmissions_rows[0])
    transposed: List[List[float]] = [[] for _ in range(n_filters)]
    for row in transmissions_rows:
        # if some rows are shorter, pad them with zeros
        for i in range(n_filters):
            value = row[i] if i < len(row) else 0.0
            transposed[i].append(value)

    return wavelengths, transposed


def linear_interpolate(x: float, xs: List[float], ys: List[float]) -> float:
    """
    Linear interpolation of (xs, ys) at point x.
    If x is out of bounds, return nearest endpoint value.
    xs must be sorted in ascending order.
    """
    if not xs or not ys:
        raise ValueError("Coordinate and value arrays must be non-empty.")
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]

    idx = bisect.bisect_left(xs, x)
    if idx == 0:
        return ys[0]
    if idx >= len(xs):
        return ys[-1]

    x0, x1 = xs[idx - 1], xs[idx]
    y0, y1 = ys[idx - 1], ys[idx]
    if x1 == x0:
        return y0
    alpha = (x - x0) / (x1 - x0)
    return y0 + alpha * (y1 - y0)


def spectral_density_selden(
    temperature_k: float,
    wl_grid_nm: List[float],
    theta_deg: float,
    lambda_0_nm: float,
) -> List[float]:
    """
    Compute spectral density using Selden-like formula (original logic preserved).
    temperature_k: electron temperature in K
    wl_grid_nm: list of wavelengths in nm
    theta_deg: scattering angle in degrees
    lambda_0_nm: reference wavelength in nm

    Returns list of spectral densities (same length as wl_grid_nm).
    """
    m_e = 9.10938356e-31
    c = C_LIGHT
    q_e = E_CHARGE

    alpha_T = m_e * c * c / (2 * q_e)
    theta = math.radians(theta_deg)
    alpha = alpha_T / temperature_k

    densities: List[float] = []
    for wl_nm in wl_grid_nm:
        x = (wl_nm / lambda_0_nm) - 1.0
        a_loc = (1 + x) ** 3 * math.sqrt(2 * (1 - math.cos(theta)) * (1 + x) + x * x)
        b_loc = math.sqrt(1 + (x * x) / (2 * (1 - math.cos(theta)) * (1 + x))) - 1
        c_loc = math.sqrt(alpha / math.pi) * (
            1 - (15 / (16 * alpha)) + 345 / (512 * alpha * alpha)
        )
        # divide by lambda_0 (in meters) because wl_grid is in nm; lambda_0_nm -> m factor is 1e-9
        densities.append(
            (c_loc / a_loc) * math.exp(-2 * alpha * b_loc) / (lambda_0_nm * 1e-9)
        )

    return densities


def get_expected_fe(
    avalanche_path: str,
    filters_path: str,
    *,
    wl_start_nm: float = 800.0,
    wl_step_nm: float = 0.2,
    wl_steps: int = 1315,
    te_start: float = 1.0,
    te_step: float = 0.2,
    te_steps: int = 2000,
    theta_deg: float = 110.0,
    lambda_0_nm: float = 1064.4,
) -> Dict:
    """
    Compute filter-integrated responses for a grid of electron temperatures.

    Returns a dictionary containing:
      - 'wl_grid': list of wavelengths (nm)
      - 'te_grid': list of temperatures (K)
      - for each temperature value (float) : list of integrals (one per filter)

    The returned dict uses float keys for temperatures to preserve the original behavior.
    """
    avalanche_wl, avalanche_amp = read_avalanche_amper(avalanche_path)
    filters_wl, filters_per_filter = read_filters_file(filters_path, transpose=True)

    # Prepare grids
    wl_grid = [wl_start_nm + i * wl_step_nm for i in range(wl_steps)]
    te_grid = [te_start + i * te_step for i in range(te_steps)]

    # Interpolate detector (avalanche) amplitude to wl_grid
    detector_interp = [
        linear_interpolate(wl, avalanche_wl, avalanche_amp) for wl in wl_grid
    ]

    # Interpolate filters
    filters_interp: List[List[float]] = []
    for fl in filters_per_filter:
        filters_interp.append(
            [linear_interpolate(wl, filters_wl, fl) for wl in wl_grid]
        )

    # Precompute spectral densities per temperature lazily inside loop
    result: Dict = {"wl_grid": wl_grid, "te_grid": te_grid}

    # integration factor will include division by wavelength (m) inside loop and multiply by wl_step_m at the end
    wl_step_m = wl_step_nm * 1e-9

    for t in te_grid:
        section = spectral_density_selden(t, wl_grid, theta_deg, lambda_0_nm)
        filter_integrals: List[float] = []
        for filter_trans in filters_interp:
            # since wl_grid is in nm, convert wl to meters inside loop
            integral = 0.0
            for wavelength_nm, section_val, detector_value, filter_value in zip(
                wl_grid, section, detector_interp, filter_trans
            ):
                wavelength_m = wavelength_nm * 1e-9
                integral += section_val * filter_value * detector_value / wavelength_m
            filter_integrals.append(integral * wl_step_m)
        result[t] = filter_integrals

    return result


if __name__ == "__main__":
    filters_path = (
        r"C:\Users\user\PycharmProjects\DTS_web\datasheets\filters_equator.csv"
    )
    avalanche_path = r"C:\Users\user\PycharmProjects\DTS_web\datasheets\aw_hama.csv"

    fe_expected = get_expected_fe(
        filters_path=filters_path, avalanche_path=avalanche_path
    )

    # channels = {
    #     f"ch_{ch + 1}": [values[ch] for key, values in fe_expected.items() if key not in {'wl_grid', 'te_grid'}]
    #     for ch in range(3)
    # }
    #
    # ch1_to_ch2, ch2_to_ch3 = [], []
    #
    # for ch1, ch2, ch3 in zip(channels["ch_1"], channels["ch_2"], channels["ch_3"]):
    #     ch1_to_ch2.append(ch1 / ch2 if ch2 != 0 else 0.0)
    #     ch2_to_ch3.append(ch2 / ch3 if ch3 != 0 else 0.0)
    #
    # output_data = {
    #     "Temperature (eV)": [round(t, 1) for t in fe_expected["te_grid"]],
    #     "Channel 1": channels["ch_1"],
    #     "Channel 2": channels["ch_2"],
    #     "Channel 3": channels["ch_3"],
    #     "Ch1/Ch2": ch1_to_ch2,
    #     "Ch2/Ch3": ch2_to_ch3,
    # }
    #
    with open("fe_expected_90deg.json", "w", encoding="utf-8") as f:
        json.dump(fe_expected, f, indent=4)
