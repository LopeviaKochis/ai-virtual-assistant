#!/bin/bash

# VARIABLES
ACR_NAME="acrdoctorsolragdev"
IMAGE_NAME="doctor-sol-rag-app"
IMAGE_TAG="v2"

# Construir imagen
echo " Construyendo imagen Docker..."
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

# Etiquetar
echo "🏷 Etiquetando imagen..."
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}

# Login al ACR
echo "Iniciando sesión en ACR..."
az acr login --name ${ACR_NAME}

# Push a Azure
echo "Subiendo imagen al ACR..."
docker push ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}

echo "Imagen subida correctamente: ${ACR_NAME}.azurecr.io/${IMAGE_NAME}:${IMAGE_TAG}"
