#!/usr/bin/env python
# coding: utf-8

# # About this code
#
# Compute the overlap betweeen the target groups and detected groups, where
# the target groups are those identified by Thomson Reuters and
# the detected groups are those detected by the algorithm.
#


import numpy as np
import sys
import pandas as pd
from scipy import sparse
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.colors as colors
from matplotlib import cm


def load_detected_cartels(years, cartel_dir):
    cartel_table_list = []
    group_id_offset = 0
    for year in years:
        cartel_table = pd.read_csv(
            "{root}/cartels-{year}.csv".format(root=cartel_dir, year=year), sep="\t"
        )
        cartel_table["year"] = year
        cartel_table["group_id"] += group_id_offset
        group_id_offset = np.max(cartel_table["group_id"].values) + 1
        cartel_table_list += [cartel_table]
    cartel_table = pd.concat(cartel_table_list, ignore_index=True)
    return cartel_table


def load_journal_groups_suspended_by_TR(filename):
    return pd.read_csv(filename, sep="\t")


def const_membership_matrix(T, node_id_col, membership_id_col, N):
    """
    Construct the membership matrix from pandas dataframe
    The matrix U[i,k] = 1 if node i belongs to the kth group. Otherwise U[i,k] = 0. 
    """
    node_id = T[node_id_col].values
    membership_id = T[membership_id_col].values
    return sparse.csc_matrix(
        (np.ones(len(node_id)), (node_id, membership_id)),
        shape=(N, np.max(membership_id) + 1),
    )


def add_id_column(Ta, Tb, node_id_col="mag_journal_id"):
    """
    Add a column ,_id, to two tables, Ta and Tb, 
    that indicates the id for the union of the node_id_col columns for Ta and Tb
    """
    # Find all the set of nodes in the table
    nodes = np.unique(Ta[node_id_col].values.tolist() + Tb[node_id_col].values.tolist())
    N = nodes.size  # number of nodes
    node2id = {x: i for i, x in enumerate(nodes)}  # node label to integer id

    # convert node label to node ids
    Ta["_id"] = Ta[node_id_col].apply(lambda x: node2id[x])
    Tb["_id"] = Tb[node_id_col].apply(lambda x: node2id[x])
    return Ta, Tb, N


def calc_overlap(U_a, U_b, min_intersection=2):
    """
    Calculate the overlap between the memberships, Ua and Ub, where
    Ua and Ub are membership matrices given by const_membership_matrix func
    """

    # Compute the intersection and the union of the detected and target groups
    Intersection = (U_a.T @ U_b).toarray()

    # Set Intersection to 0 if only one node is shared
    Intersection[Intersection < min_intersection] = 0

    sz_b = np.array(U_b.sum(axis=0)).reshape(-1)
    S = Intersection @ np.diag(1.0 / sz_b)
    return S


def slice_groups(T, group_ids, group_id_col):
    s = T[group_id_col].apply(lambda x: x in group_ids).values
    return T[s]


def make_color_map(dw, min_w, max_w):
    disc_min_w = dw * np.floor(min_w / dw)
    disc_max_w = dw * np.ceil(max_w / dw)
    bounds = np.linspace(
        disc_min_w, disc_max_w, np.round((disc_max_w - disc_min_w) / dw).astype(int) + 1
    )
    norm = colors.BoundaryNorm(boundaries=bounds, ncolors=256)
    cmap = cm.get_cmap("viridis")
    return cmap, norm


if __name__ == "__main__":

    CARTEL_DIR = sys.argv[1]
    TR_GROUP_FILE = sys.argv[2]
    OUTPUT = sys.argv[3]

    detection_threshold = 0.4  # minimum overlap score at which we regard detected

    # Load the data
    groups_CI = load_detected_cartels(np.arange(2000, 2020), CARTEL_DIR)

    groups_TR = load_journal_groups_suspended_by_TR(TR_GROUP_FILE)

    # Assgin a new id for the mag_journal_id
    groups_CI, groups_TR, N = add_id_column(groups_CI, groups_TR, "mag_journal_id")

    # Construct the membership matrix
    U_CI = const_membership_matrix(
        groups_CI, node_id_col="_id", membership_id_col="group_id", N=N
    )
    U_TR = const_membership_matrix(
        groups_TR, node_id_col="_id", membership_id_col="group_id", N=N
    )

    # Compute the overlap
    O = calc_overlap(U_TR, U_CI)
    O[O < detection_threshold] = 0

    # Detected group pairs
    gid_TR, gid_CI, o = sparse.find(O)
    detected_groups = slice_groups(groups_CI, gid_CI, "group_id")

    d1 = dict(zip(gid_CI, gid_TR))
    d2 = dict(zip(gid_CI, o))
    detected_groups["overlap"] = detected_groups["group_id"].apply(
        lambda x: d2.get(x, -1)
    )
    detected_groups["group_id_TR"] = detected_groups["group_id"].apply(
        lambda x: d1.get(x, -1)
    )

    # Make a colormap
    cmap, norm = make_color_map(0.2, 0.4, 1)

    # Plot parameters
    plot_TR_params = {
        "marker": "x",
        "color": "black",
        "edgecolor": "black",
        "linewidth": 1.5,
        "s": 110,
        "zorder": 5,
        "label": "Thomson Reuters",
    }

    plot_CI_params = {
        "hue": "overlap",
        "edgecolor": "black",
        "palette": "viridis",
        "vmin": 0,
        "vmax": 1,
        "hue_norm": norm,
        "linewidth": 1.2,
        "label": "Proposed",
        "s": 130,
        "zorder": 2,
    }

    # Set up the canvas
    sns.set(font_scale=1.3)
    sns.set_style("white")
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot the points
    ax = sns.scatterplot(
        data=detected_groups[["year", "group_id_TR", "overlap"]].drop_duplicates(),
        x="year",
        y="group_id_TR",
        **plot_CI_params,
        ax=ax,
    )

    sns.scatterplot(
        data=groups_TR[["year", "group_id"]].drop_duplicates(),
        x="year",
        y="group_id",
        **plot_TR_params,
        ax=ax,
    )

    # Colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = ax.figure.colorbar(sm)
    cbar.ax.set_title("Overlap", pad=20)

    # X and Y labels
    ax.set_ylabel("ID of the group suspended by Thomson Reuters, $\ell$")
    ax.set_xlabel("Year")

    # Legends
    ax.scatter(
        [1990],
        [0],
        label="Number of within-group citations without self-citations",
        color="#c5c5c5",
        edgecolor="black",
        s=150,
        marker="s",
    )
    ax.scatter(
        [1990], [1], label="CIDRE", color="grey", edgecolor="black", s=150, marker="o"
    )

    handles, labels = ax.get_legend_handles_labels()
    order = np.array([6, 8, 7])
    handles = [handles[i] for i in order]
    labels = [labels[i] for i in order]
    leg1 = ax.legend(
        handles[:2],
        labels[:2],
        frameon=False,
        loc="center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=2,
    )
    ax.add_artist(leg1)

    # Range
    xticks = np.arange(2006, 2019)
    ax.set_xlim(2006, 2018.5)
    plt.xticks(np.arange(2006, 2019), ["`%02d" % d for d in xticks - 2000])
    plt.yticks(np.arange(0, 23), np.arange(1, 23))

    # Save figure
    fig.savefig(OUTPUT, bbox_inches="tight", dpi=300)
