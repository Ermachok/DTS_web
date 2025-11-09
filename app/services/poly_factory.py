import bisect
import math
import os.path
import statistics
from pathlib import Path
import matplotlib.pyplot as plt
from app.services.diagnostic_utils import GainsEquator, LaserNdYag


class Polychromator:
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
        """
        :param poly_name: номер полихроматора в стойке!
        :param fiber_number: номер волокна, 1 - вверх
        :param caen_time: приведенные по максимуму времена
        :param caen_data: данные с каена, 5 каналов
        :param config_connection: конфиг
        :param absolut_calib:
        """

        self.poly_name = poly_name
        self.fiber_number = fiber_number
        self.z_cm = z_cm

        self.signals = caen_data
        self.signals_time = caen_time
        self.ch_number = len(self.signals)
        self.gain = gains
        self.laser = laser

        self.signals_integrals = None
        self.signals_noise_integrals = None

        self.fe_data = fe_expected
        self.expected_data = None
        self.config = config_connection

        self.spectral_calibration = spectral_calib
        self.absolut_calibration = absolut_calib

        # self.load_spectral_calibration(spectral_calib_path=spectral_calib)
        # self.load_absolut_calibration(absolut_calib_path=absolut_calib)

        self.temperatures = []
        self.density = []

        self.errors_T = []
        self.errors_n = []

    def get_signal_integrals(
            self, shots_before_plasma: int = 4, shots_after: int = 17, t_step: float = 0.325
    ) -> tuple[list, list]:
        """
        RETURNS PHE
        :param shots_before_plasma:
        :param shots_after:
        :param t_step:
        :return:
        """
        excess_noise_factor = 3
        all_const = self.gain.resulting_multiplier
        noise_len = 300

        all_shots_signal = []
        all_shots_noise = []
        for shot in range(1, shots_before_plasma + shots_after):  # 1 пропускаю 0 запуск
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

                signal_lvl = statistics.median(self.signals[poly_ch][shot][:noise_len])
                lvl_integral = signal_lvl * (
                        self.config[poly_ch]["sig_RightBord"]
                        - self.config[poly_ch]["sig_LeftBord"]
                )
                if poly_ch == 0:
                    summ_of_ideal_thomson_signal = 24  # взят отнормированный сигнал томсона без шумов
                    sig_maximum = max(
                        self.signals[poly_ch][shot][
                        signal_ind[0]: signal_ind[
                            1]])
                    signal_integral = (sig_maximum - signal_lvl) * summ_of_ideal_thomson_signal * t_step

                    print(self.poly_name, signal_integral)

                else:
                    signal_integral = (
                            sum(self.signals[poly_ch][shot][signal_ind[0]: signal_ind[1]])
                            * t_step
                            - lvl_integral
                    )

                phe_number = signal_integral * all_const

                noise_track = (
                                      (statistics.stdev(self.signals[poly_ch][shot][:noise_len]))
                                      * all_const
                                      * t_step
                                      * (signal_ind[1] - signal_ind[0])
                              ) ** 2

                if phe_number > 0:
                    noise_excess = phe_number * excess_noise_factor
                else:
                    phe_number = 1
                    noise_excess = 0
                all_ch_signal.append(phe_number)
                all_ch_noise.append((noise_track + noise_excess) ** 0.5)

            all_shots_signal.append(all_ch_signal)
            all_shots_noise.append(all_ch_noise)

        return all_shots_signal, all_shots_noise

    def get_temperatures(self):
        """
        GIVES TEMPERATURE LIST
        :return:
        """
        self.signals_integrals, self.signals_noise_integrals = (
            self.get_signal_integrals()
        )
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
                                       - sum_1 * (f_e[ch] * self.spectral_calibration[ch]) / sum_2
                               ) ** 2 / noise[ch] ** 2
                    ans.append({T_e: khi})

            results.append(ans)

        for shot_integral in results:
            sort = sorted(shot_integral, key=lambda x: list(x.values())[0])
            for T in sort[0].keys():
                self.temperatures.append(T)

    def get_density(self, apd_gain: float = 100):
        electron_radius = 2.81e-15
        e_charge = 1.6e-19

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
                sum_divider += (
                                       self.fe_data[T_e][ch] * self.spectral_calibration[ch]
                               ) ** 2 / noise_phe[ch] ** 2

            self.density.append(
                str(
                    sum_numerator
                    / (
                            sum_divider
                            * self.laser.laser_energy
                            * (self.laser.laser_wl / (apd_gain * e_charge))
                            * self.absolut_calibration
                            * electron_radius ** 2
                    )
                )
            )

    def get_errors(self):
        ch_nums = self.ch_number

        electron_radius = 2.81e-15
        laser_wl = 1064.4e-9
        e_charge = 1.6e-19
        M = 100
        laser_energy = 1.2

        full_coef = (
                self.absolut_calibration
                * laser_energy
                * electron_radius ** 2
                * laser_wl
                / (M * e_charge)
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
                    derivative_fe = (
                                            self.fe_data[T_e][ch] - self.fe_data[T_e_next][ch]
                                    ) / T_e_step

                    sum_fe_to_noise += (self.fe_data[T_e][ch] / shot_noise[ch]) ** 2
                    sum_derivative_fe_to_noise += (derivative_fe / shot_noise[ch]) ** 2
                    sum_fe_derivative_fe_to_noise += (
                                                             derivative_fe * self.fe_data[T_e][ch] / shot_noise[ch] ** 2
                                                     ) ** 2

                M_errT = sum_fe_to_noise / (
                        sum_fe_to_noise * sum_derivative_fe_to_noise
                        - sum_fe_derivative_fe_to_noise
                )

                M_errn = sum_derivative_fe_to_noise / (
                        sum_fe_to_noise * sum_derivative_fe_to_noise
                        - sum_fe_derivative_fe_to_noise
                )

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

    def get_expected_phe(self):
        from_shot = 5
        to_shot = 20

        electron_radius = 6.6e-29
        laser_energy = 1.5

        for shot, T_e, n_e in zip(
                self.signals_integrals[from_shot:to_shot],
                self.temperatures[from_shot:to_shot],
                self.density[from_shot:to_shot],
        ):
            print("shot_number ", self.signals_noise_integrals.index(shot), end="  ")
            print(
                T_e,
                n_e,
                "got ",
                shot[0],
                "expected",
                self.absolut_calibration
                * self.fe_data[T_e][0]
                * electron_radius
                * laser_energy
                * float(n_e),
                "got",
                shot[1],
                "expected",
                self.absolut_calibration
                * self.fe_data[T_e][1]
                * electron_radius
                * laser_energy
                * float(n_e),
            )

    def plot_raw_signals(self, from_shot: int = 10, to_shot: int | str = 20):
        fig, ax = plt.subplots(nrows=len(self.signals), ncols=1, figsize=(13, 8))

        if int == type(to_shot):
            pass
        elif str.lower(to_shot) == "all":
            to_shot = len(self.signals[0])

        for ch in range(len(self.signals)):
            for shot in range(from_shot, to_shot):
                time, signal = self.get_raw_data(shot_num=shot, ch_num=ch)
                ax[ch].plot(time, signal, label="shot %d" % shot)
                ax[ch].set_xlim([0, 80])
        ax[0].legend(ncol=3)
        plt.subplots_adjust(left=0.05, right=0.95, top=0.96, bottom=0.07)
        ax[0].set_title(f"{self.poly_name}")
        plt.show()

    def get_raw_data(self, shot_num: int = None, ch_num: int = None):
        if ch_num is None and shot_num is None:
            return self.signals_time, self.signals
        return self.signals_time[shot_num], self.signals[ch_num][shot_num]

    def write_raw_signals(self, path: Path):

        path_entry = os.path.join(path, self.poly_name)
        for ch in range(self.ch_number):
            path = path_entry + f"_{ch + 1}channel.csv"
            with open(path, "w") as w_file:
                for count in range(1024):
                    string = f"{count * 0.325}, "
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

    laser = LaserNdYag(laser_wl=1064.4e-9, laser_energy=laser_energy)

    poly_042 = Polychromator(
        poly_name="eqTS_42_G10",
        fiber_number=3,
        z_cm=-38.6,
        config_connection=config_connection["equator_caens"][0]["channels"][1:5],
        gains=equatorGain,
        fe_expected=equator_fe,
        laser=laser,
        spectral_calib=spectral_calib["eqTS_42_G10"],
        absolut_calib=absolut_calib["eqTS_42_G10"],
        caen_time=all_caens[0]["shots_time"],
        caen_data=all_caens[0]["caen_channels"][1:5],
    )

    poly_046 = Polychromator(
        poly_name="eqTS_46_G10",
        fiber_number=2,
        z_cm=-37.1,
        config_connection=config_connection["equator_caens"][1]["channels"][11:16],
        gains=equatorGain,
        fe_expected=equator_fe,
        laser=laser,
        spectral_calib=spectral_calib["eqTS_46_G10"],
        absolut_calib=absolut_calib["eqTS_46_G10"],
        caen_time=all_caens[1]["shots_time"],
        caen_data=all_caens[1]["caen_channels"][11:16],
    )

    poly_047 = Polychromator(
        poly_name="eqTS_47_G10",
        fiber_number=4,
        z_cm=-39.9,
        config_connection=config_connection["equator_caens"][0]["channels"][6:10],
        gains=equatorGain,
        fe_expected=equator_fe,
        laser=laser,
        spectral_calib=spectral_calib["eqTS_47_G10"],
        absolut_calib=absolut_calib["eqTS_47_G10"],
        caen_time=all_caens[0]["shots_time"],
        caen_data=all_caens[0]["caen_channels"][6:10],
    )

    poly_048 = Polychromator(
        poly_name="eqTS_48_G10",
        fiber_number=5,
        z_cm=-41,
        config_connection=config_connection["equator_caens"][0]["channels"][11:16],
        gains=equatorGain,
        fe_expected=equator_fe,
        laser=laser,
        spectral_calib=spectral_calib["eqTS_48_G10"],
        absolut_calib=absolut_calib["eqTS_48_G10"],
        caen_time=all_caens[0]["shots_time"],
        caen_data=all_caens[0]["caen_channels"][11:16],
    )

    poly_049 = Polychromator(
        poly_name="eqTS_49_G10",
        fiber_number=6,
        z_cm=-42.2,
        config_connection=config_connection["equator_caens"][1]["channels"][1:5],
        gains=equatorGain,
        fe_expected=equator_fe,
        laser=laser,
        spectral_calib=spectral_calib["eqTS_49_G10"],
        absolut_calib=absolut_calib["eqTS_49_G10"],
        caen_time=all_caens[1]["shots_time"],
        caen_data=all_caens[1]["caen_channels"][1:5],
    )

    poly_050 = Polychromator(
        poly_name="eqTS_50_G10",
        fiber_number=7,
        z_cm=-43.25,
        config_connection=config_connection["equator_caens"][1]["channels"][6:10],
        gains=equatorGain,
        fe_expected=equator_fe,
        laser=laser,
        spectral_calib=spectral_calib["eqTS_50_G10"],
        absolut_calib=absolut_calib["eqTS_50_G10"],
        caen_time=all_caens[1]["shots_time"],
        caen_data=all_caens[1]["caen_channels"][6:10],
    )

    del all_caens

    fibers = [
        poly_046,
        poly_042,
        poly_047,
        poly_048,
        poly_049,
        poly_050,
    ]

    return combiscope_times, fibers


def calculate_Te_ne(fibers: Polychromator | list[Polychromator]):
    for fiber in fibers:
        fiber.get_temperatures()
        fiber.get_density()
        fiber.get_errors()
