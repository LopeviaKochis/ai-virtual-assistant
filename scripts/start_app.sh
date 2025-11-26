#!/bin/bash

RESOURCE_GROUP="rg-doctor-sol-rag-dev"
CONTAINERAPP_NAME="doctor-sol-ai"

echo "Encendiendo Container App..."
az containerapp scale \
  --name $CONTAINERAPP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 1 \
  --max-replicas 1

echo "App encendida."
