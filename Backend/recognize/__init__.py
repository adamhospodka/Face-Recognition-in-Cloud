import logging
from msrest.authentication import CognitiveServicesCredentials
from azure.cognitiveservices.vision.face import FaceClient

from common.keys import ENDPOINT_FACEAPI, KEY_FACEAPI


def main(input):
    faces_ids_dict = input["faces_ids_dict"]
    PERSON_GROUP_ID = input["PERSON_GROUP_ID"]
    face_client = FaceClient(ENDPOINT_FACEAPI, CognitiveServicesCredentials(KEY_FACEAPI))

    identified_faces = {}
    for frame_faces_key in faces_ids_dict:
        if len(faces_ids_dict[frame_faces_key]) > 0:
            recognition = face_client.face.identify(
                                face_ids = faces_ids_dict[frame_faces_key], 
                                person_group_id = PERSON_GROUP_ID
                            )
            identified_faces[frame_faces_key] = []

            for person in recognition:
                if len(person.candidates) > 0:
                    identified_faces[frame_faces_key].append(person.candidates[0].person_id)
                    logging.info(f'Face {person.face_id} matches {person.candidates[0].person_id} with a confidence of {person.candidates[0].confidence}.')

                    print(f"RECOGNIZE:{frame_faces_key} contains: {person.candidates[0].person_id}")

    return identified_faces