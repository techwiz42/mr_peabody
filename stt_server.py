#!/usr/bin/env python3
"""
Server script to run on Digital Ocean droplet
Receives audio data from client and transcribes using Google Speech-to-Text API
"""
import os
import io
import socket
import wave
import threading
from dotenv import load_dotenv
from google.cloud import speech_v1 as speech
from google.api_core.client_options import ClientOptions

def load_environment():
    """Load environment variables from .env file"""
    load_dotenv()
    # Verify required variables are loaded
    required_vars = ['GOOGLE_API_KEY']
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")
    print(f"Environment loaded successfully (using GOOGLE_API_KEY)")

def transcribe_audio_file(audio_content, sample_rate_hertz=16000):
    """Transcribe the given audio data using Google Speech-to-Text API with API key"""
    # Set up client with API key
    api_key = os.getenv("GOOGLE_API_KEY")
    client_options = ClientOptions(api_key=api_key)
    client = speech.SpeechClient(client_options=client_options)
    
    # Configure audio settings
    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=sample_rate_hertz,
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
    
    # Format results as text
    result_text = ""
    if not results:
        result_text = "No transcription results returned. The audio might be silent or unclear."
    else:
        for i, result in enumerate(results, 1):
            result_text += f"Result {i}:\n"
            result_text += f"  Transcript: {result['transcript']}\n"
            result_text += f"  Confidence: {result['confidence']:.4f}\n"
    
    return result_text

def handle_client(client_socket, client_address):
    """Handle individual client connection"""
    print(f"Connection from {client_address}")
    
    try:
        # First receive the audio format information
        format_info = client_socket.recv(1024).decode('utf-8')
        rate, channels, sample_width = map(int, format_info.split(','))
        print(f"Audio format: {rate}Hz, {channels} channels, {sample_width} bytes per sample")
        
        # Send acknowledgment
        client_socket.sendall(b"ACK")
        
        # Receive audio data
        print("Receiving audio data...")
        audio_data = b""
        while True:
            chunk = client_socket.recv(4096)
            if b"END" in chunk:
                audio_data += chunk.split(b"END")[0]
                break
            if not chunk:
                break
            audio_data += chunk
        
        print(f"Received {len(audio_data)} bytes of audio data")
        
        # Save the received audio to a temporary WAV file
        temp_file = f"received_{client_address[0]}_{client_address[1]}.wav"
        with wave.open(temp_file, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(audio_data)
        
        # Read the file in a format compatible with Google's API
        with open(temp_file, 'rb') as audio_file:
            audio_content = audio_file.read()
        
        # Transcribe the audio
        transcription = transcribe_audio_file(audio_content, rate)
        print("Transcription completed")
        
        # Send the transcription back to the client
        client_socket.sendall(transcription.encode('utf-8'))
        client_socket.sendall(b"END_TRANSCRIPTION")
        
        # Clean up temporary file
        os.remove(temp_file)
        
    except Exception as e:
        print(f"Error handling client {client_address}: {e}")
    finally:
        client_socket.close()
        print(f"Connection with {client_address} closed")

def start_server(port=12345):
    """Start the server to listen for incoming audio data"""
    # Load environment variables
    load_environment()
    
    # Create a socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Enable address reuse
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Bind to all interfaces
    server_socket.bind(('0.0.0.0', port))
    
    # Listen for incoming connections
    server_socket.listen(5)
    print(f"Server listening on port {port}...")
    
    try:
        while True:
            # Accept client connection
            client_socket, client_address = server_socket.accept()
            
            # Handle client in a new thread
            client_thread = threading.Thread(
                target=handle_client, 
                args=(client_socket, client_address)
            )
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    finally:
        server_socket.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Server for speech-to-text transcription')
    parser.add_argument('--port', '-p', type=int, default=12345, 
                        help='Port to listen on (default: 12345)')
    
    args = parser.parse_args()
    start_server(args.port)
