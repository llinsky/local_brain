#!/usr/bin/env python3
"""
Generate pre-cached audio files for common system messages.
Run this once to create audio files that can be played instantly.
"""

import os
import wave
import numpy as np
from piper.voice import PiperVoice

def save_audio_to_wav(audio_chunks, filename, sample_rate):
    """Save audio chunks to a WAV file."""
    # Collect all audio data
    audio_data = []
    for chunk in audio_chunks:
        chunk_data = np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)
        audio_data.append(chunk_data)
    
    # Concatenate all chunks
    full_audio = np.concatenate(audio_data) if audio_data else np.array([], dtype=np.int16)
    
    # Save to WAV file
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(full_audio.tobytes())

def main():
    # Load Piper TTS model
    piper_model_path = "data/en_US-kusal-medium.onnx"
    if not os.path.exists(piper_model_path):
        print(f"Error: Piper model not found at {piper_model_path}")
        print("Please download the model from https://huggingface.co/rhasspy/piper-voices")
        return
    
    piper_voice = PiperVoice.load(piper_model_path)
    
    # Common system messages to pre-generate
    messages = {
        "thinking.wav": "Thinking...",
        "processing.wav": "Processing...",
        "searching.wav": "Searching...",
        "ready.wav": "Ready!",
        "goodbye.wav": "Goodbye.",
        "shutting_down.wav": "Shutting down.",
        "new_conversation.wav": "New conversation.",
        "error.wav": "Error.",
        "tool_executing.wav": "Executing...",
        "generating_response.wav": "Generating..."
    }
    
    # Create audio cache directory
    cache_dir = "audio_cache"
    os.makedirs(cache_dir, exist_ok=True)
    
    print("Generating pre-cached audio files...")
    
    for filename, text in messages.items():
        filepath = os.path.join(cache_dir, filename)
        print(f"Generating {filename}: '{text}'")
        
        try:
            # Generate audio chunks
            audio_chunks = list(piper_voice.synthesize(text))
            
            # Save to WAV file
            save_audio_to_wav(audio_chunks, filepath, piper_voice.config.sample_rate)
            
            print(f"  ✅ Saved to {filepath}")
            
        except Exception as e:
            print(f"  ❌ Error generating {filename}: {e}")
    
    print("\nAudio cache generation complete!")
    print(f"Files saved in {cache_dir}/")

if __name__ == "__main__":
    main()