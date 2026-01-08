import numpy as np


def load_txt_matrix(path: str) -> np.ndarray:
    """
    Загружает матрицу из txt.
    Разделители: пробелы или табы.
    Пропускает пустые строки.
    """
    rows = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            row = [float(x) for x in parts]
            rows.append(row)

    M = np.array(rows)

    # Проверки для ясности
    if M.shape[0] < 2 or M.shape[1] < 2:
        raise ValueError("Матрица слишком маленькая или неправильный формат")

    return M


def extract_times(M: np.ndarray):
    # первая строка: 0, t1, t2, ...
    return M[0, 1:].tolist()


def extract_radii(M: np.ndarray):
    # первый столбец: 0, R1, R2, ...
    radii = [R / 1000 for R in M[1:, 0].tolist()]
    return radii


def slice_T(M: np.ndarray, time_index: int):
    # T(R, t): строки 1.., столбец time_index+1
    return M[1:, time_index + 1].tolist()
