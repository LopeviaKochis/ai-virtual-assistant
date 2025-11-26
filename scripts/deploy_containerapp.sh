#!/bin/bash

# VARIABLES CONFIGURABLES
RESOURCE_GROUP="rg-doctor-sol-rag-dev"
ENV_NAME="env-doctor-sol-rag-dev"
LOCATION="westus2"
ACR_NAME="acrdoctorsolragdev"
IMAGE_NAME="doctor-sol-rag-app"
IMAGE_TAG="v2"
CONTAINERAPP_NAME="doctor-sol-ai"

# -----¡Modificado para verificar si existe un environment y usarlo para un nuevo despliegue!------
echo "Creando entorno de Container Apps (si no existe)..."
az containerapp env create \
  --name $ENV_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION || true # <- Si ya existe, no falla
# ************************************************************************************************
echo "Desplegando Container App..."
az containerapp create \
  --name $CONTAINERAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ENV_NAME \
  --image ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG} \
  --target-port 8000 \
  --ingress external \
  --registry-server ${ACR_NAME}.azurecr.io \
  --min-replicas 1 \
  --max-replicas 1 \
  --cpu 1 --memory 2Gi

echo "Aplicación desplegada. URL:"
az containerapp show \
  --name $CONTAINERAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  -o tsv
