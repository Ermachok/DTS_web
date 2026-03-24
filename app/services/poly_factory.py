import bisect
import math
import os.path
import statistics
from pathlib import Path

import numpy as np

from app.services.diagnostic_utils import GainsEquator, LaserNdYag


class Polychromator:
    # Class-level constants
    EXCESS_NOISE_FACTOR = 3
    ELECTRON_RADIUS = 2.81e-15
    E_CHARGE = 1.6e-19
    DEFAULT_M = 100
    NOISE_LEN = 75
    T_STEP = 0.325

    def __init__(
            self,
            poly_name: int | str,
            fiber_number: int,
            z_cm: float,
            caen_time: list,
            caen_data: list,
            config_connection=None,
            gains: GainsEquator = None,
            laser: LaserNdYag = None,
            absolut_calib: Path | dict | float = None,
            spectral_calib: Path | dict = None,
            fe_expected: dict = None,
    ):
        self.poly_name = poly_name
        self.fiber_number = fiber_number
        self.z_cm = z_cm

        self.signals = caen_data
        self.signals_time = caen_time
        self.ch_number = 3
        self.gain = gains
        self.laser = laser

        self.signals_integrals = None
        self.signals_noise_integrals = None

        self.fe_data = fe_expected
        self.expected_data = None
        self.config = config_connection

        self.spectral_calibration = spectral_calib[: self.ch_number]
        self.absolut_calibration = absolut_calib

        self.temperatures = []
        self.density = []

        self.errors_T = []
        self.errors_n = []

        # internal caches for fast calculations
        self._fe_cache_ready = False
        self._te_grid_arr = None
        self._te_keys = None
        self._F = None
        self._spectral_arr = None
        self._te_index_map = None

    def _normalize_laser_energy(self):
        n_shots = len(self.signals_integrals) if self.signals_integrals is not None else 0

        E = self.laser.laser_energy

        if isinstance(E, (int, float)):
            return [float(E)] * n_shots

        if isinstance(E, (list, tuple)):
            if n_shots == 0:
                return list(E)
            if len(E) != n_shots:
                raise ValueError(
                    f"laser_energy length mismatch: got {len(E)}, expected {n_shots}"
                )
            return list(E)

        raise TypeError("laser_energy must be float or list[float]")

    def _prepare_fe_cache(self):
        if self._fe_cache_ready:
            return

        if self.fe_data is None:
            raise ValueError("fe_data is not provided")

        if "Te_grid" not in self.fe_data:
            raise KeyError("fe_data must contain 'Te_grid'")

        te_grid = np.asarray(self.fe_data["Te_grid"], dtype=float)
        te_keys = [str(t) for t in te_grid]

        spectral = np.asarray(self.spectral_calibration[: self.ch_number], dtype=float)

        F_rows = []
        for key in te_keys:
            if key not in self.fe_data:
                raise KeyError(f"Temperature key '{key}' not found in fe_data")
            row = np.asarray(self.fe_data[key][: self.ch_number], dtype=float) * spectral
            F_rows.append(row)

        F = np.asarray(F_rows, dtype=float)  # shape (nT, ch)

        self._te_grid_arr = te_grid
        self._te_keys = te_keys
        self._F = F
        self._spectral_arr = spectral
        self._te_index_map = {float(t): i for i, t in enumerate(te_grid)}
        self._fe_cache_ready = True

    def get_signal_integrals(
            self, shots_before_plasma: int = 4, shots_after: int = 17
    ) -> tuple[list, list]:
        all_const = self.gain.resulting_multiplier

        all_shots_signal = []
        all_shots_noise = []

        total_shots = shots_before_plasma + shots_after
        for shot in range(1, total_shots):
            all_ch_signal = []
            all_ch_noise = []

            for poly_ch in range(self.ch_number):
                signal_ind = [
                    bisect.bisect_left(
                        self.signals_time[shot], self.config[poly_ch]["sig_LeftBord"]
                    ),
                    bisect.bisect_right(
                        self.signals_time[shot], self.config[poly_ch]["sig_RightBord"]
                    ),
                ]

                signal_lvl = statistics.median(
                    self.signals[poly_ch][shot][: self.NOISE_LEN]
                )
                lvl_integral = signal_lvl * (
                        self.config[poly_ch]["sig_RightBord"]
                        - self.config[poly_ch]["sig_LeftBord"]
                )

                if poly_ch == 0:
                    summ_of_ideal_thomson_signal = 24
                    sig_maximum = max(
                        self.signals[poly_ch][shot][signal_ind[0]: signal_ind[1]]
                    )
                    signal_integral = (
                            (sig_maximum - signal_lvl)
                            * summ_of_ideal_thomson_signal
                            * self.T_STEP
                    )
                else:
                    signal_integral = (
                            sum(self.signals[poly_ch][shot][signal_ind[0]: signal_ind[1]])
                            * self.T_STEP
                            - lvl_integral
                    )

                phe_number = signal_integral * all_const

                noise_track_mV = [
                    1100 - 1250 + v * 2500 / 4096
                    for v in self.signals[poly_ch][shot][: self.NOISE_LEN]
                ]
                noise_track = (
                                      statistics.stdev(noise_track_mV)
                                      * all_const
                                      * self.T_STEP
                                      * (signal_ind[1] - signal_ind[0])
                              ) ** 2 + 0.01

                if phe_number > 0:
                    noise_excess = phe_number * self.EXCESS_NOISE_FACTOR
                else:
                    phe_number = 1
                    noise_excess = 0

                all_ch_signal.append(phe_number)
                all_ch_noise.append((noise_track + noise_excess) ** 0.5)

            all_shots_signal.append(all_ch_signal)
            all_shots_noise.append(all_ch_noise)

        return all_shots_signal, all_shots_noise

    def get_temperatures(self):
        self.signals_integrals, self.signals_noise_integrals = self.get_signal_integrals()
        self._prepare_fe_cache()

        y = np.asarray(self.signals_integrals, dtype=float)  # (nshots, ch)
        sigma = np.asarray(self.signals_noise_integrals, dtype=float)  # (nshots, ch)

        if y.ndim != 2 or sigma.ndim != 2:
            raise ValueError("signals_integrals and signals_noise_integrals must be 2D")

        if y.shape != sigma.shape:
            raise ValueError(
                f"Shape mismatch: signals_integrals {y.shape}, noise {sigma.shape}"
            )

        with np.errstate(divide="ignore", invalid="ignore"):
            w = np.divide(1.0, np.square(sigma), out=np.zeros_like(sigma), where=sigma > 0)

        # F: (nT, ch)
        # y[:, None, :] -> (nshots, 1, ch)
        # w[:, None, :] -> (nshots, 1, ch)
        # F[None, :, :] -> (1, nT, ch)
        F = self._F

        sum_1 = np.sum(y[:, None, :] * F[None, :, :] * w[:, None, :], axis=2)  # (nshots, nT)
        sum_2 = np.sum(np.square(F)[None, :, :] * w[:, None, :], axis=2)  # (nshots, nT)

        with np.errstate(divide="ignore", invalid="ignore"):
            A_hat = np.divide(sum_1, sum_2, out=np.zeros_like(sum_1), where=sum_2 > 0)

        residuals = y[:, None, :] - A_hat[:, :, None] * F[None, :, :]
        chi2 = np.sum(np.square(residuals) * w[:, None, :], axis=2)  # (nshots, nT)

        best_idx = np.argmin(chi2, axis=1)
        self.temperatures = [self._te_keys[i] for i in best_idx]

    def get_density(self):
        if not self.temperatures:
            self.get_temperatures()

        self._prepare_fe_cache()

        laser_energies = np.asarray(self._normalize_laser_energy(), dtype=float)
        y = np.asarray(self.signals_integrals, dtype=float)
        sigma = np.asarray(self.signals_noise_integrals, dtype=float)

        with np.errstate(divide="ignore", invalid="ignore"):
            w = np.divide(1.0, np.square(sigma), out=np.zeros_like(sigma), where=sigma > 0)

        te_idx = np.asarray(
            [self._te_index_map[float(T_e)] for T_e in self.temperatures],
            dtype=int,
        )

        F_sel = self._F[te_idx, :]  # (nshots, ch)

        sum_numerator = np.sum(y * F_sel * w, axis=1)
        sum_divider = np.sum(np.square(F_sel) * w, axis=1)

        denom = (
                sum_divider
                * laser_energies
                * (self.laser.laser_wl / (self.DEFAULT_M * self.E_CHARGE))
                * self.absolut_calibration
                * self.ELECTRON_RADIUS ** 2
        )

        with np.errstate(divide="ignore", invalid="ignore"):
            ne = np.divide(sum_numerator, denom, out=np.zeros_like(sum_numerator), where=denom != 0)

        self.density = [str(v) for v in ne]

    def get_errors(self, low_Te_error=4):
        if self.signals_noise_integrals is None or self.signals_integrals is None:
            self.get_temperatures()

        if not self.temperatures:
            self.get_temperatures()

        if not self.density:
            self.get_density()

        self._prepare_fe_cache()

        laser_energies = np.asarray(self._normalize_laser_energy(), dtype=float)
        sigma = np.asarray(self.signals_noise_integrals, dtype=float)

        with np.errstate(divide="ignore", invalid="ignore"):
            w = np.divide(1.0, np.square(sigma), out=np.zeros_like(sigma), where=sigma > 0)

        te_values = np.asarray([float(t) for t in self.temperatures], dtype=float)
        ne_values = np.asarray([float(n) for n in self.density], dtype=float)

        te_idx = np.asarray([self._te_index_map[t] for t in te_values], dtype=int)

        full_coef = (
                self.absolut_calibration
                * self.ELECTRON_RADIUS ** 2
                * self.laser.laser_wl
                / (self.DEFAULT_M * self.E_CHARGE)
        )

        self.errors_T = []
        self.errors_n = []

        for i, idx in enumerate(te_idx):
            try:
                # forward difference as in original logic
                if idx + 1 >= len(self._te_grid_arr):
                    self.errors_T.append(0)
                    self.errors_n.append(0)
                    continue

                T0 = self._te_grid_arr[idx]
                T1 = self._te_grid_arr[idx + 1]
                dT = T1 - T0

                if dT == 0:
                    self.errors_T.append(0)
                    self.errors_n.append(0)
                    continue

                # Same model as in fit:
                # mu_ch = A * F_ch(T)
                # where A = ne * full_coef * E_laser
                F0 = self._F[idx, : self.ch_number]
                F1 = self._F[idx + 1, : self.ch_number]
                dF_dT = (F1 - F0) / dT

                A = ne_values[i] * full_coef * laser_energies[i]

                # Jacobian wrt parameters [A, T]
                # dmu/dA = F0
                # dmu/dT = A * dF_dT
                J = np.column_stack((F0, A * dF_dT))  # (ch, 2)

                Wi = np.diag(w[i, : self.ch_number])
                fisher = J.T @ Wi @ J

                cov = np.linalg.inv(fisher)

                err_A = math.sqrt(max(cov[0, 0], 0.0))
                err_T = math.sqrt(max(cov[1, 1], 0.0))

                denom_n = full_coef * laser_energies[i]
                if denom_n == 0:
                    self.errors_T.append(0)
                    self.errors_n.append(0)
                    continue

                err_n = err_A / denom_n

                if te_values[i] < low_Te_error:
                    err_T = min(low_Te_error, err_T)

                self.errors_T.append(str(err_T))
                self.errors_n.append(str(err_n))

            except (IndexError, ZeroDivisionError, ValueError, np.linalg.LinAlgError):
                self.errors_T.append(0)
                self.errors_n.append(0)

    def write_raw_signals(self, path: Path):
        path_entry = os.path.join(path, self.poly_name)
        for ch in range(self.ch_number):
            path_to_file = path_entry + f"_{ch + 1}channel.csv"
            with open(path_to_file, "w") as w_file:
                for count in range(1024):
                    string = f"{count * self.T_STEP}, "
                    for shot in self.signals[ch]:
                        string += f"{str(shot[count])}, "
                    w_file.write(string + "\n")

    def debug_chi2(self):
        self._prepare_fe_cache()

        y = np.asarray(self.signals_integrals, dtype=float)
        sigma = np.asarray(self.signals_noise_integrals, dtype=float)

        te_values = [float(t) for t in self.temperatures]
        te_idx = [self._te_index_map[t] for t in te_values]

        laser = np.asarray(self._normalize_laser_energy(), dtype=float)

        full_coef = (
                self.absolut_calibration
                * self.ELECTRON_RADIUS ** 2
                * self.laser.laser_wl
                / (self.DEFAULT_M * self.E_CHARGE)
        )

        chi2_list = []

        for i in range(10, 13):
            F = self._F[te_idx[i]]

            A = (
                    float(self.density[i])
                    * full_coef
                    * laser[i]
            )

            mu = A * F

            chi2 = np.sum(((y[i] - mu) / sigma[i]) ** 2)

            chi2_list.append(chi2)

        dof = self.ch_number - 2

        chi2_red = [c / dof for c in chi2_list]

        return chi2_red

    def chi2_profile(self, shot_index):
        """
        χ²(T) профиль для одного импульса.
        Возвращает:
            Te_grid, chi2(T), индекс минимума
        """

        # убедиться, что есть данные
        if self.signals_integrals is None or self.signals_noise_integrals is None:
            raise RuntimeError("run get_temperatures() first")

        # подготовить кэш fe
        if not self._fe_cache_ready:
            self._prepare_fe_cache()

        y = np.asarray(self.signals_integrals[shot_index], dtype=float)
        sigma = np.asarray(self.signals_noise_integrals[shot_index], dtype=float)

        w = 1.0 / sigma ** 2

        F = self._F
        Te_grid = self._te_grid_arr

        # оптимальная амплитуда A(T)
        sum1 = np.sum(y * F * w, axis=1)
        sum2 = np.sum(F ** 2 * w, axis=1)

        A = sum1 / sum2

        residuals = y - A[:, None] * F
        chi2 = np.sum((residuals ** 2) * w, axis=1)

        best_idx = int(np.argmin(chi2))

        return Te_grid, chi2, best_idx


