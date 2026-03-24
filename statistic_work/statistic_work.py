import csv
import json
from pathlib import Path

from app.services.caen_handler import handle_all_caens
from app.services.poly_factory import built_fibers, calculate_Te_ne

BASE_DATA_PATH = Path(r"C:\experimantal_data\DTS\autumn_2025\DTS")
OUT_BASE_PATH = Path(r"C:\Users\user\PycharmProjects\DTS_web")

TE_FILE = OUT_BASE_PATH / "Te_all.csv"
NE_FILE = OUT_BASE_PATH / "ne_all.csv"

DEFAULT_PATHS = {
    "connections": Path("../config/config_connection_11_2025.json"),
    "absolut_calib": Path(
        "../calibrations/absolute/absolute_calib_jan2026_no_pest.json"
    ),
    "spectral_calib": Path(
        "../calibrations/relative/EN_spectral_config_2024_05_14_WRONG.json"
    ),
    "fe_expected": Path("../fe_expected/f_expected_equator_june2024.json"),
}

CONFIG_DATA = {
    "absolut_calib": None,
    "spectral_calib": None,
    "fe_expected": None,
    "connections": None,
}


def load_single_config(file_path: Path, key: str):
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        CONFIG_DATA[key] = json.load(f)


def load_all_configs():
    for key, path in DEFAULT_PATHS.items():
        load_single_config(path, key)


def init_global_csvs(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    if not TE_FILE.exists():
        with open(TE_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                [
                    "shot_id",
                    "shot_index",
                    "combiscope_time_ms",
                    "Te_eV",
                    "Te_error",
                    "z_cm",
                    "poly_name",
                ]
            )

    if not NE_FILE.exists():
        with open(NE_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                [
                    "shot_id",
                    "shot_index",
                    "combiscope_time_ms",
                    "ne_m3",
                    "ne_error",
                    "z_cm",
                    "poly_name",
                ]
            )


def select_indices(times, t_min=160.0, t_max=190.0):
    return [i for i, t in enumerate(times) if t_min <= t <= t_max]


def append_global_csvs(
    fiber,
    shot_id,
    combiscope_times,
    indices,
):
    with open(TE_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for i in indices:
            w.writerow(
                [
                    shot_id,
                    i,
                    combiscope_times[i],
                    fiber.temperatures[i],
                    fiber.errors_T[i],
                    fiber.z_cm,
                    fiber.poly_name,
                ]
            )

    with open(NE_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for i in indices:
            w.writerow(
                [
                    shot_id,
                    i,
                    combiscope_times[i],
                    fiber.density[i],
                    fiber.errors_n[i],
                    fiber.z_cm,
                    fiber.poly_name,
                ]
            )


def main():
    load_all_configs()

    config = CONFIG_DATA["connections"]
    expected_fe = CONFIG_DATA["fe_expected"]
    abs_calib = CONFIG_DATA["absolut_calib"]
    spec_calib = CONFIG_DATA["spectral_calib"]

    init_global_csvs(OUT_BASE_PATH)

    for shot_dir in sorted(p for p in BASE_DATA_PATH.iterdir() if p.is_dir()):
        shot_id = shot_dir.name
        print(f"Processing {shot_id}")

        try:
            data = handle_all_caens(path=shot_dir)
            all_caens = data["caens_data"]
            combiscope_times = data["combiscope_times"]

            combiscope_times, fibers = built_fibers(
                config_connection=config,
                all_caens=all_caens,
                combiscope_times=combiscope_times,
                expected_fe=expected_fe,
                spectral_calib=spec_calib,
                absolut_calib=abs_calib,
                laser_energy=1.5,
            )

            valid_idx = select_indices(combiscope_times)
            if not valid_idx:
                continue

            calculate_Te_ne(fibers)

            for fiber in fibers:
                append_global_csvs(
                    fiber,
                    shot_id,
                    combiscope_times,
                    valid_idx,
                )

        except Exception as e:
            print(f"ERROR {shot_id}: {e}")
            pass


if __name__ == "__main__":
    main()
