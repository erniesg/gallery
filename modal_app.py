from modal import App, Image, Volume
import moviepy.editor as mp
from pathlib import Path
import whisper
from loguru import logger
import os
import asyncio
from datetime import datetime
import io
import tempfile
import torch

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
)

# Initialize the Modal app with the custom image
app = App("video-audio-transcription-app", image=app_image)

# Define the volume for audio and video storage
volume = Volume.from_name("audio-storage", create_if_missing=True)

def extract_audio_locally(video_file_path):
    logger.info(f"Extracting audio from video: {video_file_path}")
    try:
        video = mp.VideoFileClip(video_file_path)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        audio_file_name = f"{timestamp}_{Path(video_file_path).stem}.mp3"
        audio_file_path = Path(tempfile.gettempdir()) / audio_file_name
        video.audio.write_audiofile(str(audio_file_path))
        logger.info(f"Audio extracted and saved to: {audio_file_path}")
        return str(audio_file_path)
    except Exception as e:
        logger.error(f"Failed to extract audio: {str(e)}")
        raise

def save_transcription(output_directory, filename, plain_text, srt_subtitles):
    logger.info(f"Saving transcription for {filename}")
    try:
        with volume.batch_upload() as batch:
            batch.put_file(io.BytesIO(plain_text.encode("utf-8")), f"{output_directory}/{filename}.txt")
            batch.put_file(io.BytesIO(srt_subtitles.encode("utf-8")), f"{output_directory}/{filename}.srt")
        logger.info("Transcription files saved successfully")
    except Exception as e:
        logger.error(f"Error saving transcription files: {str(e)}")
        raise

@app.function(gpu="any", volumes={"/media": volume}, _allow_background_volume_commits=True)
async def transcribe_audio(remote_audio_path):
    # Use CUDA, if available
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {DEVICE}")

    logger.info(f"Transcribing audio from path: {remote_audio_path}")
    logger.info("Reloading volume to get the latest committed state")
    try:
        volume.reload()
        logger.info("Volume reloaded successfully")
        files = list(volume.iterdir("/media"))
        logger.info(f"All files in volume: {[file.path for file in files]}")
        for file_entry in files:
            logger.info(f"File entry after reload: {file_entry.path}")
    except Exception as e:
        logger.error(f"Error reloading volume or listing files: {str(e)}")
        raise

    # Remove leading slash if present
    remote_audio_path = remote_audio_path.lstrip('/')
    logger.info(f"Formatted path for reading: {remote_audio_path}")

    try:
        audio_data = b""
        logger.info(f"Attempting to read file at path: {remote_audio_path}")
        for chunk in volume.read_file(remote_audio_path):
            audio_data += chunk
        logger.info("Audio file read successfully")
    except Exception as e:
        logger.error(f"Error reading audio file: {str(e)}")
        raise

    logger.info("Saving audio data to a temporary file")
    try:
        # Save the audio data to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio_file:
            temp_audio_file.write(audio_data)
            temp_audio_path = temp_audio_file.name
        logger.info("Audio data saved to a temporary file")
    except Exception as e:
        logger.error(f"Error saving audio data to a temporary file: {str(e)}")
        raise

    logger.info("Loading Whisper model")
    try:
        model = whisper.load_model("large").to(DEVICE)
        logger.info("Whisper model loaded successfully")
    except Exception as e:
        logger.error(f"Error loading Whisper model: {str(e)}")
        raise

    logger.info("Transcribing audio")
    try:
        result = model.transcribe(temp_audio_path, verbose=False, language="en")
        logger.info("Transcription completed")

        plain_text = result["text"]
        srt_writer = whisper.utils.WriteSRT("") # Create an instance of the WriteSRT class
        srt_buffer = io.StringIO() # Create a StringIO buffer to write the SRT subtitles
        srt_writer.write_result(result, srt_buffer) # Write the SRT subtitles to the buffer
        srt_subtitles = srt_buffer.getvalue() # Get the SRT subtitles as a string

        return plain_text, srt_subtitles
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
    local_audio_path = extract_audio_locally(local_video_path)

    # Get the filename from the local audio path
    audio_filename = Path(local_audio_path).name

    # Upload the audio file to the volume using the same filename
    remote_audio_path = f"/media/{audio_filename}"
    logger.info(f"Remote audio path: {remote_audio_path}")

    try:
        with volume.batch_upload() as batch:
            batch.put_file(local_audio_path, remote_audio_path)
        logger.info(f"File uploaded successfully.")

        for file_entry in volume.iterdir(str(remote_audio_path)):
            logger.info(f"File in remote: {file_entry.path}")
    except Exception as e:
        logger.error(f"Failed to upload file: {str(e)}")
        raise

    # Remove the local audio file after uploading
    try:
        os.remove(local_audio_path)
        logger.info(f"Local audio file {local_audio_path} removed")
    except Exception as e:
        logger.error(f"Failed to remove local audio file: {str(e)}")

    # Transcribe the audio from the volume
    plain_text, srt_subtitles = transcribe_audio.remote(remote_audio_path)

    # Print the first 150 words of the plain text
    print("First 150 words of plain text:")
    print(" ".join(plain_text.split()[:150]) + " ...")

    print("\nFirst 8 lines of SRT subtitles:")
    print("\n".join(srt_subtitles.split("\n")[:8]))

    # Save the transcription files to the remote volume
    output_directory = "/media/transcriptions"
    save_transcription(output_directory, Path(audio_filename).stem, plain_text, srt_subtitles)
