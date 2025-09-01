from google.cloud import storage, vision
import os
import logging
import aiohttp
import vertexai
from vertexai.generative_models import Part

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

logger = logging.getLogger(__name__)

def detect_safe_search_uri(uri):
    """Detects unsafe features in the file located in Google Cloud Storage or on the Web."""
    client = vision.ImageAnnotatorClient()
    image = vision.Image()
    image.source.image_uri = uri

    response = client.safe_search_detection(image=image) # type: ignore
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

async def gemini_image(ctx, model, bucket_name, prompt: str = '', dont_modify_prompt: bool = False):
    """Interacts with the Gemini Vertex AI API for images"""
    logger.info(f"{ctx.author} called the gemini_image function with prompt: {prompt}")
    if ctx.message is None:
        # Fetch the last message in the channel
        async for msg in ctx.channel.history(limit=2):
            if msg.id != ctx.message.id:
                ctx.message = msg
                break

    if ctx.message is None:
        return "No message found to extract image links from."

    # Check for image attachments using MIME type
    image_links = [(attachment.url, attachment.content_type) for attachment in ctx.message.attachments if attachment.content_type and attachment.content_type.startswith('image/')]

    if not image_links:
        return "No image links found in attachments."

    image_link = image_links[0]

    try:
        # Download the image file
        async with aiohttp.ClientSession() as session:
            async with session.get(image_link[0]) as response:
                if response.status == 200:
                    image_path = f"temp_image_{ctx.message.id}.{image_link[1].split('/')[-1]}"
                    with open(image_path, 'wb') as f:
                        f.write(await response.read())
                else:
                    logger.error(f"Failed to download image from {image_link[0]}. Status: {response.status}")
                    return "Failed to download the image."

        # Upload the image file to Google Cloud Storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(os.path.basename(image_path))
        blob.upload_from_filename(image_path)
        logger.info(f"Uploaded {image_path} to GCS bucket {bucket_name} as {blob.name}")
        gcs_uri = f"gs://{bucket_name}/{blob.name}"

        # Use the GCS URI with Vertex AI
        image_file = Part.from_uri(gcs_uri, image_link[1])
        if dont_modify_prompt:
            custom_instructions = prompt + '.. Image is attached.'
        else:
            if prompt:
                custom_instructions = INSTRUCTIONS.get(prompt, f"{INSTRUCTIONS['freeform']} : {prompt}")
            else:
                custom_instructions = INSTRUCTIONS['image']
        logger.info(f"Custom instructions for image processing: {custom_instructions}")
        response = model.generate_content([image_file, custom_instructions]).text
        logger.info(f"Generated content for image: {response}")

        # Clean up the downloaded file and delete from GCS
        os.remove(image_path)
        blob.delete()
        logger.info(f"Cleaned up temporary image file {image_path} and deleted {blob.name} from GCS.")

        return response
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return f"Error: {str(e)}"

async def gemini_video(ctx, model, bucket_name, prompt: str = '', dont_modify_prompt: bool = False):
    """Interacts with the Gemini Vertex AI API for videos"""
    logger.info(f"{ctx.author} called the gemini_video function with prompt: {prompt}")
    if ctx.message is None:
        # Fetch the last message in the channel
        async for msg in ctx.channel.history(limit=2):
            if msg.id != ctx.message.id:
                ctx.message = msg
                break

    if ctx.message is None:
        return "No message found to extract video links from."

    # Check for video attachments using MIME type
    video_links = [(attachment.url, attachment.content_type) for attachment in ctx.message.attachments if attachment.content_type and attachment.content_type.startswith('video/')]

    if not video_links:
        return "No video links found in attachments."

    video_link = video_links[0]

    try:
        # Download the video file
        async with aiohttp.ClientSession() as session:
            async with session.get(video_link[0]) as response:
                if response.status == 200:
                    video_path = f"temp_video.{video_link[1].split('/')[-1]}"
                    with open(video_path, 'wb') as f:
                        f.write(await response.read())
                else:
                    return "Failed to download the video."

        # Upload the video file to Google Cloud Storage
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(os.path.basename(video_path))
        blob.upload_from_filename(video_path)
        gcs_uri = f"gs://{bucket_name}/{blob.name}"

        # Use the GCS URI with Vertex AI
        video_file = Part.from_uri(gcs_uri, video_link[1])
        if dont_modify_prompt:
            custom_instructions = prompt + '.. Video is attached.'
        else:
            if prompt:
                custom_instructions = INSTRUCTIONS.get(prompt, f"{INSTRUCTIONS['freeform']} { prompt}")
            else:
                custom_instructions = INSTRUCTIONS['video']
        response = model.generate_content([video_file, custom_instructions]).text

        # Clean up the downloaded file and delete from GCS
        os.remove(video_path)
        blob.delete()

        return response
    except Exception as e:
        return f"Error: {str(e)}"