def built_fibers(
        config_connection: dict,
        all_caens,
        combiscope_times,
        expected_fe: dict,
        spectral_calib: dict,
        absolut_calib: dict,
        laser_energy: float,
) -> (list, list[Polychromator]):
    equatorGain = GainsEquator()
    equator_fe = expected_fe

    laser = LaserNdYag(laser_wl=1064.4e-9, laser_energy=laser_energy)
    specs = [
        (
            "eqTS_46_G10",
            2,
            -37.1,
            1,
            slice(11, 15),
            config_connection["equator_caens"][1]["channels"][11:15],
            "eqTS_46_G10",
        ),
        (
            "eqTS_42_G10",
            3,
            -38.6,
            0,
            slice(1, 5),
            config_connection["equator_caens"][0]["channels"][1:5],
            "eqTS_42_G10",
        ),
        (
            "eqTS_47_G10",
            4,
            -39.9,
            0,
            slice(6, 10),
            config_connection["equator_caens"][0]["channels"][6:10],
            "eqTS_47_G10",
        ),
        (
            "eqTS_48_G10",
            5,
            -41.0,
            0,
            slice(11, 15),
            config_connection["equator_caens"][0]["channels"][11:15],
            "eqTS_48_G10",
        ),
        (
            "eqTS_49_G10",
            6,
            -42.2,
            1,
            slice(1, 5),
            config_connection["equator_caens"][1]["channels"][1:5],
            "eqTS_49_G10",
        ),
        (
            "eqTS_50_G10",
            7,
            -43.25,
            1,
            slice(6, 10),
            config_connection["equator_caens"][1]["channels"][6:10],
            "eqTS_50_G10",
        ),
    ]

    fibers = []
    for (
            name,
            fiber_num,
            z_cm,
            caen_index,
            chan_slice,
            cfg_channels,
            calib_poly_name,
    ) in specs:
        caen = all_caens[caen_index]
        poly = Polychromator(
            poly_name=name,
            fiber_number=fiber_num,
            z_cm=z_cm,
            config_connection=cfg_channels,
            gains=equatorGain,
            fe_expected=equator_fe,
            laser=laser,
            spectral_calib=spectral_calib[calib_poly_name],
            absolut_calib=absolut_calib[calib_poly_name],
            caen_time=caen["shots_time"],
            caen_data=caen["caen_channels"][chan_slice],
        )
        fibers.append(poly)

    del all_caens
    return combiscope_times, fibers


def calculate_Te_ne(fibers: Polychromator | list[Polychromator]):
    for fiber in fibers:
        fiber.get_temperatures()
        fiber.get_density()
        fiber.get_errors()

        # chi = fiber.debug_chi2()
        #
        # Te_grid, chi2, best = fiber.chi2_profile(11)
        # import matplotlib.pyplot as plt
        #
        # plt.plot(Te_grid, chi2)
        # plt.axvline(float(fiber.temperatures[11]), linestyle="--")
        # plt.xlabel("Te (eV)")
        # plt.ylabel("chi2")
        # plt.show()
        #
        # print("mean chi2:", np.mean(chi))
        # print("median chi2:", np.median(chi))
