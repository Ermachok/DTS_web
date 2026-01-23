import bisect
import math
import os.path
import statistics
import numpy as np
from pathlib import Path
from app.services.diagnostic_utils import GainsEquator, LaserNdYag


class Polychromator:
    # Class-level constants
    EXCESS_NOISE_FACTOR = 3
    ELECTRON_RADIUS = 2.81e-15
    E_CHARGE = 1.6e-19
    LASER_WL = 1064.4e-9
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
            absolut_calib: Path | dict = None,
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

        self.spectral_calibration = spectral_calib[:self.ch_number]
        self.absolut_calibration = absolut_calib

        self.temperatures = []
        self.density = []

        self.errors_T = []
        self.errors_n = []

    def get_signal_integrals(
            self, shots_before_plasma: int = 4, shots_after: int = 17
    ) -> tuple[list, list]:
        all_const = self.gain.resulting_multiplier

        all_shots_signal = []
        all_shots_noise = []
        for shot in range(1, shots_before_plasma + shots_after):
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

                signal_lvl = statistics.median(self.signals[poly_ch][shot][:self.NOISE_LEN])
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

                noise_track_mV = [1100 - 1250 + v * 2500/4096 for v in self.signals[poly_ch][shot][:self.NOISE_LEN]]
                noise_track = (
                        (
                                statistics.stdev(noise_track_mV)
                                * all_const
                                * self.T_STEP
                                * (signal_ind[1] - signal_ind[0])
                        )
                        ** 2 + 0.01
                )
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
        results = []
        for shot_integral, noise in zip(
                self.signals_integrals, self.signals_noise_integrals
        ):
            ans = []
            for index, (T_e, f_e) in enumerate(self.fe_data.items()):
                khi = 0
                if index >= 2:
                    sum_1 = 0
                    sum_2 = 0
                    for ch in range(self.ch_number):
                        sum_1 += (
                                shot_integral[ch]
                                * (f_e[ch] * self.spectral_calibration[ch])
                                / noise[ch] ** 2
                        )
                        sum_2 += (f_e[ch] * self.spectral_calibration[ch]) ** 2 / noise[
                            ch
                        ] ** 2

                    for ch in range(self.ch_number):
                        khi += (
                                       shot_integral[ch]
                                       - sum_1
                                       * (f_e[ch] * self.spectral_calibration[ch])
                                       / sum_2
                               ) ** 2 / noise[ch] ** 2
                    ans.append({T_e: khi})

            results.append(ans)

        for shot_integral in results:
            sort = sorted(shot_integral, key=lambda x: list(x.values())[0])
            for T in sort[0].keys():
                self.temperatures.append(T)

    def get_density(self, apd_gain: float = 100):
        if not self.temperatures:
            self.get_temperatures()

        for shot_phe, noise_phe, T_e in zip(
                self.signals_integrals, self.signals_noise_integrals, self.temperatures
        ):
            sum_numerator = 0
            sum_divider = 0
            for ch in range(self.ch_number):
                sum_numerator += (
                        shot_phe[ch]
                        * (self.fe_data[T_e][ch] * self.spectral_calibration[ch])
                        / noise_phe[ch] ** 2
                )
                sum_divider += (self.fe_data[T_e][ch] * self.spectral_calibration[ch]
                                ) ** 2 / noise_phe[ch] ** 2

            self.density.append(
                str(
                    sum_numerator
                    / (
                            sum_divider
                            * self.laser.laser_energy
                            * (self.laser.laser_wl / (apd_gain * self.E_CHARGE))
                            * self.absolut_calibration
                            * self.ELECTRON_RADIUS ** 2
                    )
                )
            )

    def get_errors(self, low_Te_error=4):
        ch_nums = self.ch_number

        full_coef = (
                self.absolut_calibration
                * self.laser.laser_energy
                * self.ELECTRON_RADIUS ** 2
                * self.LASER_WL
                / (self.DEFAULT_M * self.E_CHARGE)
        )

        for shot_noise, T_e in zip(self.signals_noise_integrals, self.temperatures):
            try:
                shot_num = self.signals_noise_integrals.index(shot_noise)
                T_e_ind = self.fe_data["Te_grid"].index(float(T_e))
                T_e_next = str(self.fe_data["Te_grid"][T_e_ind + 1])

                sum_fe_to_noise = 0
                sum_derivative_fe_to_noise = 0
                sum_fe_derivative_fe_to_noise = 0
                T_e_step = float(T_e_next) - float(T_e)
                for ch in range(ch_nums):
                    derivative_fe = (self.fe_data[T_e][ch] - self.fe_data[T_e_next][ch]
                                     ) / T_e_step

                    sum_fe_to_noise += (self.fe_data[T_e][ch] / shot_noise[ch]) ** 2
                    sum_derivative_fe_to_noise += (derivative_fe / shot_noise[ch]) ** 2
                    sum_fe_derivative_fe_to_noise += (
                                                             derivative_fe
                                                             * self.fe_data[T_e][ch]
                                                             / shot_noise[ch] ** 2
                                                     ) ** 2

                M_errT = sum_fe_to_noise / (
                        sum_fe_to_noise * sum_derivative_fe_to_noise
                        - sum_fe_derivative_fe_to_noise
                )

                M_errn = sum_derivative_fe_to_noise / (
                        sum_fe_to_noise * sum_derivative_fe_to_noise
                        - sum_fe_derivative_fe_to_noise
                )

                if float(T_e) < low_Te_error:
                    self.errors_T.append(
                        str(min(low_Te_error,
                                math.sqrt(
                                    M_errT / (float(self.density[shot_num]) * full_coef) ** 2)
                                ))
                    )
                else:
                    self.errors_T.append(
                        str(
                            math.sqrt(
                                M_errT / (float(self.density[shot_num]) * full_coef) ** 2
                            )
                        )
                    )

                self.errors_n.append(str(math.sqrt(M_errn / full_coef ** 2)))

            except (IndexError, ZeroDivisionError, ValueError):
                self.errors_T.append(0)
                self.errors_n.append(0)

    def write_raw_signals(self, path: Path):
        path_entry = os.path.join(path, self.poly_name)
        for ch in range(self.ch_number):
            path = path_entry + f"_{ch + 1}channel.csv"
            with open(path, "w") as w_file:
                for count in range(1024):
                    string = f"{count * self.T_STEP}, "
                    for shot in self.signals[ch]:
                        string += f"{str(shot[count])}, "
                    w_file.write(string + "\n")


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

    laser = LaserNdYag(laser_wl=Polychromator.LASER_WL, laser_energy=laser_energy)

    specs = [
        ("eqTS_46_G10", 2, -37.1, 1, slice(11, 15), config_connection["equator_caens"][1]["channels"][11:15],
         "eqTS_46_G10"),

        ("eqTS_42_G10", 3, -38.6, 0, slice(1, 5), config_connection["equator_caens"][0]["channels"][1:5],
         "eqTS_42_G10"),

        ("eqTS_47_G10", 4, -39.9, 0, slice(6, 10), config_connection["equator_caens"][0]["channels"][6:10],
         "eqTS_47_G10"),

        ("eqTS_48_G10", 5, -41.0, 0, slice(11, 15), config_connection["equator_caens"][0]["channels"][11:15],
         "eqTS_48_G10"),

        ("eqTS_49_G10", 6, -42.2, 1, slice(1, 5), config_connection["equator_caens"][1]["channels"][1:5],
         "eqTS_49_G10"),

        ("eqTS_50_G10", 7, -43.25, 1, slice(6, 10), config_connection["equator_caens"][1]["channels"][6:10],
         "eqTS_50_G10"),
    ]

    fibers = []
    for name, fiber_num, z_cm, caen_index, chan_slice, cfg_channels, calib_poly_name in specs:
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
