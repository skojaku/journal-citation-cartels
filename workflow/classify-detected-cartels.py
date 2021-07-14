#!/usr/bin/env python
# coding: utf-8
import warnings

warnings.simplefilter(action="ignore")
import sys
import pandas as pd
import numpy as np
from scipy import sparse
import utils
import json
import py2neo


def count_citations_papers_within_group(journal_ids, year):

    journals = ",".join(["'%d'" % c for c in journal_ids])
    query = """
        match (jsrc:Journal)-[:published_from]-(psrc:Paper)-[r:cites]->(ptrg:Paper)-[:published_from]-(jtrg:Journal)
        where 
            jsrc.JournalId in [{journals}] and 
            jtrg.JournalId in [{journals}] and 
            psrc.Year = {yf} and 
            not ID(jsrc) = ID(jtrg) and
            {ys}<=ptrg.Year and ptrg.Year<{yf}
        return 
            ID(psrc) as source, 
            ID(ptrg) as target,
            jsrc.JournalId as s_journal, 
            jtrg.JournalId as t_journal
    """.format(
        journals=journals, ys=year - 2, yf=year
    )
    citations = graph.run(query).to_data_frame()
    w_out = citations.groupby("source").size().values
    w_in = citations.groupby("target").size().values
    return w_out, w_in


def count_citations_authors_within_group(journal_ids, year):

    journals = ",".join(["'%d'" % c for c in journal_ids])
    query = """
        match (jsrc:Journal)-[:published_from]-(psrc:Paper)-[r:cites]->(ptrg:Paper)-[:published_from]-(jtrg:Journal)
        match (a:Author)-[:written_by]-(ptrg:Paper)
        where 
            jsrc.JournalId in [{journals}] and 
            jtrg.JournalId in [{journals}] and 
            psrc.Year = {yf} and 
            not ID(jsrc) = ID(jtrg) and
            {ys}<=ptrg.Year and ptrg.Year<{yf}
        return
            distinct ID(a) as author_id, count(distinct r) as w order by w desc
    """.format(
        journals=journals, ys=year - 2, yf=year
    )
    citations_in = graph.run(query).to_data_frame()

    query = """
        match (jsrc:Journal)-[:published_from]-(psrc:Paper)-[r:cites]->(ptrg:Paper)-[:published_from]-(jtrg:Journal)
        match (a:Author)-[:written_by]-(psrc:Paper)
        where 
            jsrc.JournalId in [{journals}] and 
            jtrg.JournalId in [{journals}] and 
            psrc.Year = {yf} and 
            not ID(jsrc) = ID(jtrg) and
            {ys}<=ptrg.Year and ptrg.Year<{yf}
        return  
            distinct ID(a) as author_id, count(distinct r) as w order by w desc
    """.format(
        journals=journals, ys=year - 2, yf=year
    )
    citations_out = graph.run(query).to_data_frame()
    return citations_out["w"].values, citations_in["w"].values


if __name__ == "__main__":

    NET_DIR = sys.argv[1]  # "../../data/networks"
    TR_DETECTED_FILE = sys.argv[
        2
    ]  # "../../data/ThomsonReuters/journal-groups-suspended-by-TR.csv"
    CI_DETECTED_DIR = sys.argv[3]  # "../../data/cartels"
    CLASSIFIED_RESULT = sys.argv[4]  # "classified_results.csv"
    SAMPLED_CAETELS_FILE = sys.argv[5]  # "sampled_"

    th = 0.3  # Fraction of citations above which we regard excessive concentration
    years = np.arange(2010, 2020)  # Years for the detected cartels

    # Connect to the database
    graph = utils.get_db()

    # Load the networks
    A_list = {}
    node_list = {}
    for year in years:
        A, _, nodes = utils.load_network(year, NET_DIR)
        A_list[year] = A
        node_list[year] = nodes

    groups_TR = pd.read_csv(TR_DETECTED_FILE, sep="\t")
    groups_CI = utils.load_detected_cartels(years, CI_DETECTED_DIR)

    # Remove groups that contain at least one suspended journal
    suspended_journals = np.unique(groups_TR["mag_journal_id"].values)
    contained = [
        gid
        for gid, dg in groups_CI.groupby("gross_group_id")
        if ~np.any(np.isin(dg["mag_journal_id"], suspended_journals))
    ]
    unsuspended_groups_CI = utils.slice_groups(groups_CI, contained, "gross_group_id")

    # Compute the fraction of citations at author and paper levels
    cit_concentration = []
    N = unsuspended_groups_CI["gross_group_id"].max() + 1
    for (year, gid), cartel in unsuspended_groups_CI.groupby(
        ["year", "gross_group_id"]
    ):

        A = A_list[year]
        journal_ids = node_list[year]

        nodes = cartel.node_id.values
        As = A[:, nodes][nodes, :].toarray()
        As = As - np.diag(np.diag(As))

        # Count the number of citations that each paper and author
        # recieves and provides citations within the groups
        p_out, p_in = count_citations_papers_within_group(journal_ids[nodes], year)
        a_out, a_in = count_citations_authors_within_group(journal_ids[nodes], year)

        # Compute the fraction of citations within the group
        p_in = np.max(p_in / np.sum(As))
        p_out = np.max(p_out / np.sum(As))

        a_in = np.max(a_in / np.sum(As))
        a_out = np.max(a_out / np.sum(As))

        cit_concentration += [
            {
                "p_out": p_out,
                "p_in": p_in,
                "a_in": a_in,
                "a_out": a_out,
                "year": year,
                "gid": gid,
                "num_edges": np.sum(As),
            }
        ]

    # Classify the detected groups
    def classify(row, th):
        if row["p_out"] >= th:
            return "out-paper-exclusive (a)"
        elif row["p_in"] >= th:
            return "in-paper-exclusive (b)"
        elif row["a_out"] >= th:
            return "out_author_exclusive (c)"
        elif row["a_in"] >= th:
            return "in-author_exclusive (d)"
        else:
            return "others (e)"

    df = pd.DataFrame(cit_concentration)
    df["type"] = df.apply(lambda x: classify(x, th), axis=1)
    df_before_2019 = df[df.year < 2019]

    # Save the classification to a file
    df_before_2019.groupby("type").size().reset_index().to_csv(
        CLASSIFIED_RESULT, sep="\t"
    )

    # Sample one cartel for each type that contains the largest number
    # of within-group citations in the type
    sampled_cartels = []
    for i, dg in df_before_2019.groupby("type"):
        row = dg.sort_values(by="num_edges", ascending=False).head(1)
        gross_group_id = row["gid"].values[0]
        year = row["year"].values[0]
        journal_ids = groups_CI[groups_CI.gross_group_id == gross_group_id][
            "mag_journal_id"
        ].values
        group_id = groups_CI[groups_CI.gross_group_id == gross_group_id][
            "group_id"
        ].values[0]
        sampled_cartels += [{"type": i, "group_id": group_id, "year": year}]

    # Save them to a file
    pd.DataFrame(sampled_cartels).to_csv(SAMPLED_CAETELS_FILE, sep="\t")
