import logging
from time import sleep
import requests

import azure.functions as func
import azure.durable_functions as df
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials

from common.keys import (
    ENDPOINT_FACEAPI,
    KEY_FACEAPI,
    MOVIE_API_KEY,
    TENANT_ID,
    CLIENT_ID,
    CLIENT_SECRET,
    SUBSCRIPTION_ID,
    RESOURCE_GROUP_NAME,
    ACCOUNT_NAME,
    BLOB_CONNECTION_STRING
)


def orchestrator_function(context: df.DurableOrchestrationContext):
    callInput = context.get_input() #gets input given by httpStarter
    
    PERSON_GROUP_ID = context.new_uuid() #to use the same PERSON_ID everywhere

    #Get movie id
    movieId: int = get_movie_id(callInput["probableMovieName"])

    face_client = FaceClient(ENDPOINT_FACEAPI, CognitiveServicesCredentials(KEY_FACEAPI))
    
    try:
        face_client.person_group.get(PERSON_GROUP_ID)
    except Exception as e:
        logging.info(f"person group {PERSON_GROUP_ID} not yet created, creating...")
        face_client.person_group.create(
                            person_group_id=PERSON_GROUP_ID,
                            name=f"grp_{PERSON_GROUP_ID}"
                        )

    
    if not context.is_replaying:
        context.set_custom_status("learning the faces")
    
    faces_tasks = get_tasks_to_add_faces_to_model(movieId, context, PERSON_GROUP_ID)
    faces_ids_and_names = yield context.task_all(faces_tasks)

    context.set_custom_status("training the model")
    face_client.person_group.train(PERSON_GROUP_ID)
    training_status = face_client.person_group.get_training_status(PERSON_GROUP_ID)
    while (training_status.status != "succeeded"):
        if (training_status.status == "notstarted"):
            face_client.person_group.train(PERSON_GROUP_ID)
        if (training_status.status == "failed"):
            raise Exception(f"training failed: {training_status.message}")
        training_status = face_client.person_group.get_training_status(PERSON_GROUP_ID)
        print(f"training status: {training_status.status}")
        sleep(3)

    
    #Slice the movie and detect faces (without identification)
    faces_ids_dict = yield context.call_activity('sliceMovie', callInput["inputMovieUrl"])

    #Identify faces from our PERSON GROUP
    identified_faces_dict = yield context.call_activity("recognize", {"faces_ids_dict": faces_ids_dict, "PERSON_GROUP_ID": PERSON_GROUP_ID})
    
    #Create result
    name_id_map = {}
    for element in faces_ids_and_names:
        name_id_map[element[0]] = element[1]

    result_actors = {}
    for frame in identified_faces_dict:
        result_actors[frame] = [] #{frame_0: [Daniel Craig, Tobie...], ...}
        for actor_id in identified_faces_dict[frame]:
            result_actors[frame].append(name_id_map[actor_id])

    return result_actors
    #return {"name_id_mapping": name_id_map, "identified_faces_dict": identified_faces_dict}


def get_movie_id(probableMovieName: str) -> str:
    queryParams_getID = (("api_key", MOVIE_API_KEY), ("query", probableMovieName))
    url = "https://api.themoviedb.org/3/search/movie"
    response = requests.request("GET", url, params=queryParams_getID)
    return response.json()["results"][0]["id"]


def get_tasks_to_add_faces_to_model(movieId: int, context: df.DurableOrchestrationContext, PERSON_GROUP_ID: str): #maybe return tasks and call them from the main
    context.set_custom_status("adding faces")
    queryParams_getActors = (("api_key", MOVIE_API_KEY),)
    url = f"http://api.themoviedb.org/3/movie/{movieId}/casts"
    responseActorPaths = requests.request("GET", url, params=queryParams_getActors)
    parallel_tasks = []

    for i in range(5):
        faces_input = dict()
        faces_input["PERSON_GROUP_ID"] = PERSON_GROUP_ID
        faces_input["actor_profile_path"] = responseActorPaths.json()["cast"][i]["profile_path"]
        faces_input["name"] = responseActorPaths.json()["cast"][i]["name"]
        parallel_tasks.append(context.call_activity("getFaces", faces_input))
        
    return parallel_tasks

main = df.Orchestrator.create(orchestrator_function)
