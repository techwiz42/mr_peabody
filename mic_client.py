#!/usr/bin/env python3
"""
Client script that records from local microphone and sends the audio data
to a server running on a Digital Ocean droplet
"""
import pyaudio
import socket
import time
import argparse
import wave
import os

# Audio recording parameters
RATE = 16000        # Sample rate
CHUNK = 1024        # Buffer size
FORMAT = pyaudio.paInt16  # 16-bit audio
CHANNELS = 1        # Mono audio
RECORD_SECONDS = 5  # Default recording duration

def record_and_send(server_ip, server_port, duration=RECORD_SECONDS, save_local=False):
    """Record audio from microphone and send to the remote server"""
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    
    # Open audio stream
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    print(f"Connecting to server at {server_ip}:{server_port}...")
    
    # Create socket and connect to server
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((server_ip, server_port))
    except ConnectionRefusedError:
        print("Error: Could not connect to server. Make sure the server is running.")
        return
    
    # Send audio format information
    format_info = f"{RATE},{CHANNELS},{p.get_sample_size(FORMAT)}"
    client_socket.sendall(format_info.encode('utf-8'))
    
    # Wait for acknowledgment
    ack = client_socket.recv(1024)
    if ack != b"ACK":
        print("Error: Server did not acknowledge format info")
        return
    
    print(f"Recording for {duration} seconds...")
    frames = []
    
    # Start recording with a visual indicator
    for i in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
        # Send the audio chunk to the server
        client_socket.sendall(data)
        # Print a simple progress indicator
        if i % 10 == 0:
            dots = "." * (i // 10 % 4)
            print(f"\rRecording and sending{dots:<3}", end="")
    
    print("\nFinished recording!")
    
    # Signal end of transmission
    client_socket.sendall(b"END")
    
    # Receive transcription from server
    print("Waiting for transcription results...")
    transcription_data = b""
    while True:
        chunk = client_socket.recv(4096)
        if chunk == b"" or b"END_TRANSCRIPTION" in chunk:
            if b"END_TRANSCRIPTION" in chunk:
                transcription_data += chunk.split(b"END_TRANSCRIPTION")[0]
            break
        transcription_data += chunk
    
    # Close everything
    stream.stop_stream()
    stream.close()
    p.terminate()
    client_socket.close()
    
    # Save recording locally if requested
    if save_local:
        wf = wave.open("local_recording.wav", 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        print("Local recording saved as 'local_recording.wav'")
    
    # Display transcription results
    print("\nTranscription Results:")
    print("---------------------")
    print(transcription_data.decode('utf-8'))

def main():
    """Parse command line arguments and start recording"""
    parser = argparse.ArgumentParser(description='Record from microphone and send to server')
    parser.add_argument('--server', '-s', default='127.0.0.1', 
                        help='Server IP address (default: 127.0.0.1)')
    parser.add_argument('--port', '-p', type=int, default=12345, 
                        help='Server port (default: 12345)')
    parser.add_argument('--duration', '-d', type=float, default=RECORD_SECONDS, 
                        help=f'Recording duration in seconds (default: {RECORD_SECONDS})')
    parser.add_argument('--save', action='store_true', 
                        help='Save recording locally')
    
    args = parser.parse_args()
    
    try:
        record_and_send(args.server, args.port, args.duration, args.save)
    except KeyboardInterrupt:
        print("\nRecording stopped by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
