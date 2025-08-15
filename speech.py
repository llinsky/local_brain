import openwakeword
from openwakeword.model import Model
import pyaudio
import numpy as np
import io
import wave
import signal
import sys
import os
from piper.voice import PiperVoice
import sounddevice as sd
import nemo.collections.asr as nemo_asr
import time


# Load Piper TTS model - replace with your downloaded model path
piper_model_path = "data/en_US-kusal-medium.onnx"  # Download from https://huggingface.co/rhasspy/piper-voices
piper_voice = PiperVoice.load(piper_model_path)

parakeet_model = nemo_asr.models.EncDecRNNTBPEModel.from_pretrained("nvidia/parakeet-rnnt-1.1b")

from config import SILENCE_DURATION, SILENCE_THRESHOLD, SAMPLE_RATE, MINIMUM_RECORDING_TIME

def handle_interrupt(sig, frame):
    print("\n👋 Caught interrupt, exiting cleanly...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_interrupt)

def play_notification_beep(frequency=800, duration=0.2):
    """Play a short notification beep."""
    try:
        # Generate a simple sine wave beep
        sample_rate = 22050
        frames = int(duration * sample_rate)
        t = np.linspace(0, duration, frames)
        wave_data = np.sin(2 * np.pi * frequency * t) * 0.3
        
        # Convert to int16 for playback
        audio_data = (wave_data * 32767).astype(np.int16)
        
        # Play the beep
        sd.play(audio_data, sample_rate)
        sd.wait()  # Wait until the sound finishes
    except Exception as e:
        print(f"Could not play notification beep: {e}")

def play_thinking_sound():
    """Play a brief thinking sound."""
    play_notification_beep(600, 0.1)

def play_processing_sound():
    """Play a processing sound."""
    play_notification_beep(400, 0.15)

def play_ready_sound():
    """Play a ready/completion sound."""
    play_notification_beep(1000, 0.1)

def play_wake_word_detected_sound():
    """Play a brief wake word detection sound."""
    play_notification_beep(800, 0.15)

def play_cached_audio(filename: str):
    """Play a pre-cached audio file if it exists, otherwise fall back to TTS."""
    global _is_speaking
    import wave
    
    cache_path = os.path.join("audio_cache", filename)
    
    if os.path.exists(cache_path):
        try:
            _is_speaking = True
            # Load and play the cached WAV file
            with wave.open(cache_path, 'rb') as wav_file:
                frames = wav_file.readframes(wav_file.getnframes())
                audio_data = np.frombuffer(frames, dtype=np.int16)
                
                # Play the audio
                sd.play(audio_data, wav_file.getframerate())
                sd.wait()  # Wait until playback finishes
                _is_speaking = False
                return True
        except Exception as e:
            print(f"Error playing cached audio {filename}: {e}")
            _is_speaking = False
    
    return False

def speak_or_cached(text: str, cache_filename: str = None):
    """Speak text, using cached audio if available."""
    if cache_filename and play_cached_audio(cache_filename):
        print(f"Playing cached: {text}")
        return
    
    # Fall back to normal TTS
    speak(text)

def cleanup_audio():
    """Gracefully clean up audio resources."""
    try:
        # Stop any active SoundDevice playback
        sd.stop()
        
        # Small delay to ensure SoundDevice cleanup completes
        time.sleep(0.1)
        
        print("Audio cleanup completed")
    except Exception as e:
        print(f"Audio cleanup warning: {e}")

def clean_text_for_speech(text: str) -> str:
    """Clean text for better TTS pronunciation by removing markdown formatting."""
    import re
    
    # Remove markdown formatting
    # Remove bold/italic asterisks and underscores
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold** -> bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic* -> italic
    text = re.sub(r'__([^_]+)__', r'\1', text)      # __bold__ -> bold
    text = re.sub(r'_([^_]+)_', r'\1', text)        # _italic_ -> italic
    
    # Remove code blocks and inline code
    text = re.sub(r'```[^`]*```', '', text)         # Remove code blocks
    text = re.sub(r'`([^`]+)`', r'\1', text)        # `code` -> code
    
    # Remove links but keep text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)  # [text](url) -> text
    
    # Remove headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)  # # Header -> Header
    
    # Clean up multiple spaces and newlines
    text = re.sub(r'\n+', '. ', text)               # Multiple newlines -> period space
    text = re.sub(r'\s+', ' ', text)                # Multiple spaces -> single space
    
    # Remove common markdown artifacts that sound weird
    text = text.replace('---', '.')                 # Horizontal rules
    text = text.replace('***', '.')                 # Bold+italic
    
    return text.strip()

# Global flag to track when TTS is playing
_is_speaking = False

def is_speaking():
    """Check if TTS is currently playing."""
    return _is_speaking

def speak(text: str):
    global _is_speaking
    # Clean text for better speech synthesis
    cleaned_text = clean_text_for_speech(text)
    print(f"Speaking: {cleaned_text}")
    
    _is_speaking = True
    
    # Use synthesize to get audio chunks
    stream = sd.OutputStream(samplerate=piper_voice.config.sample_rate, channels=1, dtype='int16')
    stream.start()
    
    try:
        for audio_chunk in piper_voice.synthesize(cleaned_text):
            # Convert audio bytes to numpy array and play
            audio_data = np.frombuffer(audio_chunk.audio_int16_bytes, dtype=np.int16)
            stream.write(audio_data)
    finally:
        stream.stop()
        stream.close()
        _is_speaking = False

def record_command(pa, chunk_size, silence_threshold=SILENCE_THRESHOLD, silence_duration=SILENCE_DURATION):
    stream = pa.open(
        rate=SAMPLE_RATE,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=chunk_size
    )
    print("🎙️ Listening for command (auto-stop on silence)...")
    frames = []
    silence_chunks = int(silence_duration / (chunk_size / SAMPLE_RATE))
    minimum_chunks = int(MINIMUM_RECORDING_TIME / (chunk_size / SAMPLE_RATE))
    silent_chunks = 0
    chunk_count = 0
    
    try:
        while True:
            data = stream.read(chunk_size, exception_on_overflow=False)
            frames.append(data)
            chunk_count += 1
            
            # Convert bytes to numpy int16 to compute volume using RMS
            audio_np = np.frombuffer(data, dtype=np.int16)
            # Use RMS (Root Mean Square) for better volume detection
            volume = np.sqrt(np.mean(audio_np.astype(np.float32) ** 2))
            
            # Only start silence detection after minimum recording time
            if chunk_count >= minimum_chunks:
                if volume < silence_threshold:
                    silent_chunks += 1
                else:
                    silent_chunks = 0
                if silent_chunks >= silence_chunks:
                    print("Silence detected, stopping recording.")
                    break
    finally:
        stream.stop_stream()
        stream.close()
    # Wrap into WAV buffer
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b''.join(frames))
    wav_buffer.seek(0)
    return wav_buffer

def transcribe_audio(wav_buffer):
    # Parakeet transcription (expects WAV file path; save temp file)
    temp_wav = "temp_input.wav"
    with open(temp_wav, 'wb') as f:
        f.write(wav_buffer.getvalue())
    transcription = parakeet_model.transcribe([temp_wav])[0]
    os.remove(temp_wav)
    
    # Handle NeMo Hypothesis object - extract text
    if hasattr(transcription, 'text'):
        return transcription.text.strip().lower()
    else:
        return str(transcription).strip().lower()

