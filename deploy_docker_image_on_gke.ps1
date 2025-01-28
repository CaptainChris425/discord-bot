# Set variables
Set-Variable GCLOUD_PROJECT_ID "nightbotcommands"
Set-Variable REGION "us-west2"
Set-Variable CLUSTER_NAME "discord-bot-cluster-usw2"
Set-Variable ARTIFACT_REPOSITORY_NAME "discord-bot-repo"
Set-Variable ARTIFACT_IMAGE_NAME "gemini-bot"

# Set Project
Write-Output 'Y' | gcloud config set project $GCLOUD_PROJECT_ID

# View Configurations
gcloud config list

# Enable APIs
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable container.googleapis.com

# View Enabled APIs
gcloud services list --enabled --project $GCLOUD_PROJECT_ID

# Create a new Docker repository named $ARTIFACT_REPOSITORY_NAME in the location us-west2 with the description "Docker repository"
gcloud artifacts repositories create $ARTIFACT_REPOSITORY_NAME --repository-format=docker --location=$REGION --description="Docker repository"

# Verify that your repository was created
gcloud artifacts repositories list

# Build and upload image
gcloud builds submit --region=$REGION --tag $REGION-docker.pkg.dev/$GCLOUD_PROJECT_ID/$ARTIFACT_REPOSITORY_NAME/$ARTIFACT_IMAGE_NAME-image:latest

# Create a GKE cluster
# gcloud container clusters create-auto $CLUSTER_NAME --region $REGION

# Install the kubectl component
gcloud components install kubectl

# Verify that kubectl is installed
kubectl version

# gcloud components install gke-gcloud-auth-plugin
gcloud components install gke-gcloud-auth-plugin

# gke-gcloud-auth-plugin --version
gke-gcloud-auth-plugin --version

# Update the kubectl configuration to use the plugin
gcloud container clusters get-credentials $CLUSTER_NAME --region=$REGION

# Verify the configuration
kubectl get namespaces

# Verify that you have access to the cluster. The following command lists the nodes in  your container cluster which are up and running and indicates that you have access to  the cluster
kubectl get nodes

# Deploy the resource to the cluster
kubectl apply -f deployment.yaml

# Track the status of the Deployment
kubectl get deployments

# After the Deployment is complete, you can see the Pods that the Deployment created
kubectl get pods