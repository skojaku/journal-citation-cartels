import pandas as pd
import sys
import utils

PAPER_COUNT_FILE = sys.argv[1]

if __name__ == "__main__":

    # connect to the database
    graph = utils.get_db()

    # Compute the paper count first
    #TODO Switch to correct
    query = """ 
    MATCH (j:Journal)<-[:published_from]-(p)
    return ID(j) as id, count(p) as pcount, p.Year as year
    """
    df = graph.run(query).to_data_frame()

    df.to_csv(PAPER_COUNT_FILE, sep="\t")
