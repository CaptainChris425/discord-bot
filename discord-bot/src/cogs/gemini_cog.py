# Description: This file contains the GeminiCog class, which is a cog for the Discord bot that interacts with the Gemini Vertex AI API.
import discord
from discord.ext import commands
import os
import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.generative_models import Part
from vertexai.preview.vision_models import ImageGenerationModel
import aiohttp
import asyncio
from gtts import gTTS
from google.cloud import storage, vision
import logging
from utils.helpers import *

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
DEBUG_GUILD_ID = os.getenv('DEBUG_GUILD_ID', 123456789012345678)
logger.info(f"DEBUG: {DEBUG}, DEBUG_GUILD_ID: {DEBUG_GUILD_ID}")

class GeminiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        self.location = 'us-central1'  # Change this to your Vertex AI location
        self.bucket_name = os.getenv('GCS_BUCKET_NAME')
        self.model = GenerativeModel("gemini-1.5-flash-002")
        self.image_model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")  # Initialize the ImageGenerationModel
        # Initialize the Vertex AI client
        vertexai.init(project=self.project_id, location=self.location)

    def check_debug_mode(self, ctx):
        if DEBUG and ctx.guild.id != DEBUG_GUILD_ID:
            logger.info(f"Debug mode is enabled. This command is only available in the debug server. ctx.guild.id: {ctx.guild.id}, DEBUG_GUILD_ID: {DEBUG_GUILD_ID}")
            return False
        return True

    @commands.command(name='ai')
    async def gemini(self, ctx, *, prompt: str = None):
        """Main command to interact with the Gemini Vertex AI API"""
        logger.info(f"{ctx.author} called the gemini command with prompt: {prompt}")
        if not self.check_debug_mode(ctx):
            return

        try:
            text_response = await process_and_generate_response(ctx, self.model, self.bucket_name, prompt)
            # Split the response into chunks of 2000 characters
            for i in range(0, len(text_response), 2000):
                await ctx.send(text_response[i:i+2000])
        except Exception as e:
            await ctx.send(f"Error: {str(e)}")

    @commands.command(name='imgen')
    async def imgen(self, ctx, *, prompt: str = None):
        """Generates an image based on the given prompt using ImageGenerationModel"""
        logger.info(f"{ctx.author} called the imgen command with prompt: {prompt}")
        if not self.check_debug_mode(ctx):
            return

        try:
            for attempt in range(3):  # Retry up to 3 times
                image_response = self.image_model.generate_images(
                    prompt=prompt,
                    number_of_images=3,
                    language="en",
                    aspect_ratio="1:1",
                    safety_filter_level="block_some",
                )
                logger.info(f"Attempt {attempt + 1}: image_response: {image_response}")

                if image_response.images:  # Check if any images were generated
                    image_path = f"temp_image_{ctx.message.id}.png"
                    image_response[0].save(location=image_path)
                    await ctx.send(file=discord.File(image_path))
                    os.remove(image_path)  # Clean up the downloaded file
                    break
            else:
                await ctx.send("Failed to generate images after 3 attempts.")

        except Exception as e:
            await ctx.send(f"Error: {str(e)}")

async def setup(bot):
    await bot.add_cog(GeminiCog(bot))