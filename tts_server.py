#!/usr/bin/env python3
"""
Server script to run on Digital Ocean droplet
Receives text from client and synthesizes speech using Google Text-to-Speech API
Then sends the audio data back to the client for playback
"""
import os
import io
import socket
import threading
import argparse
from dotenv import load_dotenv
from google.cloud import texttospeech
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

def synthesize_text(text, voice_name="en-US-Neural2-F", language_code="en-US", speaking_rate=1.0):
    """Convert text to speech using Google Text-to-Speech API with API key"""
    # Set up client with API key
    api_key = os.getenv("GOOGLE_API_KEY")
    client_options = ClientOptions(api_key=api_key)
    client = texttospeech.TextToSpeechClient(client_options=client_options)
    
    # Build the synthesis input
    synthesis_input = texttospeech.SynthesisInput(text=text)
    
    # Build the voice request
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name
    )
    
    # Select the audio config
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speaking_rate
    )
    
    # Perform the text-to-speech request
    print(f"Synthesizing speech for: '{text[:50]}...' (if longer)")
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    
    # Return the audio content
    return response.audio_content

def handle_client(client_socket, client_address):
    """Handle individual client connection"""
    print(f"Connection from {client_address}")
    
    try:
        # Receive the TTS request
        data = b""
        while True:
            chunk = client_socket.recv(4096)
            if b"END_REQUEST" in chunk:
                data += chunk.split(b"END_REQUEST")[0]
                break
            if not chunk:
                break
            data += chunk
        
        # Parse the request
        request_text = data.decode('utf-8')
        
        # Check if the request has voice parameters (JSON format)
        voice_name = "en-US-Neural2-F"  # default
        language_code = "en-US"  # default
        speaking_rate = 1.0  # default
        
        # Split the request if it contains voice parameters
        # Format: VOICE_PARAMS||voice_name||language_code||speaking_rate||TEXT
        if "VOICE_PARAMS||" in request_text:
            parts = request_text.split("||", 4)
            if len(parts) >= 4:
                voice_name = parts[1] or voice_name
                language_code = parts[2] or language_code
                try:
                    speaking_rate = float(parts[3]) if parts[3] else speaking_rate
                except ValueError:
                    pass
                request_text = parts[4] if len(parts) > 4 else ""
        
        print(f"Received text: '{request_text[:50]}...' (if longer)")
        print(f"Voice settings: {voice_name}, {language_code}, rate={speaking_rate}")
        
        # Generate speech from text
        try:
            audio_content = synthesize_text(
                request_text, 
                voice_name=voice_name,
                language_code=language_code,
                speaking_rate=speaking_rate
            )
            
            # Send audio size first for the client to prepare
            audio_size = len(audio_content)
            client_socket.sendall(f"{audio_size}\n".encode('utf-8'))
            
            # Send the audio data
            client_socket.sendall(audio_content)
            client_socket.sendall(b"END_AUDIO")
            
            print(f"Sent {audio_size} bytes of audio data to {client_address}")
            
        except Exception as e:
            error_msg = f"Error synthesizing speech: {str(e)}"
            print(error_msg)
            client_socket.sendall(f"ERROR: {error_msg}".encode('utf-8'))
            
    except Exception as e:
        print(f"Error handling client {client_address}: {e}")
    finally:
        client_socket.close()
        print(f"Connection with {client_address} closed")

def list_available_voices():
    """List all available voices from Google TTS API"""
    try:
        # Set up client with API key
        api_key = os.getenv("GOOGLE_API_KEY")
        client_options = ClientOptions(api_key=api_key)
        client = texttospeech.TextToSpeechClient(client_options=client_options)
        
        # List all available voices
        voices = client.list_voices()
        
        print("Available voices:")
        for voice in voices.voices:
            languages = ", ".join(voice.language_codes)
            gender = texttospeech.SsmlVoiceGender(voice.ssml_gender).name
            print(f"Name: {voice.name}")
            print(f"  Language codes: {languages}")
            print(f"  Gender: {gender}")
            print(f"  Natural sample rate: {voice.natural_sample_rate_hertz}Hz")
            print()
            
    except Exception as e:
        print(f"Error listing voices: {e}")

def start_server(port=12345, list_voices=False):
    """Start the server to listen for incoming text requests"""
    # Load environment variables
    load_environment()
    
    # List available voices if requested
    if list_voices:
        list_available_voices()
    
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
    parser = argparse.ArgumentParser(description='Server for text-to-speech synthesis')
    parser.add_argument('--port', '-p', type=int, default=12345, 
                        help='Port to listen on (default: 12345)')
    parser.add_argument('--list-voices', '-l', action='store_true',
                        help='List all available voices')
    
    args = parser.parse_args()
    start_server(args.port, args.list_voices)
