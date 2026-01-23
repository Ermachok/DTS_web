from pathlib import Path
import msgpack


def caen_msg_handler(
        path, t_step=0.325, time_shift=100, processed_shots: int | str = 30
):
    """
    :param time_shift: сдвиг для построения в одной системе координат
    :param path:путь до файла
    :param t_step: шаг оцифровщика
    :param noise_len: длина для вычисления уровня над нулем и уровня шума
    :param processed_shots: количество обработанных выстрелов
    :return:
    """

    times = []
    caen = []
    caen_channels_number = 16
    with path.open(mode="rb") as file:
        data = msgpack.unpackb(file.read())

    if str(processed_shots).lower() == "all":
        processed_shots = len(data)

    combiscope_times = []
    for caen_channel in range(caen_channels_number):
        caen_ch = []
        for laser_shot in range(processed_shots):
            if caen_channel == 0:
                combiscope_times.append(round(data[laser_shot]["t"] - data[0]["t"], 3))
            signal = data[laser_shot]["ch"][caen_channel]
            caen_ch.append(signal)
        caen.append(caen_ch)

    for laser_shot in range(processed_shots):
        max_position_ind = caen[0][laser_shot].index(max(caen[0][laser_shot]))
        time = [time_shift - (max_position_ind - t) * t_step for t in range(1024)]
        times.append(time)

    return combiscope_times[1:], times, caen  # [1:] - первый нулевой запуск опускаю


def handle_all_caens(path: Path = "uploads/msg_pkgs", processed_shots: int | str = 30) -> (list, list):
    msg_files_num_x10 = [6, 7]

    all_caens = []
    combiscope_times = []
    for msg_num in msg_files_num_x10:
        new_path = Path(f"{path}/{str(msg_num)}.msgpk")
        combiscope_times, times, caen_data = caen_msg_handler(
            new_path, processed_shots=processed_shots
        )
        all_caens.append(
            {"caen_num": msg_num, "shots_time": times, "caen_channels": caen_data}
        )

    return {"combiscope_times": combiscope_times, "caens_data": all_caens}
