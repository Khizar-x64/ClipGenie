import whisper
import torch
from moviepy import VideoFileClip, concatenate_videoclips
import time
from sentence_transformers import SentenceTransformer, util
import os
import logging
import traceback
from storage_manager import StorageManager

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

WHISPER_MODEL_SIZE = "base"  # Can be tiny, base, small, medium, large

# Initialize storage manager
storage_mgr = StorageManager()

def process_video(video_path, user_input, upload_folder, summarized_folder, user_id=None):
    try:
        # Generate unique filenames
        base_filename = os.path.splitext(os.path.basename(video_path))[0]
        audio_path = os.path.join(upload_folder, f"{base_filename}_audio.mp3")
        transcription_file_path = os.path.join(upload_folder, f"{base_filename}_transcription.txt")
        output_video_path = os.path.join(summarized_folder, f"{base_filename}_output.mp4")

        # Convert all paths to absolute paths
        audio_path = os.path.abspath(audio_path)
        transcription_file_path = os.path.abspath(transcription_file_path)
        output_video_path = os.path.abspath(output_video_path)

        logger.info(f"Video path: {video_path}")
        logger.info(f"Audio path: {audio_path}")
        logger.info(f"Transcription path: {transcription_file_path}")
        logger.info(f"Output path: {output_video_path}")

        # Step 1: Extract audio
        logger.info("Extracting audio from video...")
        with VideoFileClip(video_path) as video_clip:
            video_clip.audio.write_audiofile(audio_path)
        logger.info("Audio extraction completed")

        # Step 2: Load Whisper model and transcribe
        logger.info(f"Loading Whisper model: {WHISPER_MODEL_SIZE}")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        
        model = whisper.load_model(WHISPER_MODEL_SIZE, device=device)
        
        start = time.time()
        logger.info(f"Starting transcription of file: {audio_path}")
        result = model.transcribe(audio_path, fp16=False)
        logger.info("Transcription completed successfully")
        end = time.time()
        logger.info(f"Transcription completed in {end - start:.2f} seconds")

        # Write full transcription to file
        logger.info("Writing full transcription to file...")
        with open(transcription_file_path, 'w', encoding='utf-8') as file:
            for segment in result['segments']:
                file.write(f"{segment['start']:.2f}s {segment['end']:.2f}s {segment['text']}\n")
        logger.info(f"Full transcription saved at {transcription_file_path}")

        # Process segments
        segments = process_segments(result['segments'], user_input, video_path)

        # Create final video and save its transcript
        output_video_path = create_final_video(video_path, segments, output_video_path, summarized_folder)

        # If user is logged in, move to summarized folder and upload to Firebase
        if user_id:
            storage_result = storage_mgr.process_video_storage(output_video_path, user_id)
            return storage_result
        
        return {'local_path': output_video_path, 'firebase_url': None}

    except Exception as e:
        logger.error(f"Error in process_video: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    finally:
        # Cleanup temporary audio file only
        try:
            if os.path.exists(audio_path):
                os.remove(audio_path)
                logger.info("Temporary audio file cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def process_segments(segments, user_input, video_path):
    with VideoFileClip(video_path) as video_clip:
        video_duration = video_clip.duration

    segments_data = [{"start": segment['start'], 
                     "end": segment['end'], 
                     "text": segment['text']} 
                    for segment in segments]

    # Ensure segments do not exceed video duration
    filtered_segments = []
    for segment in segments_data:
        if segment["start"] >= video_duration:
            logger.warning(f"Skipping segment {segment['start']}s - {segment['end']}s (out of bounds)")
            continue
        segment["end"] = min(segment["end"], video_duration)
        filtered_segments.append(segment)

    segments_text = [segment["text"] for segment in filtered_segments]

    # Generate embeddings
    logger.info("Generating embeddings for segments...")
    model_sentence = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model_sentence.encode(segments_text)

    logger.info(f"Calculating similarity scores for prompt: {user_input}")
    query_embedding = model_sentence.encode([user_input])
    similarity_scores = util.pytorch_cos_sim(query_embedding, embeddings)
    scores = similarity_scores[0].tolist()

    # Sort and select segments
    scored_segments = sorted(zip(filtered_segments, scores), key=lambda x: x[1], reverse=True)
    top_n = 20
    chosen_segments = [
        {"start": segment["start"], "end": segment["end"], "text": segment["text"]}
        for segment, _ in scored_segments[:top_n]
    ]
    chosen_segments.sort(key=lambda x: x["start"])

    return merge_segments_with_constraints(chosen_segments)

def create_final_video(video_path, segments, output_video_path, summarized_folder):
    logger.info("Creating final video...")
    video_segments = []

    output_transcription_file_path = os.path.join(summarized_folder, f"{os.path.basename(output_video_path)}_transcription.txt")

    with VideoFileClip(video_path) as video_clip:
        video_duration = video_clip.duration

        with open(output_transcription_file_path, 'w', encoding='utf-8') as file:
            for segment in segments:
                try:
                    start_time = segment["start"]
                    end_time = min(segment["end"], video_duration)

                    if start_time >= video_duration:
                        logger.warning(f"Skipping segment {start_time}s - {end_time}s (out of bounds)")
                        continue

                    logger.info(f"Extracting video from {start_time}s to {end_time}s")
                    video_segment = video_clip.subclipped(start_time, end_time)
                    video_segments.append(video_segment)

                    # Write output transcript
                    file.write(f"{start_time:.2f}s {end_time:.2f}s {segment['text']}\n")

                except Exception as e:
                    logger.error(f"Error extracting segment {segment}: {str(e)}")
                    logger.error(traceback.format_exc())

        if video_segments:
            logger.info(f"Combining {len(video_segments)} video segments...")
            final_video = concatenate_videoclips(video_segments, method="chain")

            start = time.time()
            final_video.write_videofile(
                output_video_path,
                codec="libx264",
                audio_codec="aac",
                fps=30,
                bitrate="1670k",
                threads=0,
                preset="ultrafast"
            )
            end = time.time()
            logger.info(f"Video export completed in {end - start:.2f} seconds")

            # Clean up video segments
            for segment in video_segments:
                segment.close()
            final_video.close()
        else:
            logger.warning("No video segments to combine")

    return output_video_path

def merge_segments_with_constraints(segments, min_cut_duration=15.0, close_gap=10.0, max_total_duration=480.0):
    merged_segments = []
    last_segment = None
    total_duration = 0.0

    for segment in segments:
        segment_duration = segment["end"] - segment["start"]

        if segment_duration < min_cut_duration:
            segment["end"] = segment["start"] + min_cut_duration

        adjusted_duration = segment["end"] - segment["start"]
        if total_duration + adjusted_duration > max_total_duration:
            break

        if last_segment and segment["start"] - last_segment["end"] <= close_gap:
            last_segment["end"] = max(last_segment["end"], segment["end"])
        else:
            if last_segment:
                merged_segments.append(last_segment)
                total_duration += last_segment["end"] - last_segment["start"]
            last_segment = segment

    if last_segment:
        merged_segments.append(last_segment)

    return merged_segments
