from modal import App, Image, Volume
import moviepy.editor as mp
from pathlib import Path
import whisper
from loguru import logger
import shutil
import os
import asyncio
from datetime import datetime
import time
import os
import io
from pathlib import Path
import tempfile

# Setup logger
logger.add("debug.log", rotation="10 MB")

# Define the Docker image with necessary dependencies
app_image = (
    Image.debian_slim(python_version="3.10")
    .apt_install("git")
    .pip_install(
        "git+https://github.com/openai/whisper.git",
        "dacite",
        "jiwer",
        "ffmpeg-python",
        "gql[all]~=3.0.0a5",
        "python-multipart~=0.0.9",
        "pandas",
        "loguru==0.6.0",
        "torchaudio==2.1.0",
        "moviepy"
    )
    .apt_install("ffmpeg")
    .pip_install("ffmpeg-python")
)

# Initialize the Modal app with the custom image
app = App("video-audio-transcription-app", image=app_image)

# Define the volume for audio and video storage
storage_volume = Volume.from_name("storage", create_if_missing=True)

@app.function(volumes={"/media": storage_volume})
def upload_audio_to_volume(volume, local_audio_path, volume_audio_path):
    logger.info(f"File ready at {volume_audio_path}, ensuring it's committed.")
    try:
        volume.commit()  # Commit changes to ensure they are visible remotely
        logger.info(f"Changes committed successfully.")
        return "Commit successful"  # Return a success message
    except Exception as e:
        logger.error(f"Failed to commit changes: {str(e)}")
        return f"Commit failed: {str(e)}"  # Return an error message

def extract_audio_locally(video_file_path):
    logger.info(f"Extracting audio from video: {video_file_path}")
    try:
        video = mp.VideoFileClip(video_file_path)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        audio_file_name = f"{timestamp}_{Path(video_file_path).stem}.mp3"
        audio_file_path = Path(video_file_path).parent / audio_file_name
        video.audio.write_audiofile(str(audio_file_path))
        logger.info(f"Audio extracted and saved to: {audio_file_path}")
        return str(audio_file_path)
    except Exception as e:
        logger.error(f"Failed to extract audio: {str(e)}")
        raise

@app.function(volumes={"/media": storage_volume})
async def transcribe_audio(audio_data: bytes):
    logger.info("Loading audio data from memory")
    try:
        # Create a temporary file with the audio data
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio_file:
            temp_audio_file.write(audio_data)
            temp_audio_path = temp_audio_file.name

        # Load the audio using AudioFileClip
        audio = mp.AudioFileClip(temp_audio_path)
        logger.info("Audio data loaded successfully")
    except Exception as e:
        logger.error(f"Error loading audio data: {str(e)}")
        raise

    logger.info("Loading Whisper model")
    try:
        model = whisper.load_model("base")
        logger.info("Whisper model loaded successfully")
    except Exception as e:
        logger.error(f"Error loading Whisper model: {str(e)}")
        raise

    logger.info("Transcribing audio")
    try:
        result = model.transcribe(temp_audio_path)
        logger.info("Transcription completed")
        return result["text"]
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        raise
    finally:
        # Remove the temporary audio file
        os.unlink(temp_audio_path)

# Local entrypoint to chain the functions and execute the workflow
@app.local_entrypoint()
async def main():
    local_video_path = "/Users/erniesg/Movies/video.mov"
    logger.info(f"Starting processing for: {local_video_path}")
    try:
        local_audio_path = extract_audio_locally(local_video_path)
        logger.info(f"Local audio path: {local_audio_path}.")

        with open(local_audio_path, "rb") as f:
            audio_data = f.read()

        logger.info(f"Invoking transcription on audio data.")
        transcription = transcribe_audio.remote(audio_data)
        logger.info(f"Transcription result: {transcription}")
        print(transcription)
    except Exception as e:
        logger.error(f"Error in processing workflow: {str(e)}")
