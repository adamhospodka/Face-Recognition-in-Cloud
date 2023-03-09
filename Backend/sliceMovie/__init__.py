import logging
from time import sleep
import random
import uuid

from azure.identity import ClientSecretCredential
from azure.mgmt.media import AzureMediaServices
from azure.storage.blob import ContainerClient, BlobServiceClient, AccessPolicy, PublicAccess, ContainerSasPermissions

from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials

from common.keys import (
    TENANT_ID,
    CLIENT_ID,
    CLIENT_SECRET,
    SUBSCRIPTION_ID,
    RESOURCE_GROUP_NAME,
    ACCOUNT_NAME,
    BLOB_CONNECTION_STRING,
    ENDPOINT_FACEAPI,
    KEY_FACEAPI
)

from azure.mgmt.media.models import Asset, Job, JobInputHttp, JobOutputAsset


def main(inputMovieUrl: str):
    # Credentials
    credentials = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
    client = AzureMediaServices(credentials, SUBSCRIPTION_ID)
    assets = client.assets.list(RESOURCE_GROUP_NAME, ACCOUNT_NAME)
    uniqueness = random.randint(0,9999999) #can we use uuid? this may collide

    # Out
    out_asset_name = 'outputassetName' + str(uniqueness)
    out_alternate_id = 'outputALTid' + str(uniqueness)
    out_description = 'outputdescription' + str(uniqueness)

    output_asset = Asset(
        alternate_id=out_alternate_id,
        description=out_description
    )

    outputAsset = client.assets.create_or_update( #toto grca logy...... asi........................
        RESOURCE_GROUP_NAME, 
        ACCOUNT_NAME,
        out_asset_name,
        output_asset
    )

    # ------ Clients ------ #
    media_services_client = AzureMediaServices(credentials, SUBSCRIPTION_ID)
    blob_service_client = BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)


    # ------ Initiatee Azure Job ------ #
    job_name = 'job-video2images-'+ str(uniqueness)

    theJob = Job(
        input= JobInputHttp(files=[inputMovieUrl]),
        outputs=[JobOutputAsset(asset_name=out_asset_name)]
    )

    # Launch job in Azure
    job = client.jobs.create(
        RESOURCE_GROUP_NAME,
        ACCOUNT_NAME,
        'video2images_1s',
        job_name,
        parameters=theJob
    )

    # ------ Get images ------ #

    # Blob container name
    container_from_asset_name = client.assets.get(
        RESOURCE_GROUP_NAME, 
        ACCOUNT_NAME, 
        out_asset_name
    )

    images_container = container_from_asset_name.container

    # Blob container handle
    container = ContainerClient.from_connection_string(
        BLOB_CONNECTION_STRING, 
        container_name=images_container
    )

    # Define access policy
    access_policy = AccessPolicy(permission=ContainerSasPermissions(read=True, write=True))
    identifiers = {'read': access_policy}

    container.set_container_access_policy(signed_identifiers=identifiers, public_access=PublicAccess.Container)


    # Download images to variable as byte-array
    def get_images_urls(images_container=images_container):
        image_urls = []

        for blob in container.list_blobs():
            if ".jpg" in blob.name:
                blob_client = blob_service_client.get_blob_client(
                    container=images_container, 
                    blob=blob.name
                )
                image_urls.append(blob_client.url)
            
        return image_urls


    job_done = False
    while (job_done == False):
        sleep(4)
        job_done = client.jobs.get(RESOURCE_GROUP_NAME, ACCOUNT_NAME, 'video2images_1s', job_name).state == 'Finished'
    
    images_urls = get_images_urls()

    face_client = FaceClient(ENDPOINT_FACEAPI, CognitiveServicesCredentials(KEY_FACEAPI))
    
    identified_faces = {}
    frames_counter = 0

    for image_url in images_urls:
        
        detected_faces = face_client.face.detect_with_url(
                                image_url,
                                detection_model='detection_03'
                            )
        faces_ids = [face.face_id for face in detected_faces]
        identified_faces[f"frame_{frames_counter}"] = faces_ids
        print(f"DETECT: frame_{frames_counter} : identified faces: {faces_ids}")
        frames_counter += 1

    return identified_faces
