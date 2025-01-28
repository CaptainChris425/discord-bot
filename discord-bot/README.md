# Discord Bot Project

This project is a simple Discord bot built using the `discord.py` library. It serves as a template for creating your own Discord bots with modular cogs and utility functions.

## Project Structure

```
discord-bot
├── src
│   ├── bot.py
│   ├── cogs
│   │   └── example_cog.py
│   └── utils
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
   In `src/bot.py`, replace `YOUR_BOT_TOKEN` with your actual bot token.

## Usage

To run the bot, execute the following command in your terminal:
```
python src/bot.py
```

## Features

- **Cogs:** The bot supports cogs, which allow you to organize commands and event listeners into separate classes.
- **Utilities:** Helper functions are provided to assist with common tasks such as message formatting and event logging.

## Contributing

Feel free to fork the repository and submit pull requests for any improvements or features you would like to add.