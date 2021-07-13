#=============================================
# Configuration 
#=============================================

source_data_dir=$1
cleaned_data_dir=$2

#=============================================
# Initialize
#=============================================

# If this is a fresh file
#
# Escape the quotes
#
dos2unix $source_data_dir/*.txt

rm -r $cleaned_data_dir 
mkdir $cleaned_data_dir


#=============================================
# Note:
# Column numbers can be found in the mag data schema
# https://docs.microsoft.com/en-us/academic-services/graph/reference-data-schema
#=============================================

# TODO Need to run one of these for chosen area. But weird syntax
{ echo -e "AuthorId:ID(Author-ID)\tNormalizedName\tDisplayName";cut -f 1,3,4 $source_data_dir/Authors.txt; } >$cleaned_data_dir/Authors.txt

{ echo -e "PaperId:ID(Paper-ID)\tDoi\tDocType\tPaperTitle\tYear:INT\tJournalId\tConferenceSeriesId";cut -f 1,3,4,5,8,11,12 $source_data_dir/Papers.txt; } >$cleaned_data_dir/Papers.txt

{ echo -e "ConferenceSeriesId:ID(Conference-ID)\tNormalizedName";cut -f 1,3 $source_data_dir/ConferenceSeries.txt; } >$cleaned_data_dir/ConferenceSeries.txt

{ echo -e "JournalId:ID(Journal-ID)\tNormalizedName\t";cut -f 1,3 $source_data_dir/Journals.txt; } >$cleaned_data_dir/Journals.txt

{ echo -e "ConferenceSeriesId:ID(Conference-ID)\tNormalizedName";cut -f 1,3 $source_data_dir/ConferenceSeries.txt; } >$cleaned_data_dir/ConferenceSeries.txt

{ echo -e ":START_ID(Paper-ID)\t:END_ID(Paper-ID)";cat $source_data_dir/PaperReferences.txt; } >$cleaned_data_dir/PaperReferences.txt

{ echo -e ":START_ID(Paper-ID)\t:END_ID(Author-ID)";cut -f 1,2 $source_data_dir/PaperAuthorAffiliations.txt; } >$cleaned_data_dir/PaperAuthorAffiliations.txt

{ echo -e ":START_ID(Paper-ID)\t:END_ID(Journal-ID)";cut -f 1,11 $source_data_dir/Papers.txt; } | awk -F"\t" '{if($2!="")print $0}' >$cleaned_data_dir/PaperJournalAffiliations.txt

#
# Escape the quotes
#
for file in $cleaned_data_dir/*.txt
do
	sed -i "s/\"/\\\\\"/g;s/'/\\\'/g" $file
done
