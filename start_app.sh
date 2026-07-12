#!/bin/bash
cd /home/opc/ciphervault_social
source ciphervault_social/venv/bin/activate
exec ciphervault_social/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
