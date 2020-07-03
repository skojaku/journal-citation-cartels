import numpy as np
import pandas as pd
import os
import sys
import utils

n = len(sys.argv) -1

OUTPUT_EDGE_FILE = sys.argv.pop()
OUTPUT_NODE_FILE = sys.argv.pop()

n_2, _ = divmod(n-2,  2)
NODE_FILES = sys.argv[:n_2]
EDGE_FILES = sys.argv[n_2:]

if __name__ == "__main__":

    # connect to the database
    graph = utils.get_db()

    node_list = []
    edge_list = []
    for i in enumerate(NODE_FILES)
        nodes = pd.read_csv(NODE_FILES[i], sep = "\t")
        edges = pd.read_csv(EDGE_FILES[i], sep = "\t")
        node_list += [nodes]
        edge_list += [edges]

    nodes = pd.concat(node_list, ignore_index=True)
    edges = pd.concat(edge_list, ignore_index=True)

    edges = edges.groupby(["source", "target"]).agg("w").sum().reset_index()
    nodes.to_csv(OUTPUT_NODE_FILE, sep="\t")
    edges.to_csv(OUTPUT_EDGE_FILE, sep="\t")
