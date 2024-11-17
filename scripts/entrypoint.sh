#!/bin/bash

fastapi run --host "0.0.0.0" --port $FASTAPI_PORT --workers $FASTAPI_NUM_WORKERS app/main.py