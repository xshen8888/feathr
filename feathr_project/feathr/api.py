import os, json
import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Response, status
from pyapacheatlas.core import (AtlasException)
from pydantic import BaseModel
from opencensus.ext.azure.log_exporter import AzureLogHandler
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError, ServiceRequestError, ResourceNotFoundError
from feathr._envvariableutil import _EnvVaraibleUtil
from feathr.protobuf.featureValue_pb2 import FeatureValue
from feathr._feature_registry import _FeatureRegistry
from feathr._file_utils import write_to_file
from feathr._synapse_submission import _FeathrSynapseJobLauncher
from feathr._databricks_submission import _FeathrDatabricksJobLauncher
from feathr.query_feature_list import FeatureQuery
from feathr.settings import ObservationSettings
from feathr.constants import *
from feathr._feature_registry import _FeatureRegistry



app = FastAPI()

# Log Level
log_level = os.getenv("logLevel", "INFO")

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
app_insights_connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
formatter = logging.Formatter("[%(asctime)s] [%(name)s:%(lineno)s - %(funcName)5s()] %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
if app_insights_connection_string:
    azure_handler = AzureLogHandler(connection_string=app_insights_connection_string)
    logger.addHandler(azure_handler)
else:
    logger.warning("APPLICATIONINSIGHTS_CONNECTION_STRING is not set - will NOT log to AppInsights!!")
logger.setLevel(log_level)
logger.info("starting %s", __file__)

appServiceKey = os.getenv("AppServiceKey") if os.getenv("AppServiceKey") else "test"

config_path = '../feathrcli/data/feathr_user_workspace/feathr_config.yaml'
# registry = _FeatureRegistry(config_path = config_path)

def getRegistryClient(config_path : Optional[str] = config_path):
    return _FeatureRegistry(config_path = config_path)


@app.get("/")
async def root(code):
    """
    Root endpoint
    """
    if code != appServiceKey:
        raise HTTPException(status_code=403, detail="You are not allowed to access this resource")
    return {"message": "To call/invoke add endpoint."}

class Features(BaseModel):
    """
    Defining contract for input field
    """

    features: List[str]


@app.get("/projects/{project_name}/features", response_model=Features)
def list_registered_features(code, project_name: str, response: Response):
    """List all the already registered features. If project_name is not provided or is None, it will return all
    the registered features; otherwise it will only return features under this project
    """
    if code != appServiceKey:
        raise HTTPException(status_code=403, detail="You are not allowed to access this resource")  
    try:
        registry_client = getRegistryClient()
        logger.info("Retrieved registry client successfully")
        response.status_code = status.HTTP_200_OK
        result = registry_client.list_registered_features(project_name)
        return {"features" : result}
    except AtlasException as ae:
        logger.error("Error retrieving feature: %s", ae.args[0])
        raise HTTPException(status_code=400, detail="Error: " + ae.args[0])
    except Exception as err:
        logger.error("Error: %s", err.args[0])
        raise HTTPException(status_code=400, detail="Error: " + err.args[0])


@app.get("/projects/{project_name}/features/{feature_name}")
def get_feature_qualifiedName(code : str, project_name: str, feature_name: str, response: Response, type_name: Optional[str] = None):
    """List all the already registered features. If project_name is not provided or is None, it will return all
    the registered features; otherwise it will only return features under this project
    """
    if code != appServiceKey:
        raise HTTPException(status_code=403, detail="You are not allowed to access this resource")  
    try:
        registry_client = getRegistryClient()
        logger.info("Retrieved registry client successfully")
        response.status_code = status.HTTP_200_OK
        result = None
        if type_name: # Type is provided
            result = registry_client.get_feature_by_fqdn_type(feature_name, type_name)
        else:
            result = registry_client.get_feature_by_fqdn(feature_name)
        return result
    except AtlasException as ae:
        logger.error("Error retrieving feature: %s", ae.args[0])
        raise HTTPException(status_code=400, detail=ae.args[0])
    except Exception as err:
        logger.error("Error: %s", err.args[0])
        raise HTTPException(status_code=400, detail=err.args[0])



