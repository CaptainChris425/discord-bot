# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app
# Copy the requirements file into the container
COPY discord-bot/requirements.txt .

# Install the dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Install Pre-requisites
RUN apt-get update && apt-get install -y
RUN apt-get install -y curl
RUN curl -sSL https://sdk.cloud.google.com | bash

# Copy the rest of the application code into the container
COPY discord-bot .

# Set environment variables
ENV DEBUG=False
ENV GOOGLE_CLOUD_PROJECT="nightbotcommands"
ENV GOOGLE_CLOUD_PROJECT_ID="nightbotcommands"
ENV GCS_BUCKET_NAME="discord-bot-bucket-cy"
ENV DEBUG_GUILD_ID=
ENV CONVERSATION_CHANNEL_NAME="ai-chatroom"
ENV DISCORD_TOKEN=""


# Expose the port the app runs on (if applicable)
EXPOSE 8000

# Command to run the application
CMD ["python", "src/bot.py"]