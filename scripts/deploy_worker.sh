#!/bin/bash

# Variables (ajusta según tu entorno)
RESOURCE_GROUP="rg-doctor-sol-rag-dev"
ENV_NAME="env-doctor-sol-rag-dev"
ACR_NAME="acrdoctorsolragdev"
IMAGE_TAG="v3"

# Desplegar el Worker
# Nota el uso de --command para sobrescribir Gunicorn por el script del worker
az containerapp create \
  --name "ai-assistant-worker" \
  --resource-group $RESOURCE_GROUP \
  --environment $ENV_NAME \
  --image ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG} \
  --min-replicas 1 \
  --max-replicas 1 \
  --cpu 1 --memory 2.1Gi \
  --command "python" "worker.py" \
  --env-vars-from-secret "REDIS_URL=redis-secret" \
  --registry-server ${ACR_NAME}.azurecr.io
