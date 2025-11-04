import json
from pathlib import Path


class GainsEquator:
    def setup(self):
        self.full_gain = (
            self.q_e
            * self.M_gain
            * self.R_gain
            * self.G_magic
            * self.divider
            * self.gain_out
        )
        self.converter = self.mV_2_V * self.ns_2_s
        self.resulting_multiplier = self.converter / self.full_gain

    def __init__(self):
        self.q_e = 1.6e-19
        self.M_gain = 1e2
        self.R_gain = 1e4
        self.G_magic = 2.43
        self.divider = 0.5
        self.gain_out = 10
        self.mV_2_V = 1e-3
        self.ns_2_s = 1e-9

        self.full_gain = None
        self.converter = None
        self.resulting_multiplier = None

        self.setup()


class Gains_T15_34:
    def setup(self):
        self.full_gain = self.q_e * self.M_gain * self.R_gain * self.gain_out
        self.converter = self.mV_2_V * self.ns_2_s
        self.resulting_multiplier = self.converter / self.full_gain

    def __init__(self):
        self.M_gain = 1e2
        self.q_e = 1.6e-19
        self.gain_out = 10
        self.R_gain = 1e4

        self.mV_2_V = 1e-3
        self.ns_2_s = 1e-9

        self.full_gain = None
        self.converter = None
        self.resulting_multiplier = None

        self.setup()


class Gains_T15_35(Gains_T15_34):
    def setup(self):
        self.full_gain = self.q_e * self.M_gain * self.R_gain * self.gain_out
        self.converter = self.mV_2_V * self.ns_2_s
        self.resulting_multiplier = self.converter / self.full_gain

    def __init__(self):
        super().__init__()
        self.R_gain = 5e3

        self.setup()


class ExpectedFe:
    def __init__(self, equator_poly_path: Path = None, t15_poly_path: Path = None):
        if equator_poly_path:
            self.equator_fe = self.load_fe_expected(equator_poly_path)

        if t15_poly_path:
            self.t15_fe = self.load_fe_expected(t15_poly_path)

    @staticmethod
    def load_fe_expected(path: Path):
        with open(path, "r") as f_file:
            fe_data = json.load(f_file)
        return fe_data


class LaserNdYag:
    def __init__(self, laser_wl: float, laser_energy: float):
        self.laser_wl = laser_wl
        self.laser_energy = laser_energy


