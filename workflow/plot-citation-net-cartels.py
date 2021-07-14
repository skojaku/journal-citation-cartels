#!/usr/bin/env python
# coding: utf-8

import warnings

warnings.simplefilter(action="ignore")
import pandas as pd
import numpy as np
from scipy import sparse
import seaborn as sns
import matplotlib.pyplot as plt
import pickle
import textwrap
import re
import sys, os
import utils

sys.path.append(os.path.abspath(os.path.join("libs/cidre")))
from cidre import draw

sys.path.append(os.path.abspath(os.path.join("libs/iso4")))
from iso4 import abbreviate
import nltk

nltk.download("wordnet")


def load_sampled_cartel(net_data_dir, cartel_dir, sampled_cartel_file):
    # Load journal names
    journal_names = pd.read_csv("%s/journal_names.csv" % net_data_dir, sep="\t")

    # Load the cartels in each category
    df_sampled = pd.read_csv(sampled_cartel_file, sep="\t")
    df_2019 = utils.load_detected_cartels([2019], cartel_dir)

    sampled_cartel = []
    sampled_cartel = [(r["group_id"], r["year"]) for i, r in df_sampled.iterrows()]
    sampled_cartel += [(r["group_id"], r["year"]) for i, r in df_2019.iterrows()]

    retval = []

    for _, row in df_sampled.iterrows():

        group_id = row["group_id"]
        year = row["year"]

        cartel = utils.load_detected_cartels([year], cartel_dir)
        cartel = cartel[cartel.group_id == group_id]
        A, Araw, nodes = utils.load_network(year, net_data_dir)

        cartel = pd.merge(
            cartel,
            journal_names,
            left_on="mag_journal_id",
            right_on="mag_journal_id",
            how="left",
        )
        retval += [{"cartel": cartel, "A": A}]

    # Load the cartels that are detected in 2019
    year = 2019
    cartel_table = utils.load_detected_cartels([year], cartel_dir)
    A, Araw, nodes = utils.load_network(year, net_data_dir)

    # Compute the recipient score using the general citations
    for cid, cartel in cartel_table.groupby("group_id"):
        cartel = pd.merge(
            cartel,
            journal_names,
            left_on="mag_journal_id",
            right_on="mag_journal_id",
            how="left",
        )
        retval += [{"cartel": cartel, "A": A}]

    return retval


if __name__ == "__main__":
    NET_DATA_DIR = sys.argv[1]  # "../../data/networks"
    CARTEL_DIR = sys.argv[2]  # "../../data/cartels"
    SAMPLED_CARTEL_FILE = sys.argv[
        3
    ]  # "../../data/classified-cartels/case-study-cartels.csv"
    OUTPUT = sys.argv[4]

    cartel_list = load_sampled_cartel(NET_DATA_DIR, CARTEL_DIR, SAMPLED_CARTEL_FILE)

    alias_name = {
        "acta crystallographica section c crystal structure communications": "acta crystallographica section c",
        "acta crystallographica section b structural crystallography and crystal chemistry": "acta crystallographica section b",
    }

    preset_name = {
        "iucrdata": "IUCrData",
        "acta crystallographica section e crystallographic communications": "Acta Crystallogr. Sect. E",
    }

    def abbreviate_journal_title(title):
        # Abbreviation of journal titles according to NLM
        # See http://wayback.archive-it.org/org-350/20130705122245/http://www.nlm.nih.gov/pubs/factsheets/constructitle.html
        abbrev_title = abbreviate(title)

        if title in preset_name.keys():
            abbrev_title = preset_name[title]
        else:
            title = alias_name.get(title, title)
            abbrev_title = abbreviate(title)
            abbrev_title = re.sub(
                "(?<=^)[a-z]|(?<=\s)[a-z]", "{}", abbrev_title
            ).format(
                *map(str.upper, re.findall("(?<=^)[a-z]|(?<=\s)[a-z]", abbrev_title))
            )
        abbrev_title = re.sub(" +", " ", abbrev_title)
        return abbrev_title

    # Load the class for drawing a cartel
    dc = draw.DrawCartel()

    # Fine tune the plot
    dc.node_size = 0.15
    dc.font_scale = 1.2
    dc.theta_1 = np.pi * 0.7
    dc.angle_margin = 2 * np.pi / 30
    dc.label_width = 15
    dc.max_label_width = 18
    sns.set_style("white")
    sns.set_style("ticks")

    # Order of which we draw the figure
    order = [3, 1, 4, 0, 2, 5, 7, 10, 6, 9, 8, 11]
    threshold = 0.15

    figid = 0
    fig, axes = plt.subplots(nrows=3, ncols=4, figsize=(40, 24))
    subcap = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "$\ell$"]

    for cid, cartel_A in enumerate([cartel_list[i] for i in order]):
        cartel = cartel_A["cartel"]
        A = cartel_A["A"]

        ax = axes.flat[figid]
        figid += 1

        # Abbreviate the journal names
        cartel["name"] = cartel["name"].apply(lambda x: abbreviate_journal_title(x))

        # Sort the cartels based on the lebgth of the abbreviated names
        cartel["char_num"] = cartel["name"].apply(lambda x: len(x))
        cartel = cartel.sort_values(by="char_num", ascending=False)

        # File tune the drawing parameter
        # based on the size of cartels
        if cartel.shape[0] > 20:
            dc.node_size = 0.08
            dc.font_scale = 0.95
            dc.label_node_margin = 0.4  # 0.3
        else:
            dc.font_scale = 1.2
            dc.node_size = 0.15
            dc.label_node_margin = 0.45  # 0.31

        dc.draw(
            A,
            cartel.node_id.values.tolist(),
            cartel.donor_score.values.tolist(),
            cartel.recipient_score.values.tolist(),
            threshold,
            cartel.name.values.tolist(),
            ax=ax,
        )
        ax.text(
            0.01,
            1.05,
            "({alph}) Group {id}".format(alph=subcap[figid - 1], id=figid),
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=25,
        )

    # Manual Trim
    box = axes[0, 2].get_position()
    box.x0 = box.x0 + 0.01
    box.x1 = box.x1 + 0.01
    axes[0, 2].set_position(box)
    box = axes[1, 2].get_position()
    box.x0 = box.x0 - 0.0
    box.x1 = box.x1 - 0.0
    axes[1, 2].set_position(box)

    fig.savefig(OUTPUT, bbox_inches="tight")
