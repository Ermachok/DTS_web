import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

TE_PATH = r"..\Te_all.csv"
NE_PATH = r"..\ne_all.csv"

E_CHARGE = 1.602176634e-19


def load_and_prepare_data(te_path, ne_path, time_ms: float, rel_error_filter: float):
    te = pd.read_csv(te_path)
    ne = pd.read_csv(ne_path)

    df = pd.merge(
        te,
        ne,
        on=["shot_id", "combiscope_time_ms", "z_cm", "poly_name"],
        how="inner",
        suffixes=("_Te", "_ne"),
    )

    df = df[
        (df["Te_eV"] > 0)
        & (df["Te_eV"] < 300)
        & (df["ne_m3"] > 0)
        & df["combiscope_time_ms"].between(time_ms - 1, time_ms + 1)
    ].copy()

    # фильтр по ошибкам
    df = df[
        (df["Te_error"] / df["Te_eV"] <= rel_error_filter)
        & (df["ne_error"] / df["ne_m3"] <= rel_error_filter)
    ].copy()

    # давление
    df["p_e_Pa"] = df["ne_m3"] * df["Te_eV"] * E_CHARGE

    return df


def get_nitrogen_shots():
    return (
        list(range(46587, 46595))
        + [46598]
        + list(range(46575, 46578))
        + list(range(46579, 46586))
        + [46559, 46560]
        + list(range(46482, 46488))
        + list(range(46491, 46493))
    )


def get_two_nbi_shots():
    return [46559]


def get_two_nbi_shots_without_n2():
    return [46548]


def get_one_nbi_shots():
    return list(range(46482, 46487)) + list(range(46491, 46493))


def split_by_nitrogen(df, nitrogen_shots):
    mask = df["shot_id"].isin(nitrogen_shots)
    return df[mask], df[~mask]


def split_by_nbi(df, one_nbi_shots):
    mask = df["shot_id"].isin(one_nbi_shots)
    return df[mask], df[~mask]


def split_by_2nbi(df, two_nbi_shots):
    mask = df["shot_id"].isin(two_nbi_shots)
    return df[mask], df[~mask]


def plot_global_phase_space(df_all, df_n2):
    plt.figure(figsize=(6.5, 5.5))

    plt.errorbar(
        df_all["Te_eV"],
        df_all["ne_m3"],
        xerr=df_all["Te_error"],
        yerr=df_all["ne_error"],
        fmt="o",
        ms=3,
        alpha=0.4,
        color="blue",
        ecolor="blue",
        label="Other shots",
    )

    plt.errorbar(
        df_n2["Te_eV"],
        df_n2["ne_m3"],
        xerr=df_n2["Te_error"],
        yerr=df_n2["ne_error"],
        fmt="o",
        ms=5,
        color="tab:red",
        ecolor="tab:red",
        label="Nitrogen shots",
    )

    plt.xlim(0, 150)
    plt.ylim(0, 2e20)
    plt.xlabel("Te [eV]")
    plt.ylabel("ne [m⁻³]")
    plt.title("Global Te–ne phase space")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_local_phase_space_per_z(df, nitrogen_shots, z_vals):
    fig, axs = plt.subplots(2, 3, figsize=(12, 9), sharex=True, sharey=True)
    axs = axs.flatten()

    for ax, z in zip(axs, z_vals):
        g = df[df["z_cm"] == z]

        if len(g) < 8:
            ax.axis("off")
            continue

        g_n2 = g[g["shot_id"].isin(nitrogen_shots)]
        g_bg = g[~g["shot_id"].isin(nitrogen_shots)]

        ax.errorbar(
            g_bg["Te_eV"],
            g_bg["ne_m3"],
            xerr=g_bg["Te_error"],
            yerr=g_bg["ne_error"],
            fmt="o",
            ms=4,
            alpha=0.4,
            color="blue",
            ecolor="blue",
        )

        ax.errorbar(
            g_n2["Te_eV"],
            g_n2["ne_m3"],
            xerr=g_n2["Te_error"],
            yerr=g_n2["ne_error"],
            fmt="o",
            ms=6,
            color="tab:red",
            ecolor="tab:red",
        )

        ax.set_xlim(0, 200)
        ax.set_ylim(0, 2e20)
        ax.set_title(f"z = {z:.1f} cm")
        ax.grid(True)

    for ax in axs[3:]:
        ax.set_xlabel("Te [eV]")
    axs[0].set_ylabel("ne [m⁻³]")
    axs[3].set_ylabel("ne [m⁻³]")

    plt.suptitle("Local Te–ne phase space per z", fontsize=16)
    plt.tight_layout(rect=(0, 0, 1, 0.96))
    plt.show()


def colored_boxplot(ax, data, positions, color):
    bp = ax.boxplot(
        data,
        positions=positions,
        widths=0.3,
        showfliers=False,
        patch_artist=False,
        showmeans=True,
    )
    for key in ["boxes", "whiskers", "caps", "medians"]:
        for item in bp[key]:
            item.set_color(color)
            item.set_linewidth(1.5)

    for mean in bp["means"]:
        mean.set_marker("x")
        mean.set_markersize(4)
        mean.set_markerfacecolor(color)
        mean.set_markeredgecolor(color)


