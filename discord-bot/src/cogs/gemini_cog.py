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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEBUG = False  # Set this to True to enable debug mode
DEBUG_GUILD_ID = 1333162585981456495  # Replace with your specific Discord server ID

INSTRUCTIONS = {
    'freeform': "You are a helpful assistant. Please provide detailed and accurate responses. Keep your responses short like you are texting someone.",
    'image': "You are a helpful assistant. Please provide detailed and accurate responses. Keep your responses short like you are texting someone. The image is attached, please explain it to me.",
    'video': "You are a helpful assistant. Please provide detailed and accurate responses. Keep your responses short like you are texting someone. The video is attached, please explain it to me.",
    'document': "You are a helpful assistant. Please provide detailed and accurate responses. Keep your responses short like you are texting someone. The document is attached, please explain it to me.",
    'coach': (
        "Keep your responses short like you are texting someone. You are a videogame professional coach. You are watching a video of a player playing a game. "
        "Provide a detailed analysis of the player's gameplay. Include the player's strengths and weaknesses, and suggest ways to improve their gameplay. "
        "Specifically point out the player's positioning, aim, and movement. Also, mention any strategies the player is using and suggest new strategies they could try. "
        "Consider signing the player to your team. Would they be a good fit? Why or why not?"
    ),
    'narrate': ("provide a script to narrate what you see as if it was a play-by-play commentary of a sports game."),
    'roast': ("You are a mean person. You are roasting someone. Be as mean as you can be. Don't hold back. If you detect a game in the image or video, roast the game too."),
    'playsong': ("You are a DJ. You are playing a song for someone. Based on the prompt, play a song that fits the mood. Only respond with a song name and artist."),
    'greeting': ("You are a friendly assistant. Greet the user like they are a new friend."),
    'meme': ("You are a meme generator. Generate the best meme you can think of."),
}

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
    
    #@commands.command(name='join')
    async def join(self, ctx, *, channel: discord.VoiceChannel = None):
        """Joins a voice channel"""
        logger.info(f"{ctx.author} called the join command")
        if not ctx.author.voice:
            return await ctx.send("You are not connected to a voice channel.")
        
        channel = channel or ctx.author.voice.channel
        
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
    
    #@commands.command(name='leave')
    async def leave(self, ctx, *, prompt: str = None):
        """Leaves a voice channel"""
        logger.info(f"{ctx.author} called the leave command")
        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()
    
    @commands.command(name='ai-stop')
    async def gemini_stop(self, ctx):
        """Stops the bot from speaking"""
        logger.info(f"{ctx.author} called the ai-stop command")
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    async def process_and_generate_response(self, ctx, prompt: str = None):
        """Processes attachments and generates a response using the Gemini Vertex AI API"""
        # Check for image, video, or document links
        image_links = [(attachment.url, attachment.content_type) for attachment in ctx.message.attachments if attachment.content_type and attachment.content_type.startswith('image/')]
        video_links = [(attachment.url, attachment.content_type) for attachment in ctx.message.attachments if attachment.content_type and attachment.content_type.startswith('video/')]
        document_links = [(attachment.url, attachment.content_type) for attachment in ctx.message.attachments if attachment.content_type and (attachment.content_type.startswith('application/pdf') or attachment.content_type.startswith('text/plain'))]

        if image_links:
            await self.gemini_image(ctx, prompt=prompt)
            return
        if video_links:
            await self.gemini_video(ctx, prompt=prompt)
            return
        if document_links:
            await self.gemini_document(ctx, prompt=prompt)
            return

        # If no attachments, proceed with text prompt
        prompt = prompt or INSTRUCTIONS['greeting']
        chat_session = self.model.start_chat()
        custom_instructions = f"{INSTRUCTIONS['freeform']} {prompt[:100]}"
        text_response = []
        responses = chat_session.send_message(custom_instructions, stream=True)
        for chunk in responses:
            text_response.append(chunk.text)
        return f"{''.join(text_response)}"

    @commands.command(name='ai')
    async def gemini(self, ctx, *, prompt: str = None):
        """Main command to interact with the Gemini Vertex AI API"""
        logger.info(f"{ctx.author} called the gemini command with prompt: {prompt}")
        if not self.check_debug_mode(ctx):
            return
        try:
            text_response = await self.process_and_generate_response(ctx, prompt)
            await ctx.send(text_response)
        except Exception as e:
            await ctx.send(f"Error: {str(e)}")

    @commands.command(name='ai-voice')
    async def gemini_voice(self, ctx, *, prompt: str = None):
        """Main command to interact with the Gemini Vertex AI API"""
        logger.info(f"{ctx.author} called the ai-voice command with prompt: {prompt}")
        try:
            await self.join(ctx)
            text_response = await self.process_and_generate_response(ctx, f"Keep your response short and sweet. Act like you are talking to a person. {prompt}")
            tts = gTTS(text_response, tld='ca', lang='en')
            tts.save('gemini.mp3')
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio('gemini.mp3'))
            await ctx.send(text_response)
            ctx.voice_client.play(source, after=lambda e: logger.error(f'Player error: {e}') if e else None)
            while ctx.voice_client.is_playing():
                await asyncio.sleep(1)
            await self.leave(ctx)
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            await ctx.send("You may need to join a voice channel first, or there is an issue with Gemini.")
    
    #@commands.command(name='ai-play')
    async def gemini_play(self, ctx, *, prompt: str = None):
        """Main command to interact with the Gemini Vertex AI API"""
        if not self.check_debug_mode(ctx):
            return

        try:
            # If no attachments, proceed with text prompt
            prompt = prompt or "Greet me like I am a new friend."
            chat_session = self.model.start_chat()
            custom_instructions = f"{INSTRUCTIONS['playsong']} {prompt[:100]}"
            text_response = []
            responses = chat_session.send_message(custom_instructions, stream=True)
            for chunk in responses:
                text_response.append(chunk.text)
            await ctx.send(f"/play {''.join(text_response)}")
        except Exception as e:
            await ctx.send(f"Error: {str(e)}")

    async def gemini_image(self, ctx, *, prompt: str = None):
        """Interacts with the Gemini Vertex AI API for images"""
        if ctx.message is None:
            # Fetch the last message in the channel
            async for msg in ctx.channel.history(limit=2):
                if msg.id != ctx.message.id:
                    ctx.message = msg
                    break

        if ctx.message is None:
            await ctx.send("No message found to extract image links from.")
            return

        # Print out all attachment URLs for testing
        attachment_urls = [attachment for attachment in ctx.message.attachments]
        print("Attachment URLs:", attachment_urls)

        # Check for image attachments using MIME type
        image_links = [(attachment.url, attachment.content_type) for attachment in ctx.message.attachments if attachment.content_type and attachment.content_type.startswith('image/')]

        if not image_links:
            await ctx.send("No image links found in attachments.")
            return

        image_link = image_links[0]

        print(f'ctx.author: {ctx.author}, command is: {ctx.command}')
        try:
            detect_safe_search_uri(image_link[0])
            image_file = Part.from_uri(image_link[0], image_link[1])
            if prompt:
                custom_instructions = INSTRUCTIONS.get(prompt, f"{INSTRUCTIONS['freeform']} {prompt[:100]}")
            else:
                custom_instructions = INSTRUCTIONS['image']
            response = self.model.generate_content([image_file, custom_instructions]).text
            await ctx.send(f"Response: {response}")
        except Exception as e:
            await ctx.send(f"Error: {str(e)}")

    async def gemini_video(self, ctx, *, prompt: str = None):
        """Interacts with the Gemini Vertex AI API for videos"""
        if ctx.message is None:
            # Fetch the last message in the channel
            async for msg in ctx.channel.history(limit=2):
                if msg.id != ctx.message.id:
                    ctx.message = msg
                    break

        if ctx.message is None:
            await ctx.send("No message found to extract video links from.")
            return

        # Check for video attachments using MIME type
        video_links = [(attachment.url, attachment.content_type) for attachment in ctx.message.attachments if attachment.content_type and attachment.content_type.startswith('video/')]

        if not video_links:
            await ctx.send("No video links found in attachments.")
            return

        video_link = video_links[0]

        print(f'ctx.author: {ctx.author}, command is: {ctx.command}')
        try:
            # Download the video file
            async with aiohttp.ClientSession() as session:
                async with session.get(video_link[0]) as response:
                    if response.status == 200:
                        video_path = f"temp_video.{video_link[1].split('/')[-1]}"
                        with open(video_path, 'wb') as f:
                            f.write(await response.read())
                    else:
                        await ctx.send("Failed to download the video.")
                        return

            # Upload the video file to Google Cloud Storage
            storage_client = storage.Client()
            bucket = storage_client.bucket(self.bucket_name)
            blob = bucket.blob(os.path.basename(video_path))
            blob.upload_from_filename(video_path)
            gcs_uri = f"gs://{self.bucket_name}/{blob.name}"

            # Use the GCS URI with Vertex AI
            video_file = Part.from_uri(gcs_uri, video_link[1])
            if prompt:
                custom_instructions = INSTRUCTIONS.get(prompt, f"{INSTRUCTIONS['freeform']} {prompt[:100]}")
            else:
                custom_instructions = INSTRUCTIONS['video']
            response = self.model.generate_content([video_file, custom_instructions]).text
            await ctx.send(f"Response: {response}")

            # Clean up the downloaded file and delete from GCS
            os.remove(video_path)
            blob.delete()
        except Exception as e:
            await ctx.send(f"Error: {str(e)}")
    
    async def gemini_document(self, ctx, *, prompt: str = None):
        """Interacts with the Gemini Vertex AI API for PDF and TXT files"""
        logger.info(f"{ctx.author} called the gemini_document function with prompt: {prompt}")
        if ctx.message is None:
            # Fetch the last message in the channel
            async for msg in ctx.channel.history(limit=2):
                if msg.id != ctx.message.id:
                    ctx.message = msg
                    break

        if ctx.message is None:
            await ctx.send("No message found to extract document links from.")
            return

        # Print out all attachment URLs for testing
        attachment_urls = [attachment for attachment in ctx.message.attachments]
        print("Attachment URLs:", attachment_urls)

        # Check for PDF and TXT attachments using MIME type
        document_links = [(attachment.url, attachment.content_type) for attachment in ctx.message.attachments if attachment.content_type and (attachment.content_type.startswith('application/pdf') or attachment.content_type.startswith('text/plain'))]

        if not document_links:
            await ctx.send("No PDF or TXT links found in attachments.")
            return
        print(f'document_links: {document_links}')
        document_link = document_links[0]

        print(f'ctx.author: {ctx.author}, command is: {ctx.command}')
        try:
            document_file = Part.from_uri(document_link[0], document_link[1])
            if prompt:
                custom_instructions = INSTRUCTIONS.get(prompt, f"{INSTRUCTIONS['freeform']} {prompt[:100]}")
            else:
                custom_instructions = INSTRUCTIONS['document']
            response = self.model.generate_content([document_file, custom_instructions]).text
            await ctx.send(f"Response: {response}")

        except Exception as e:
            await ctx.send(f"Error: {str(e)}")

    #@commands.command(name='imgen')
    async def imgen(self, ctx, *, prompt: str = None):
        """Generates an image based on the given prompt using ImageGenerationModel"""
        
        if not self.check_debug_mode(ctx):
            return

        print(f'ctx.author: {ctx.author}, command is: {ctx.command}, prompt: {prompt}')
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
                    image_response[0].save(location="temp_image.png")
                    await ctx.send(file=discord.File("temp_image.png"))
                    os.remove("temp_image.png")  # Clean up the downloaded file
                    break
            else:
                await ctx.send("Failed to generate images after 3 attempts.")

        except Exception as e:
            await ctx.send(f"Error: {str(e)}")

def detect_safe_search_uri(uri):
    """Detects unsafe features in the file located in Google Cloud Storage or
    on the Web."""

    client = vision.ImageAnnotatorClient()
    image = vision.Image()
    image.source.image_uri = uri

    response = client.safe_search_detection(image=image)
    safe = response.safe_search_annotation

    # Names of likelihood from google.cloud.vision.enums
    likelihood_name = (
        "UNKNOWN",
        "VERY_UNLIKELY",
        "UNLIKELY",
        "POSSIBLE",
        "LIKELY",
        "VERY_LIKELY",
    )
    print("Safe search:")

    print(f"adult: {likelihood_name[safe.adult]}")
    print(f"medical: {likelihood_name[safe.medical]}")
    print(f"spoofed: {likelihood_name[safe.spoof]}")
    print(f"violence: {likelihood_name[safe.violence]}")
    print(f"racy: {likelihood_name[safe.racy]}")

    if response.error.message:
        raise Exception(
            "{}\nFor more info on error messages, check: "
            "https://cloud.google.com/apis/design/errors".format(response.error.message)
        )


async def setup(bot):
    await bot.add_cog(GeminiCog(bot))