##=============================================
## Configuration 
##=============================================
database_dir=$1
cleaned_data_dir=$2
conf_dir=$3
docker_container_name=$4
#docker_container_name="magdb"
#
#
rm -r $database_dir
mkdir $database_dir
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
    neo4j:4.0

sleep 10 # Wait a bit because the neo4j may not be ready immediately 

#====================================
# Import the data into neo4j database
#docker exec -it $docker_container_name bash -c '
#====================================
docker exec $docker_container_name bash -c '
neo4j-admin import --database=graph.db --trim-strings=true --nodes Author=/import/Authors.txt --nodes Paper=/import/Papers.txt --nodes Journal=/import/Journals.txt --nodes ConferenceSeries=/import/ConferenceSeries.txt --relationships cites=/import/PaperReferences.txt --relationships written_by=/import/PaperAuthorAffiliations.txt --relationships published_from=/import/PaperJournalAffiliations.txt --delimiter="\t";
exit
'

#docker restart $docker_container_name 
docker stop $docker_container_name && docker rm $docker_container_name 
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

sleep 10 # Wait a bit because the neo4j may not be ready immediately 

#====================================
# Add indexes to the database 
#====================================
docker exec $docker_container_name bash -c '
echo "
CREATE INDEX ON :Author(AuthorId);
CREATE INDEX ON :Author(NormalizedName);
CREATE INDEX ON :Journal(JournalId);
CREATE INDEX ON :Journal(NormalizedName);
CREATE INDEX ON :Affiliation(AffiliationId);
CREATE INDEX ON :Affiliation(NormalizedName);
CREATE INDEX ON :Paper(Doi);
CREATE INDEX ON :Paper(NormalizedName);
CREATE INDEX ON :Paper(PaperId);
CREATE INDEX ON :Paper(Year);
"| cypher-shell -u neo4j -p dolphinsNeverSleep
'

sleep 600 # Wait a bit until indexing complete 
