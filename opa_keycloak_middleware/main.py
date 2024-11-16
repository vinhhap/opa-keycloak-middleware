from fastapi import FastAPI, Request, Response
import structlog
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
from keycloak.exceptions import KeycloakGetError
from typing import Optional, Dict, List, Any
import uvicorn
import uuid
import os
import json
from pydantic import BaseModel

app = FastAPI(
    title="OPA Keycloak Middleware",
    description="OPA Keycloak Middleware",
    version="0.1.0"
)
logger = structlog.get_logger()

UNICORN_PORT = os.environ.get("PORT", "8888")
KEYCLOAK_SERVER_URL = os.environ.get("KEYCLOAK_SERVER_URL", "https://localhost/")
KEYCLOAK_REALM_NAME = os.environ.get("KEYCLOAK_REALM_NAME", "master")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "default")
KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")
KEYCLOAK_USERNAME = os.environ.get("KEYCLOAK_USERNAME", KEYCLOAK_CLIENT_ID)
KEYCLOAK_PASSWORD = os.environ.get("KEYCLOAK_PASSWORD", KEYCLOAK_CLIENT_SECRET)
KEYCLOAK_GRANT_TYPE = os.environ.get("KEYCLOAK_GRANT_TYPE", "client_credentials")
APP_ROOT_PATH = os.environ.get("APP_ROOT_PATH", "")

keycloak_connection = KeycloakOpenIDConnection(
    server_url=KEYCLOAK_SERVER_URL,
    realm_name=KEYCLOAK_REALM_NAME,
    client_id=KEYCLOAK_CLIENT_ID,
    client_secret_key=KEYCLOAK_CLIENT_SECRET,
    username=KEYCLOAK_USERNAME,
    password=KEYCLOAK_PASSWORD,
    grant_type=KEYCLOAK_GRANT_TYPE
)
keycloak_admin = KeycloakAdmin(connection=keycloak_connection)

class User(BaseModel):
    id: Optional[str] = None
    username: str
    groups: List[str] = []
    customAttributes: Dict[str, Any] = {}
    error: Optional[str] = None

def get_user_id(username: str) -> str | None:
    try:
        userid = keycloak_admin.get_user_id(username)
        return userid
    except KeycloakGetError as get_exception:
        e_message = json.loads(get_exception.error_message.decode('utf-8'))
        logger.info(f"User not found: {username}")
        return None
    except Exception as e:
        logger.info(e)
        return None

def get_user_groups(userid: str) -> List[str]:
    try:
        groups = keycloak_admin.get_user_groups(userid)
        parsed_groups = [g['path'] for g in groups]
        return parsed_groups
    except KeycloakGetError as get_exception:
        e_message = json.loads(get_exception.error_message.decode('utf-8'))
        logger.info(f"Groups not found for user: {userid}")
        return []
    except Exception as e:
        logger.info(e)
        return []

@app.middleware("http")
async def logger_middleware(request: Request, call_next):
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        path=request.url.path,
        method=request.method,
        client_host=request.client.host,
        request_id=str(uuid.uuid4()),
    )
    response = await call_next(request)

    structlog.contextvars.bind_contextvars(
        status_code=response.status_code,
    )

    # Exclude /healthcheck endpoint from producing logs
    if request.url.path != "/healthcheck":
        if 400 <= response.status_code < 500:
            logger.warn("Client error")
        elif response.status_code >= 500:
            logger.error("Server error")
        else:
            logger.info("OK")

    return response


@app.get("/healthcheck")
async def healthcheck():
    return {"status": "I'm still healthy!"}

@app.get("/users/{username}")
async def get_user(username: str) -> User:
    userid = get_user_id(username)
    if not userid:
        return User(username=username, error="USERNAME_NOT_FOUND")
    
    groups = get_user_groups(userid)
    return User(id=userid, username=username, groups=groups, customAttributes={})

def main():
    uvicorn.run(app, host="0.0.0.0", port=int(UNICORN_PORT), root_path=APP_ROOT_PATH)
