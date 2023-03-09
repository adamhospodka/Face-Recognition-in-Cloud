import logging
from common.keys import *
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials
from azure.cognitiveservices.vision.face.models import TrainingStatusType, Person, QualityForRecognition

MOVIE_API_KEY = "f761dc8c1d9071cb1b257bc9d7807598"
face_client = FaceClient(ENDPOINT_FACEAPI, CognitiveServicesCredentials(KEY_FACEAPI))

# Get face image url, add the face to the recognition model, return touple (name, id) of person
def main(facesInput: dict):

    PERSON_GROUP_ID = facesInput["PERSON_GROUP_ID"]
    ACTOR_PROFILE_PATH = facesInput["actor_profile_path"]
    ACTOR_NAME = facesInput["name"]

    url = f"https://www.themoviedb.org/t/p/w500{ACTOR_PROFILE_PATH}"
    queryParams_getPicture = (("api_key", MOVIE_API_KEY),)
    logging.info(f"adding pic of {ACTOR_NAME} from: {url}")

    try:
        actorX = face_client.person_group_person.create(person_group_id=PERSON_GROUP_ID, name=ACTOR_NAME)
        #face_client.person_group_person.add_face_from_stream(PERSON_GROUP_ID, actorX.person_id, image)
        face_client.person_group_person.add_face_from_url(person_group_id=PERSON_GROUP_ID, person_id=actorX.person_id, url=url)
        logging.info(f"added pic of {ACTOR_NAME}")
        print(f"added {ACTOR_NAME} with id {actorX.person_id}")
    except BaseException as e:
        logging.error(f"Exception {e=}, {type(e)=}")
        raise

    return (actorX.person_id, ACTOR_NAME)









