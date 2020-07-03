import numpy as np
import pandas as pd
import py2neo
import sys
from scipy import sparse

# connect to the database
if __name__ == "__main__":

    outputfile = sys.argv[1]

    username = "neo4j"
    password = "FSailing4046"
    uri = "bolt://127.0.0.1:7687"
    graph = py2neo.Graph(bolt=True, host="localhost", user=username, password=password)
    query = """ 
    MATCH (j:Journal)<-[:published_from]-(p)
    return ID(j) as id, count(p) as pcount, p.Year as year
    """
    pcount = graph.run(query).to_data_frame()
    pcount.to_csv(outputfile, sep="\t")
    #with open("data/networks/pcount.pickle", "wb") as f:
    #    pickle.dump(pcount, f)
