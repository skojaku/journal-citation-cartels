#
# Download the data stored in Azure account to local
#
# python3 main.py [path to the dir for the data]
#
import os, uuid
from azure.storage.blob import BlockBlobService
from joblib import Parallel, delayed
from time import time

# Configuration =================

# String required to authenticate the access
# See
# https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python#download-blobs
connect_str = "DefaultEndpointsProtocol=https;AccountName=magdb;AccountKey=utIvM90o55boj2A/NoqL8aciy/C3jcRsUmF1zgRCqzbX4kH/UV4aNXQYf9ojkslZcivj66gvOK7T3Bc7pTzXqA==;EndpointSuffix=core.windows.net"


if __name__ == "__main__":

    # Download folder
    datadir = sys.argv[1] 

    if os.path.exists(datadir) == False:
        os.mkdir(datadir)

    #
    # Key
    #
    blob_service_client = BlockBlobService(connection_string=connect_str)

    #
    # BlobServiceClient -> Container_client -> Blob_client -> Download the file and save it
    #
    filenames = [
        "Affiliations.txt",
        "Journals.txt",
        "ConferenceInstances.txt",
        "ConferenceSeries.txt",
        "Authors.txt",
        "PaperAuthorAffiliations.txt",
        "PaperExtendedAttributes.txt",
        "PaperReferences.txt",
        "PaperResources.txt",
        "Papers.txt",
        "PaperUrls.txt",
    ]

    all_containers = blob_service_client.list_containers(include_metadata=True)
    all_containers = list(all_containers)
    all_containers.sort(key=lambda x: x.properties.last_modified)

    container_name = all_containers[-1].name

    def process(datadir, filename, container_name):
        fullpath = "%s/%s" % (datadir, filename)
        print(fullpath)
        if os.path.exists(fullpath):
            return fullpath

        connect_str = "DefaultEndpointsProtocol=https;AccountName=magdb;AccountKey=utIvM90o55boj2A/NoqL8aciy/C3jcRsUmF1zgRCqzbX4kH/UV4aNXQYf9ojkslZcivj66gvOK7T3Bc7pTzXqA==;EndpointSuffix=core.windows.net"
        blob_service_client = BlockBlobService(connection_string=connect_str)
        blob_service_client.get_blob_to_path(
            container_name, "mag/%s" % filename, fullpath
        )

        return fullpath

    # Download in parallel
    r = Parallel(n_jobs=-1, verbose=10)(
        [delayed(process)(datadir, filename, container_name) for filename in filenames]
    )
