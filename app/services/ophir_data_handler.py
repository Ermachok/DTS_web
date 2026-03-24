import os


def get_ophir_data(
    ophir_path: str,
    ophir_shot_name: str,
    lines_indent: int = 36,
    ophir_to_J: float = 0.0275,
) -> list:
    for file in os.listdir(ophir_path):
        if file.endswith(ophir_shot_name):
            with open(rf"{ophir_path}\{file}", "r") as ophir_file:
                ophir_data = ophir_file.readlines()

            ophir_energy = [
                float(ophir_data[lines_indent + i].split("\t")[1]) / ophir_to_J
                for i in range(len(ophir_data) - lines_indent)
            ]
            return ophir_energy
    raise FileExistsError


def get_ophir_data_from_file(
    file_bytes: bytes, lines_indent: int = 36, ophir_to_J: float = 0.0275
) -> list[float]:

    text = file_bytes.decode("utf-8", errors="ignore")
    lines = text.splitlines()

    ophir_energy = [
        float(lines[lines_indent + i].split("\t")[1]) / ophir_to_J
        for i in range(len(lines) - lines_indent)
    ]

    return ophir_energy