async def gemini_document(ctx, model, prompt: str = '', dont_modify_prompt: bool = False):
    """Interacts with the Gemini Vertex AI API for documents"""
    logger.info(f"{ctx.author} called the gemini_document function with prompt: {prompt}")
    if ctx.message is None:
        # Fetch the last message in the channel
        async for msg in ctx.channel.history(limit=2):
            if msg.id != ctx.message.id:
                ctx.message = msg
                break

    if ctx.message is None:
        return "No message found to extract document links from."

    # Check for document attachments using MIME type
    document_links = [(attachment.url, attachment.content_type) for attachment in ctx.message.attachments if attachment.content_type and (attachment.content_type.startswith('application/pdf') or attachment.content_type.startswith('text/plain'))]

    if not document_links:
        return "No document links found in attachments."

    document_link = document_links[0]

    try:
        document_file = Part.from_uri(document_link[0], document_link[1])
        if dont_modify_prompt:
            custom_instructions = prompt + '.. Document is attached.'
        else:
            if prompt:
                custom_instructions = INSTRUCTIONS.get(prompt, f"{INSTRUCTIONS['freeform']} {prompt}")
            else:
                custom_instructions = INSTRUCTIONS['document']
        response = model.generate_content([document_file, custom_instructions]).text
        return response
    except Exception as e:
        return f"Error: {str(e)}"

async def process_and_generate_response(ctx, model, bucket_name, prompt: str = '', dont_modify_prompt: bool = False):
    """Processes attachments and generates a response using the Gemini Vertex AI API"""
    # Check for image, video, or document links
    image_links = [(attachment.url, attachment.content_type) for attachment in ctx.message.attachments if attachment.content_type and attachment.content_type.startswith('image/')]
    video_links = [(attachment.url, attachment.content_type) for attachment in ctx.message.attachments if attachment.content_type and attachment.content_type.startswith('video/')]
    document_links = [(attachment.url, attachment.content_type) for attachment in ctx.message.attachments if attachment.content_type and (attachment.content_type.startswith('application/pdf') or attachment.content_type.startswith('text/plain'))]

    if image_links:
        logger.info(f"{ctx.author} has sent an image attachment. Proccessing...")
        return await gemini_image(ctx, model, bucket_name, prompt=prompt, dont_modify_prompt=dont_modify_prompt)
    if video_links:
        logger.info(f"{ctx.author} has sent a video attachment. Proccessing...")
        return await gemini_video(ctx, model, bucket_name, prompt=prompt, dont_modify_prompt=dont_modify_prompt)
    if document_links:
        logger.info(f"{ctx.author} has sent a document attachment. Proccessing...")
        return await gemini_document(ctx, model, prompt=prompt, dont_modify_prompt=dont_modify_prompt)

    # If no attachments, proceed with text prompt
    prompt = prompt or INSTRUCTIONS['greeting']
    chat_session = model.start_chat()
    if dont_modify_prompt:
        custom_instructions = prompt
    else:
        custom_instructions = f"{INSTRUCTIONS['freeform']} {prompt}"
    text_response = []
    responses = chat_session.send_message(custom_instructions, stream=True)
    for chunk in responses:
        text_response.append(chunk.text)
    return ''.join(text_response)