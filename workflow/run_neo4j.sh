#=============================================
# Configuration 
#=============================================
docker_container_name=$1
database_dir=$2
cleaned_data_dir=$3

#=============================================
# Lunch the neo4j database 
#=============================================

docker run \
    --name $docker_container_name \
    -d \
    -p 7474:7474 -p 7687:7687 \
    -v $database_dir:/var/lib/neo4j/data \
    -v $cleaned_data_dir:/import \
    -v /etc/group:/etc/group:ro \
    -v /etc/passwd:/etc/passwd:ro \
    -u $(id -u $USER):$(id -g $USER) \
    --env NEO4J_AUTH=neo4j/dolphinsNeverSleep \
    --env NEO4J_dbms_default__database=graph.db \
    neo4j:4.0
