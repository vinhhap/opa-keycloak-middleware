import os
import json
from typing import List
import structlog
from fastapi import APIRouter, Depends
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
from keycloak.exceptions import KeycloakGetError
from ..schemas.user import User

logger = structlog.get_logger()
router = APIRouter()

KEYCLOAK_SERVER_URL = os.environ.get("KEYCLOAK_SERVER_URL", "https://localhost/")
KEYCLOAK_REALM_NAME = os.environ.get("KEYCLOAK_REALM_NAME", "master")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "default")
KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")
KEYCLOAK_USERNAME = os.environ.get("KEYCLOAK_USERNAME", KEYCLOAK_CLIENT_ID)
KEYCLOAK_PASSWORD = os.environ.get("KEYCLOAK_PASSWORD", KEYCLOAK_CLIENT_SECRET)
KEYCLOAK_GRANT_TYPE = os.environ.get("KEYCLOAK_GRANT_TYPE", "client_credentials")

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

@router.get("/{username}", tags=["user"])
async def get_user(username: str) -> User:
    userid = get_user_id(username)
    if not userid:
        return User(username=username, error="USERNAME_NOT_FOUND")
    
    groups = get_user_groups(userid)
    return User(id=userid, username=username, groups=groups, customAttributes={})