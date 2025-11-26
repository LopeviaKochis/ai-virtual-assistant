#!/bin/bash

RESOURCE_GROUP="rg-doctor-sol-rag-dev"
CONTAINERAPP_NAME="doctor-sol-ai"

echo "Apagando Container App..."
az containerapp scale \
  --name $CONTAINERAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 0 \
  --max-replicas 0

echo "App apagada."
