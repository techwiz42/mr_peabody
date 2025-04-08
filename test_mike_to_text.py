#!/usr/bin/env python3
"""
Test script for Google's Speech-to-Text API using microphone input
Records audio from the microphone and sends it to Google's API for transcription
"""
import os
import io
import time
import pyaudio
import wave
import threading
from dotenv import load_dotenv
from google.cloud import speech_v1 as speech
from google.api_core.client_options import ClientOptions

# Audio recording parameters
RATE = 16000  # Sample rate
CHUNK = 1024  # Buffer size
FORMAT = pyaudio.paInt16  # 16-bit audio
CHANNELS = 1  # Mono audio
RECORD_SECONDS = 5  # Duration to record (adjust as needed)

def load_environment():
    """Load environment variables from .env file"""
    load_dotenv()
    # Verify required variables are loaded
    required_vars = ['GOOGLE_API_KEY']
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")
    print(f"Environment loaded successfully (using GOOGLE_API_KEY)")

def record_audio(output_filename="recording.wav"):
    """Record audio from the microphone and save to a WAV file"""
    p = pyaudio.PyAudio()
    
    # Open audio stream
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    print(f"Recording for {RECORD_SECONDS} seconds...")
    frames = []
    
    # Start recording with a visual indicator
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
        # Print a simple progress indicator
        if i % 10 == 0:
            dots = "." * (i // 10 % 4)
            print(f"\rRecording{dots:<3}", end="")
    
    print("\nFinished recording!")
    
    # Stop and close the stream
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    # Save the recorded audio as a WAV file
    wf = wave.open(output_filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    return output_filename

def transcribe_audio_file(file_path):
    """Transcribe the given audio file using Google Speech-to-Text API with API key"""
    # Set up client with API key
    api_key = os.getenv("GOOGLE_API_KEY")
    client_options = ClientOptions(api_key=api_key)
    client = speech.SpeechClient(client_options=client_options)
    
    # Read audio file
    with io.open(file_path, "rb") as audio_file:
        content = audio_file.read()
    
    # Configure audio settings
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="en-US",
        enable_automatic_punctuation=True,
    )
    
    # Perform the transcription
    print("Sending audio to Google Speech-to-Text API...")
    response = client.recognize(config=config, audio=audio)
    
    # Process and return results
    results = []
    for result in response.results:
        for alternative in result.alternatives:
            results.append({
                "transcript": alternative.transcript,
                "confidence": alternative.confidence
            })
    
    return results

def streaming_transcribe():
    """
    For longer recordings, use streaming recognition
    This is a placeholder for future implementation
    """
    print("Streaming transcription not implemented in this version.")
    print("For longer recordings, consider implementing streaming recognition.")

def main():
    """Main function to test Google's Speech-to-Text API with microphone input"""
    try:
        # Load environment variables
        load_environment()
        
        # Record audio from microphone
        audio_file_path = record_audio()
        
        # Transcribe the recorded audio
        results = transcribe_audio_file(audio_file_path)
        
        # Display results
        print("\nTranscription Results:")
        print("---------------------")
        if not results:
            print("No transcription results returned. The audio might be silent or unclear.")
        
        for i, result in enumerate(results, 1):
            print(f"Result {i}:")
            print(f"  Transcript: {result['transcript']}")
            print(f"  Confidence: {result['confidence']:.4f}")
        
    except KeyboardInterrupt:
        print("\nRecording stopped by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
