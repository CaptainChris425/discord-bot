 # Discord Bot Project
 
 This project is a simple Discord bot built using the `discord.py` library. It serves as a template for creating your own Discord bots with modular cogs and utility functions, leveraging the Gemini AI model for various interactions.
 
 ## Table of Contents
 
 - [Project Structure](#project-structure)
 - [Setup Instructions](#setup-instructions)
 - [Usage](#usage)
 - [Features](#features)
 - [Configuration](#configuration)
 - [Cogs](#cogs)
 - [Utilities](#utilities)
 - [Contributing](#contributing)
 - [License](#license)
 - [Credits](#credits)
 
 ## Project Structure
 
 ```
 discord-bot
 ├── src
 │   ├── bot.py
 │   ├── cogs
 │   │   ├── __init__.py
 │   │   ├── example_cog.py
 │   │   ├── gemini_cog.py
 │   │   ├── gemini_conv_cog.py
 │   │   ├── gemini_voice_cog.py
 │   │   └── image_link_cog.py
 │   └── utils
 │       ├── __init__.py
 │       └── helpers.py
 ├── requirements.txt
 └── README.md
 ```
 
 ## Setup Instructions
 
 1. **Clone the repository:**
    ```
    git clone <repository-url>
    cd discord-bot
    ```
 
 2. **Install dependencies:**
    Make sure you have Python 3.8 or higher installed. Then, run:
    ```
    pip install -r requirements.txt
    ```
 
 3. **Create a Discord bot application:**
    - Go to the [Discord Developer Portal](https://discord.com/developers/applications).
    - Create a new application and add a bot to it.
    - Copy the bot token.
 
 4. **Configure the bot token:**
    In `src/bot.py`, replace `YOUR_BOT_TOKEN` with your actual bot token, or add it to .env.
 
 ## Usage
 
 To run the bot, execute the following command in your terminal:
 ```
 python src/bot.py
 ```
 
 ## Features
 
 - **Cogs:** The bot supports cogs, which allow you to organize commands and event listeners into separate classes.
  - **Gemini AI Integration:** Utilizes the Gemini AI model for advanced text generation, image analysis, and more.
 - **Utilities:** Helper functions are provided to assist with common tasks such as message formatting and event logging.
 - **Voice Channel Support:** Includes cogs for interacting with voice channels, allowing the bot to join, speak, and leave voice channels.
 - **Conversational AI:** Implements conversational AI within specified channels, enabling the bot to maintain context and respond to ongoing conversations.
 - **Image Generation:** Generates images based on text prompts using the Gemini AI image generation capabilities.
 
 ## Configuration
 
 The bot relies on several environment variables for configuration. These should be set either directly in your environment or in a `.env` file.
 
 - `DISCORD_TOKEN`: The token for your Discord bot. This is essential for the bot to connect to Discord.
 - `GOOGLE_CLOUD_PROJECT_ID`: Your Google Cloud Project ID. Required for accessing Vertex AI services.
 - `GCS_BUCKET_NAME`: The name of your Google Cloud Storage bucket. Used for storing temporary files, such as images and videos, for processing by the Gemini AI model.
 - `DEBUG`: A boolean value (`True` or `False`) to enable or disable debug mode. When enabled, certain commands may be restricted to a specific server.
 - `DEBUG_GUILD_ID`: The ID of the Discord guild (server) to use for debugging.
 - `CONVERSATION_CHANNEL_NAME`: The name of the channel where conversational AI is enabled. Defaults to `ai-chatroom`.
 - `BLACKJACK_CHANNEL_NAME`: The name of the channel where the blackjack game is enabled.  Defaults to `blackjack-ai-bot`.
 
 ## Cogs
 
 Cogs are modular components that provide specific functionality to the bot. The following cogs are included in this project:
 
 - `example_cog.py`: A basic example cog that demonstrates how to create commands and event listeners.
 - `gemini_cog.py`: Contains commands for interacting with the Gemini AI model, such as generating text and images.
 - `gemini_conv_cog.py`: Implements conversational AI, allowing the bot to participate in ongoing conversations within specified channels.
 - `gemini_voice_cog.py`: Provides commands for the bot to join voice channels, speak, and leave.
 - `image_link_cog.py`: (If applicable) Cog for handling image-related commands and functionalities.
 
 To enable or disable cogs, modify the `EXTENSIONS` list in `src/bot.py`.
 
 ## Utilities
 
 The `utils` directory contains helper functions that are used throughout the bot.
 
 - `helpers.py`: Provides functions for tasks such as:
  - Interacting with the Gemini AI API
  - Downloading and uploading files to Google Cloud Storage
  - Safe search detection
  - Processing image, video, and document attachments
 
 ## Contributing
 
 Feel free to fork the repository and submit pull requests for any improvements or features you would like to add.
 
 ## License
 
 This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
 
 ## Credits
 
 - This project was created using the `discord.py` library.
 - The Gemini AI integration is powered by Google's Vertex AI.
 - Thanks to all contributors who have helped improve this project.
 
 ---
 
 ### Contributing
 When contributing to this project, please ensure:
 
 *   Your code adheres to the project's coding standards.
 *   You include relevant tests for any new functionality.
 *   You update the documentation as needed.
 