def plot_boxplots_vs_z(df_n2, df_clear, z_vals):
    fig, axs = plt.subplots(1, 2, figsize=(12, 5), sharex=True)

    pos = np.arange(len(z_vals))
    offset = 0.18

    data_ne_n2 = [df_n2[df_n2["z_cm"] == z]["ne_m3"].values for z in z_vals]
    data_ne_bg = [df_clear[df_clear["z_cm"] == z]["ne_m3"].values for z in z_vals]

    colored_boxplot(axs[0], data_ne_n2, pos - offset, "red")
    colored_boxplot(axs[0], data_ne_bg, pos + offset, "blue")

    axs[0].set_yscale("log")
    axs[0].set_ylim(1e17, 1.5e20)
    axs[0].set_ylabel("ne [m⁻³]")
    axs[0].set_title("Electron density")
    axs[0].grid(True, which="both", axis="y")

    data_Te_n2 = [df_n2[df_n2["z_cm"] == z]["Te_eV"].values for z in z_vals]
    data_Te_bg = [df_clear[df_clear["z_cm"] == z]["Te_eV"].values for z in z_vals]

    colored_boxplot(axs[1], data_Te_n2, pos - offset, "red")
    colored_boxplot(axs[1], data_Te_bg, pos + offset, "blue")

    axs[1].set_ylim(0, 150)
    axs[1].set_ylabel("Te [eV]")
    axs[1].set_title("Electron temperature")
    axs[1].grid(True, axis="y")

    for ax in axs:
        ax.set_xticks(pos)
        ax.set_xticklabels([f"{z:.1f}" for z in z_vals])
        ax.set_xlabel("z [cm]")

    axs[0].plot([], [], color="red", label="with N₂")
    axs[0].plot([], [], color="blue", label="without N₂")
    axs[0].legend()

    plt.suptitle("Distributions vs z (red: N₂, blue: no N₂)", fontsize=14)
    plt.tight_layout(rect=(0, 0, 1, 0.97))
    plt.show()


def plot_boxplots_vs_z_nbi(df_2nbi, df_1nbi, z_vals):
    """
    Boxplots vs z for comparison of 2 NBI and 1 NBI regimes

    Parameters
    ----------
    df_2nbi : DataFrame
        Data for shots with 2 NBI (will be shown in red)
    df_1nbi : DataFrame
        Data for shots with 1 NBI (will be shown in blue)
    z_vals : array-like
        Sorted list of z positions
    """

    fig, axs = plt.subplots(1, 3, figsize=(12, 5), sharex=True)

    pos = np.arange(len(z_vals))
    offset = 0

    data_ne_2nbi = [df_2nbi[df_2nbi["z_cm"] == z]["ne_m3"].values for z in z_vals]
    data_ne_1nbi = [df_1nbi[df_1nbi["z_cm"] == z]["ne_m3"].values for z in z_vals]

    data_pe_2nbi = [df_2nbi[df_2nbi["z_cm"] == z]["p_e_Pa"].values for z in z_vals]
    data_pe_1nbi = [df_1nbi[df_1nbi["z_cm"] == z]["p_e_Pa"].values for z in z_vals]

    colored_boxplot(axs[2], data_pe_2nbi, pos - offset, "red")
    colored_boxplot(axs[2], data_pe_1nbi, pos + offset, "blue")

    colored_boxplot(axs[0], data_ne_2nbi, pos - offset, "red")
    colored_boxplot(axs[0], data_ne_1nbi, pos + offset, "blue")

    axs[0].set_ylim(0, 1e20)
    axs[0].set_ylabel("ne [m⁻³]")
    axs[0].set_title("Electron density")
    axs[0].grid(True, which="both", axis="y")

    data_Te_2nbi = [df_2nbi[df_2nbi["z_cm"] == z]["Te_eV"].values for z in z_vals]
    data_Te_1nbi = [df_1nbi[df_1nbi["z_cm"] == z]["Te_eV"].values for z in z_vals]

    colored_boxplot(axs[1], data_Te_2nbi, pos - offset, "red")
    colored_boxplot(axs[1], data_Te_1nbi, pos + offset, "blue")

    axs[1].set_ylim(0, 150)
    axs[1].set_ylabel("Te [eV]")
    axs[1].set_title("Electron temperature")
    axs[1].grid(True, axis="y")

    for ax in axs:
        ax.set_xticks(pos)
        ax.set_xticklabels([f"{z:.1f}" for z in z_vals])
        ax.set_xlabel("z [cm]")

    axs[0].plot([], [], color="red", label="2 NBI")
    axs[0].plot([], [], color="blue", label="1 NBI")
    axs[0].legend()

    plt.suptitle("Distributions vs z (red: 2 NBI, blue: 1 NBI)", fontsize=14)
    plt.tight_layout(rect=(0, 0, 1, 0.97))
    plt.show()


if __name__ == "__main__":
    df = load_and_prepare_data(TE_PATH, NE_PATH, time_ms=170, rel_error_filter=0.9)

    # nitrogen_shots = get_nitrogen_shots()
    one_nbi_shots = get_one_nbi_shots()
    two_nbi_shots = get_two_nbi_shots()
    two_nbi_shots_without_n = get_two_nbi_shots_without_n2()

    # df_n2, df_clear = split_by_nitrogen(df, nitrogen_shots)
    df_1nbi, _ = split_by_nbi(df, one_nbi_shots)
    df_2nbi, _ = split_by_2nbi(df, two_nbi_shots)
    df_2nbi_no_N2, _ = split_by_2nbi(df, two_nbi_shots_without_n)

    z_vals = sorted(df["z_cm"].unique())

    # plot_global_phase_space(df_clear, df_n2)
    # plot_local_phase_space_per_z(df, nitrogen_shots, z_vals)
    # plot_boxplots_vs_z(df_n2, df_clear, z_vals)
    plot_boxplots_vs_z_nbi(df_2nbi, df_2nbi_no_N2, z_vals)
