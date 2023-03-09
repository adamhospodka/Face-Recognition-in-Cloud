#Starts the orchestrator (durable function)
import json
import logging

import azure.functions as func
import azure.durable_functions as df


async def main(req: func.HttpRequest, starter: str) -> func.HttpResponse:
    try:
        requestParams = json.loads(req.get_body())
        
    except KeyError as e:
        return func.HttpResponse(body="missing request param: " + repr(e), status_code=500)
    except Exception as e:
        return func.HttpResponse(body=repr(e), status_code=500)

    client = df.DurableOrchestrationClient(starter)
    
    instance_id = await client.start_new(req.route_params["functionName"], None, requestParams)

    logging.info(f"Started orchestration with ID = '{instance_id}'.")

    return client.create_check_status_response(req, instance_id)