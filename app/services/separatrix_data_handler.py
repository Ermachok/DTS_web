import os
import json
import bisect
from typing import List, Dict, Tuple

UPLOAD_DIR = "uploads/separatrix"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_uploaded_file(upload_file, dest_name: str) -> str:
    """
    Сохраняет UploadFile в UPLOAD_DIR под именем dest_name.
    Возвращает полный путь.
    """
    dest_path = os.path.join(UPLOAD_DIR, dest_name)
    with open(dest_path, "wb") as out_f:
        upload_file.file.seek(0)
        out_f.write(upload_file.file.read())
    return dest_path


def get_available_timestamps_ms(path: str) -> List[float]:
    """
    Возвращает список времён (ms) из файла.
    Ожидается mcc_data["time"]["variable"] в секундах.
    """
    with open(path, "r", encoding="utf-8") as f:
        mcc_data = json.load(f)
    times_s = mcc_data.get("time", {}).get("variable", [])
    return [float(t) * 1000.0 for t in times_s]


def _get_boundary_vars_for_index(mcc_data: dict, index: int) -> Dict[str, Tuple[List[float], List[float]]]:
    """
    Возвращает (r_list, z_list) для сегментов по индексу (сырые значения из файла).
    """
    b = mcc_data["boundary"]
    return {
        "body": (b["rbdy"]["variable"][index], b["zbdy"]["variable"][index]),
        "leg_1": (b["rleg_1"]["variable"][index], b["zleg_1"]["variable"][index]),
        "leg_2": (b["rleg_2"]["variable"][index], b["zleg_2"]["variable"][index]),
    }


def get_separatrix_at_time(path: str, time_ms: float) -> Dict:
    """
    Возвращает separatrix для произвольного времени time_ms (ms) с линейной интерполяцией.
    Если длины массивов для сегмента различаются — возвращается ближайший срез (fallback).
    Результат масштабируется так же, как в вашей оригинальной функции (/100).
    """
    with open(path, "r", encoding="utf-8") as f:
        mcc_data = json.load(f)

    times_s = mcc_data.get("time", {}).get("variable", [])
    n = len(times_s)
    if n == 0:
        raise ValueError("Файл не содержит временных меток")

    t_s = float(time_ms) / 1000.0
    idx_right = bisect.bisect_right(times_s, t_s)
    idx_left = max(0, idx_right - 1)

    if idx_left >= n:
        idx_left = n - 1
    if idx_right >= n:
        idx_right = n - 1

    t_left_ms = float(times_s[idx_left]) * 1000.0
    t_right_ms = float(times_s[idx_right]) * 1000.0

    if idx_left == idx_right or (t_right_ms - t_left_ms) == 0:
        alpha = 0.0
    else:
        alpha = (time_ms - t_left_ms) / (t_right_ms - t_left_ms)
        alpha = max(0.0, min(1.0, alpha))

    seg_left = _get_boundary_vars_for_index(mcc_data, idx_left)
    seg_right = _get_boundary_vars_for_index(mcc_data, idx_right)

    result = {}
    for seg_name in ("body", "leg_1", "leg_2"):
        rL, zL = seg_left[seg_name]
        rR, zR = seg_right[seg_name]

        if len(rL) == len(rR) and len(zL) == len(zR) and len(rL) == len(zL):
            r_interp = []
            z_interp = []
            for a, b, c, d in zip(rL, rR, zL, zR):
                r_val = float(a) + alpha * (float(b) - float(a))
                z_val = float(c) + alpha * (float(d) - float(c))
                r_interp.append(r_val / 100.0)
                z_interp.append(z_val / 100.0)
            result[seg_name] = {"R": r_interp, "Z": z_interp}
        else:
            pick_idx = idx_left if alpha < 0.5 else idx_right
            pick_seg = seg_left if pick_idx == idx_left else seg_right
            r_pick, z_pick = pick_seg[seg_name]
            result[seg_name] = {"R": [float(x) / 100.0 for x in r_pick], "Z": [float(x) / 100.0 for x in z_pick]}

    return {
        "body": result["body"],
        "leg_1": result["leg_1"],
        "leg_2": result["leg_2"],
        "requested_time_ms": float(time_ms),
        "used_indices": {"left": idx_left, "right": idx_right},
    }
