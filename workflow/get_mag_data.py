#
# Follow the instruction below:
# https://docs.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python#download-blobs
import os, uuid, sys
from azure.storage.blob import BlockBlobService


FILENAME = sys.argv[1]
DATA_DIR = sys.argv[2]
CONNECT_KEY = sys.argv[3]


if __name__ == "__main__":
    #
    # Configuraton
    #
    # datadir = "./data-compile/original"

    #
    # Key
    #
    # connect_str = "DefaultEndpointsProtocol=https;AccountName=magdb;AccountKey=utIvM90o55boj2A/NoqL8aciy/C3jcRsUmF1zgRCqzbX4kH/UV4aNXQYf9ojkslZcivj66gvOK7T3Bc7pTzXqA==;EndpointSuffix=core.windows.net"
    blob_service_client = BlockBlobService(connection_string=CONNECT_KEY)

    #
    # BlobServiceClient -> Container_client -> Blob_client -> Download the file and save it
    #
    # filenames = [
    #    "Affiliations.txt",
    #    "Journals.txt",
    #    "ConferenceInstances.txt",
    #    "ConferenceSeries.txt",
    #    "Authors.txt",
    #    "PaperAuthorAffiliations.txt",
    #    "PaperExtendedAttributes.txt",
    #    "PaperReferences.txt",
    #    "PaperResources.txt",
    #    "Papers.txt",
    #    "PaperUrls.txt",
    # ]

    # Get container name
    all_containers = blob_service_client.list_containers(include_metadata=True)
    all_containers = list(all_containers)
    all_containers.sort(key=lambda x: x.properties.last_modified)
    container_name = all_containers[-1].name

    # Download and save files
    fullpath = "%s/%s" % (DATA_DIR, FILENAME)
    blob_service_client = BlockBlobService(connection_string=CONNECT_KEY)
    blob_service_client.get_blob_to_path(container_name, "mag/%s" % FILENAME, fullpath)
