import structlog
import uvicorn
import uuid
import os
from fastapi import FastAPI, Request, Response, Depends
from .routers import user
from .dependencies import get_api_key

app = FastAPI(
    title="OPA Keycloak Middleware",
    description="OPA Keycloak Middleware",
    version="0.1.0"
)
logger = structlog.get_logger()

UVICORN_PORT = os.environ.get("UVICORN_PORT", "8888")
APP_ROOT_PATH = os.environ.get("APP_ROOT_PATH", "")

@app.middleware("http")
async def logger_middleware(request: Request, call_next):
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        path=request.url.path,
        method=request.method,
        client_host=request.client.host,
        request_id=str(uuid.uuid4())
    )
    response = await call_next(request)

    structlog.contextvars.bind_contextvars(
        status_code=response.status_code
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

app.include_router(
    user.router,
    prefix="/api/v1/secure/user",
    dependencies=[Depends(get_api_key)]
)

def main():
    uvicorn.run(app, host="0.0.0.0", port=int(UVICORN_PORT), root_path=APP_ROOT_PATH)
