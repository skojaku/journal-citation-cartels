import numpy as np
import pandas as pd
import os
import sys
from scipy import sparse
import utils
from http.client import IncompleteRead

PAPER_COUNT_FILE = sys.argv[1]
YEAR = int(sys.argv[3])
WINDOW_LENGTH = int(sys.argv[4])
OUTPUT_NODE_FILE = sys.argv[5]
OUTPUT_EDGE_FILE = sys.argv[6]
year = YEAR

if __name__ == "__main__":

    # Connect to the database
    graph = utils.get_db()

    # Load the paper count
    pcount = pd.read_csv(PAPER_COUNT_FILE, sep="\t")
    print("Read csv")

    # Count the number of papers for each Affiliation
    ys = YEAR - WINDOW_LENGTH
    yf = YEAR
    field = "computer science"
    query = """
    MATCH (ftrg:FieldsOfStudy)<-[:field_of_study]-(trg:Paper)<-[:cites]-(src:Paper {Year:%d})-[:field_of_study]->(fsrc:FieldsOfStudy)
    WHERE trg.Year<%d and trg.Year >= %d and ftrg.NormalizedName=%s and fsrc.NormalizedName=%s
    WITH src, trg, ftrg, fsrc
    MATCH (src)-[:published_from]->(jsrc:Affiliations)
    MATCH (jtrg:Affiliations)<-[:published_from]-(trg)
    return DISTINCT toInteger(jsrc.AffiliationId) as source, toInteger(jtrg.AffiliationId) as target, toInteger(trg.PaperId) as p_target, toInteger(src.PaperId) as s_target
    LIMIT 1000
    """ % (
        yf,
        yf,
        ys,
        field,
        field,
    )

    edges = graph.run(query).to_data_frame()

 

    # print(query, edges)
    print("Done with query")

    # Make a node table
    ccount = edges.groupby(["target"])["s_target"].nunique()
    nodes = pd.DataFrame({"ccount": ccount})
    nodes = nodes.reset_index().rename(columns={"target": "id"})
    print("Made node table")

    # Slice the paper counts between ys and yf
    s = (ys <= pcount.year) & (pcount.year < yf)
    _pcount = pcount[s].copy()
    _pcount = _pcount.groupby("id").agg("sum")["pcount"].reset_index()
    print("Sliced paper")

    # Merge the pcount to the node table
    nodes = pd.merge(left=nodes, right=_pcount, left_on="id", right_on="id", how="left")

    # Uniqify and count
    edges = edges.groupby(["source", "target"]).size().reset_index(name="w")
    print("Unified edges")
    # # Add citations from retracted papers 
    # #Probably not going to bother with? 
    # if year == 2010 or year == 2011:
    #     if year == 2010:
    #         added_edges = [
    #             ["medical science monitor", "cell transplantation", 445],
    #             ["the scientific world journal", "cell transplantation", 96],
    #             ["medical science monitor", "medical science monitor", 44],
    #             ["the scientific world journal", "the scientific world journal", 26],
    #         ]
    #     elif year == 2011:
    #         added_edges = [
    #             ["medical science monitor", "cell transplantation", 87],
    #             ["medical science monitor", "medical science monitor", 32],
    #             ["the scientific world journal", "cell transplantation", 109],
    #             ["the scientific world journal", "the scientific world journal", 29],
    #             ["cell transplantation", "technology and innovation", 24],
    #         ]

    #     journal_list = list(
    #         set([x[0] for x in added_edges] + [x[1] for x in added_edges])
    #     )
    #     query = """
    #     MATCH (n:Journal)
    #     WHERE n.NormalizedName in [{journals}]
    #     return toInteger(n.JournalId) as id, n.NormalizedName as name 
    #     """.format(
    #         journals=",".join(["'%s'" % x for x in journal_list])
    #     )
    #     node_table = graph.run(query).to_data_frame()

    #     name2id = {x["name"]: x["id"] for i, x in node_table.iterrows()}
    #     edge_list = [
    #         {"source": name2id[x[0]], "target": name2id[x[1]], "w": x[2]}
    #         for x in added_edges
    #     ]
    #     added_edges = pd.DataFrame(edge_list)
    #     edges = pd.concat([edges, added_edges], ignore_index=True)

    # Save to the result
    nodes.to_csv(OUTPUT_NODE_FILE, sep="\t")
    edges.to_csv(OUTPUT_EDGE_FILE, sep="\t")
