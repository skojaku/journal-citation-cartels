import numpy as np
import pandas as pd
import py2neo 
import pickle
import os,sys
from scipy import sparse

if __name__ == "__main__":

    INPUT_FILES = sys.argv[:-1]
    OUTPUT_FILE = sys.argv[-1]

    # connect to the database
    username = "neo4j"
    password = "FSailing4046"
    uri = "bolt://127.0.0.1:7687"
    graph = py2neo.Graph(bolt=True, host='localhost', user=username, password=password)
    
    
    node_list = []
    edge_list = []
    for filename in INPUT_FILES:
    
        with open(filename, "rb") as f:
            res = pickle.load(f)
        nodes = res["nodes"]
        edges = res["edges"]
    
        node_list+=[nodes]
        edge_list+=[edges]
    
    nodes = pd.concat( node_list, ignore_index = True )
    nodes =  nodes.groupby(["id"]).sum().reset_index()
    
    edges = pd.concat( edge_list, ignore_index = True )
    edges = edges.groupby(["source", "target"]).agg("w").sum().reset_index()
    
    with open(OUTPUT_FILE, "wb") as f:
        pickle.dump({"nodes":nodes, "edges":edges}, f)
