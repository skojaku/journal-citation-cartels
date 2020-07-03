# Python code for the CIDRE algorithm

- `workflow` contains all python and bash scripts used in the `snakemake` (a python version of make)
- `paper` contains the latex files for the manuscript. 
- `notebooks` contains the Jupyter notebooks
- `libs` contains the library including the CIDRE algorithm.

## Requirement

```
networkx          2.4
numpy             1.18
pandas            1.0.5
scipy             1.5.0
```

## Installation

    conda env create -f libs/cidre/cidre.yml

## How to use

Import the library:

```python
    import sys,os
    sys.path.append(os.path.abspath(os.path.join("<path to `libs`>/cidre")))
    from cidre import cidre, filters
```
(Set a path to `libs/cidre` directory.)

Define a filtering function:
```python
    is_excessive_func = filters.get_dcsbm_threshold_filter(
        W, W_threshold, community_ids
    )
````
    
where `W` is the weighted adjacency matrix (scipy.sparse matrix), `W_threshold` is the threshold for the weight of edges, and 
`community_ids` (numpy.ndarray) takes entry `community_ids[i]` indicating the group membership of node `i`. This package contains three built-in filtering functions. See libs/cidre/cidre/filters.py.

Run the CIDRE algorithm:

```python
    citation_group_table = cidre.detect(W, theta, is_excessive_func)
```

where `theta` is the resolution parameter that determines the size and the number of groups. `citation_group_table` is the pandas data frame composed of the following columns:
- node_labels : label of nodes                                                               
- group id : ID of the group to which the node belongs                                       
- donor_score : donor score for the node                                                     
- recipient_score : recipient score for the node                                             
- is_donor : True if the node is a donor. Otherwise False.                                   
- is_recipient : True if the node is a recipient. Otherwise False.

Visualize the detected cartels:

```python
import matplotlib.pyplot as plt
from cidre import draw

# Load the class for drawing a cartel
dc = draw.DrawCartel()

for cid, cartel in citation_group_table.groupby("group_id"):
    dc.draw(
        W,
        cartel.node_id.values.tolist(),
        cartel.donor_score.values.tolist(),
        cartel.recipient_score.values.tolist(),
        theta,
        cartel.name.values.tolist(),
        ax=ax,
    )
    plt.show()
```


## Minimum example

```python 
import networkx as nx
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
sys.path.append(os.path.abspath(os.path.join("libs/cidre")))
from cidre import cidre, filters, draw

# Threshold
theta = 0.15

# Gnerate the test network.
net = nx.karate_club_graph()
W = nx.adjacency_matrix(net)
W.data = np.random.poisson(10, W.data.size)
W_threshold = W.copy()
W_threshold.data = np.random.poisson(15, W_threshold.data.size)

# Generate random community memberships
community_ids = np.random.choice(2, W.shape[0], replace=True).astype(int)

# Define the filtering function
is_excessive_func = filters.get_dcsbm_threshold_filter(W, W_threshold, community_ids)

# Detect the cartel groups
citation_group_table = cidre.detect(W, theta, is_excessive_func)
print(citation_group_table)

# Load the class for drawing a cartel
dc = draw.DrawCartel()

# Set up the canvas
fig, axes = plt.subplots(figsize=(10,10))
sns.set_style("white")
sns.set(font_scale = 1.2)
sns.set_style("ticks")

# Set the name of each node
citation_group_table["name"] = citation_group_table["node_id"].apply(lambda x : str(x))

for cid, cartel in citation_group_table.groupby("group_id"):
    dc.draw(
        W,
        cartel.node_id.values.tolist(),
        cartel.donor_score.values.tolist(),
        cartel.recipient_score.values.tolist(),
        theta,
        cartel.name.values.tolist(),
        ax=axes,
    )
    plt.show()
```

# Reproducing the results

We provide a Snakemake file to reproduce the results from the raw data (Microsoft Academic Graph). The workflow consists of the following steps:

1. Download the [Microsoft Academic Graph](https://docs.microsoft.com/en-us/academic-services/graph/reference-data-schema)
2. Import the data into [Neo4j database](https://neo4j.com/)
3. Generate files for journal citation networks 
4. Detect communities in an aggregated network
5. Detect the suspect of citation cartels in each yearly network
6. Analyze the results and generate figures

## Set up

### Conda

Install `conda` https://docs.conda.io/projects/conda/en/latest/index.html

### Snakemake

Install `snakemake` for workflow management.

    conda install ipykernel
    conda install -c bioconda -c conda-forge snakemake
 
### Docker

Install docker in your environment. Allow the snakemake to launch a new container called "magdb" without sudo.

### Path

Create a config.yaml file under the workflow. Write

    data_dir: "data"
    fig_dir: "figs"
    container_key: "<container key>"

where container key is the key for the Azure blob container that stores the Microsoft Academic Graph.

## Run Snakemake

Run the snakamke by 

    snakamake --cores 12 

## Visualize the workflow

Run 

    snakemake --dag | dot -Tpdf > dag.pdf    

and open dag.pdf
