import discord
from discord.ext import commands
from cogs import EXTENSIONS
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set the command prefix and intents
intents = discord.Intents.default()
intents.message_content = True
# intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Load cogs
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}')
    for cog in EXTENSIONS:
        await bot.load_extension(cog)

# Start the bot with the token
if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_TOKEN')
    bot.run(TOKEN)