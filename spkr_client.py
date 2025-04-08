#!/usr/bin/env python3
"""
Client script that sends text to a server running on a Digital Ocean droplet
and plays the synthesized speech on local speakers
"""
import os
import io
import socket
import argparse
import pygame
import tempfile
import threading
import time
import sys

def send_text_and_play_speech(server_ip, server_port, text, voice_name=None, 
                             language_code=None, speaking_rate=None, save_file=None):
    """Send text to server for TTS processing and play the returned audio"""
    # Initialize pygame for audio playback
    pygame.init()
    pygame.mixer.init()
    
    print(f"Connecting to server at {server_ip}:{server_port}...")
    
    # Create socket and connect to server
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((server_ip, server_port))
    except ConnectionRefusedError:
        print("Error: Could not connect to server. Make sure the server is running.")
        return
    
    # Prepare request - add voice parameters if provided
    if voice_name or language_code or speaking_rate:
        request = f"VOICE_PARAMS||{voice_name or ''}||{language_code or ''}||{speaking_rate or ''}||{text}"
    else:
        request = text
    
    print(f"Sending text: '{text[:50]}...' (if longer)")
    
    # Send the text to the server
    client_socket.sendall(request.encode('utf-8'))
    client_socket.sendall(b"END_REQUEST")
    
    # Receive the audio data
    print("Waiting for speech synthesis...")
    
    # First get the audio size
    size_data = b""
    while b'\n' not in size_data:
        chunk = client_socket.recv(1024)
        if not chunk:
            break
        size_data += chunk
    
    # Check for error message
    size_str = size_data.split(b'\n')[0].decode('utf-8')
    if size_str.startswith("ERROR:"):
        print(size_str)
        client_socket.close()
        return
    
    try:
        expected_size = int(size_str)
        print(f"Expecting {expected_size} bytes of audio data")
    except ValueError:
        print("Error parsing audio size from server")
        client_socket.close()
        return
    
    # Get remaining data after the newline
    audio_data = size_data.split(b'\n', 1)[1] if b'\n' in size_data else b""
    
    # Create a temporary file to store the audio
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
        temp_filename = temp_file.name
        temp_file.write(audio_data)
        
        # Receive the rest of the audio data
        while b"END_AUDIO" not in audio_data:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            
            if b"END_AUDIO" in chunk:
                audio_part = chunk.split(b"END_AUDIO")[0]
                temp_file.write(audio_part)
                break
            else:
                temp_file.write(chunk)
    
    client_socket.close()
    
    # Save the audio file if requested
    if save_file:
        import shutil
        shutil.copy2(temp_filename, save_file)
        print(f"Audio saved to {save_file}")
    
    # Play the audio
    print("Playing audio...")
    try:
        pygame.mixer.music.load(temp_filename)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
    except Exception as e:
        print(f"Error playing audio: {e}")
    finally:
        pygame.mixer.quit()
        pygame.quit()
        
        # Clean up temporary file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

def interactive_mode(server_ip, server_port):
    """Interactive mode for sending multiple text requests"""
    print("=== Interactive Text-to-Speech Mode ===")
    print("Type your text and press Enter to hear it spoken.")
    print("Use /voice [name] to change voice (e.g., /voice en-US-Neural2-M)")
    print("Use /lang [code] to change language (e.g., /lang fr-FR)")
    print("Use /rate [number] to change speaking rate (e.g., /rate 0.8)")
    print("Use /save [filename] to save the next audio")
    print("Type /exit or /quit to end the session")
    print("=======================================")
    
    voice_name = "en-US-Neural2-F"  # default voice
    language_code = "en-US"         # default language
    speaking_rate = 1.0             # default rate
    save_file = None                # default: don't save
    
    while True:
        try:
            text = input("\nText to speak (or command): ")
            
            # Process commands
            if text.startswith("/"):
                cmd_parts = text.split(maxsplit=1)
                cmd = cmd_parts[0].lower()
                
                if cmd in ["/exit", "/quit"]:
                    break
                    
                elif cmd == "/voice" and len(cmd_parts) > 1:
                    voice_name = cmd_parts[1]
                    print(f"Voice set to: {voice_name}")
                    continue
                    
                elif cmd == "/lang" and len(cmd_parts) > 1:
                    language_code = cmd_parts[1]
                    print(f"Language set to: {language_code}")
                    continue
                    
                elif cmd == "/rate" and len(cmd_parts) > 1:
                    try:
                        speaking_rate = float(cmd_parts[1])
                        print(f"Speaking rate set to: {speaking_rate}")
                    except ValueError:
                        print("Error: Rate must be a number")
                    continue
                    
                elif cmd == "/save" and len(cmd_parts) > 1:
                    save_file = cmd_parts[1]
                    print(f"Next audio will be saved to: {save_file}")
                    continue
                    
                elif cmd == "/info":
                    print(f"Current settings:")
                    print(f"  Voice: {voice_name}")
                    print(f"  Language: {language_code}")
                    print(f"  Speaking rate: {speaking_rate}")
                    print(f"  Save to: {save_file or 'not saving'}")
                    continue
                    
                else:
                    print(f"Unknown command: {cmd}")
                    continue
            
            # Skip empty input
            if not text:
                continue
                
            # Send text for speech synthesis
            send_text_and_play_speech(
                server_ip, 
                server_port, 
                text, 
                voice_name=voice_name,
                language_code=language_code, 
                speaking_rate=speaking_rate,
                save_file=save_file
            )
            
            # Reset save_file after using it once
            if save_file:
                print(f"Audio saved to {save_file}")
                save_file = None
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

def main():
    """Parse command line arguments and start client"""
    parser = argparse.ArgumentParser(description='Text-to-speech client')
    parser.add_argument('--server', '-s', default='127.0.0.1', 
                        help='Server IP address (default: 127.0.0.1)')
    parser.add_argument('--port', '-p', type=int, default=12345, 
                        help='Server port (default: 12345)')
    parser.add_argument('--text', '-t', 
                        help='Text to synthesize (if not provided, enters interactive mode)')
    parser.add_argument('--voice', '-v', 
                        help='Voice name (e.g., en-US-Neural2-F)')
    parser.add_argument('--language', '-l', 
                        help='Language code (e.g., en-US)')
    parser.add_argument('--rate', '-r', type=float, 
                        help='Speaking rate (default: 1.0)')
    parser.add_argument('--save', 
                        help='Save audio to file')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Enter interactive mode')
    
    args = parser.parse_args()
    
    try:
        # Interactive mode if no text provided or explicitly requested
        if args.interactive or args.text is None:
            interactive_mode(args.server, args.port)
        else:
            # Single text-to-speech conversion
            send_text_and_play_speech(
                args.server, 
                args.port, 
                args.text, 
                voice_name=args.voice,
                language_code=args.language, 
                speaking_rate=args.rate,
                save_file=args.save
            )
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
