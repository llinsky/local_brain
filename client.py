from openwakeword.model import Model
import pyaudio
import numpy as np
import sys

from speech import record_command, transcribe_audio, speak, speak_or_cached, play_thinking_sound, play_processing_sound, play_ready_sound, play_wake_word_detected_sound, cleanup_audio, is_speaking
from llm import run_conversation

from config import SAMPLE_RATE, FRAME_LENGTH, CHUNK_DURATION


def main():
    # Load openWakeWord model - replace with your trained custom model path for "GERT"
    # First, train if needed: See https://github.com/dscripka/openWakeWord for details
    oww_model = Model(
        wakeword_models=["data/hey_gert.onnx"],  # Using ONNX instead of TFLite for better compatibility
        inference_framework="onnx",  # ONNX works better on macOS Python 3.11
        vad_threshold=0.5  # Adjust for sensitivity
    )

    pa = pyaudio.PyAudio()
    current_conversation_id = None
    listening_paused = False  # Flag to track if listening is paused after "stop"
    print("👂 Listening for wake word 'Hey GERT'...")

    try:
        while True:
            stream = pa.open(
                rate=SAMPLE_RATE,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=FRAME_LENGTH
            )
            try:
                while True:
                    frame = stream.read(FRAME_LENGTH, exception_on_overflow=False)
                    
                    # Skip wake word detection if TTS is currently playing
                    if is_speaking():
                        continue
                        
                    # Get predictions (expects numpy int16 array)
                    audio_np = np.frombuffer(frame, dtype=np.int16)
                    prediction = oww_model.predict(audio_np)
                    # Check for detection (score > 0.5 threshold; key is model name, e.g., "hey_gert")
                    if prediction.get("hey_gert", 0) > 0.5:
                        print("🚨 Wake word detected!")
                        play_wake_word_detected_sound()
                        # If listening was paused, resume it
                        if listening_paused:
                            listening_paused = False
                            print("🔊 Listening resumed")
                        stream.close()
                        # Record command after wake word
                        wav_buffer = record_command(
                            pa=pa,
                            chunk_size=int(SAMPLE_RATE * CHUNK_DURATION)
                        )
                        # Transcribe
                        transcription = transcribe_audio(wav_buffer)
                        print(f"🗣️ You said: {transcription}")
                        
                        # Skip processing if transcription is empty or too short (likely noise)
                        if not transcription or len(transcription.strip()) < 2:
                            print("⚠️ Empty or too short transcription, ignoring...")
                            break
                        
                        # Check for conversation reset commands
                        if any(phrase in transcription.lower() for phrase in ["new conversation", "start over", "reset"]):
                            current_conversation_id = None
                            speak_or_cached("New conversation.", "new_conversation.wav")
                            break
                        
                        # Check for conversation end commands
                        if any(phrase in transcription.lower() for phrase in ["goodbye", "stop", "end conversation"]):
                            current_conversation_id = None
                            listening_paused = True
                            speak_or_cached("Goodbye.", "goodbye.wav")
                            print("🔇 Listening paused - say the wake word to continue")
                            break
                        
                        # Check for shutdown commands
                        if any(phrase in transcription.lower() for phrase in ["shut down", "shutdown", "exit program", "quit"]):
                            speak_or_cached("Shutting down.", "shutting_down.wav")
                            # Clean up audio resources gracefully
                            cleanup_audio()
                            pa.terminate()
                            sys.exit(0)
                        
                        # Process with Ollama
                        print("🤖 Processing your request...")
                        play_thinking_sound()
                        response, current_conversation_id = run_conversation(transcription, current_conversation_id)
                        print("✅ Response ready!")
                        play_ready_sound()
                        
                        # Speak response
                        speak(response)
                        break  # Restart wake word listening
            finally:
                if 'stream' in locals():
                    try:
                        if stream.is_active():
                            stream.close()
                    except OSError:
                        pass  # Stream already closed
    finally:
        cleanup_audio()
        pa.terminate()

if __name__ == "__main__":
    main()