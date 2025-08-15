from openwakeword.model import Model
import pyaudio
import numpy as np
import threading
import queue
import time
from datetime import datetime

from speech import record_command, transcribe_audio, speak
from llm import run_conversation
from config import SAMPLE_RATE, FRAME_LENGTH, CHUNK_DURATION

class VoiceConversationManager:
    def __init__(self, max_concurrent_conversations=3):
        self.max_concurrent = max_concurrent_conversations
        self.active_conversations = {}
        self.conversation_queue = queue.Queue()
        self.should_stop = threading.Event()
        
    def start_conversation(self, audio_data):
        """Start a new conversation in a separate thread."""
        conversation_id = f"voice_{int(time.time())}"
        
        if len(self.active_conversations) >= self.max_concurrent:
            print(f"⚠️ Maximum conversations ({self.max_concurrent}) reached. Queuing request...")
            self.conversation_queue.put(audio_data)
            return
        
        thread = threading.Thread(
            target=self._handle_conversation,
            args=(conversation_id, audio_data),
            daemon=True
        )
        
        self.active_conversations[conversation_id] = {
            'thread': thread,
            'start_time': datetime.now()
        }
        
        print(f"🎯 Starting conversation {conversation_id}")
        thread.start()
    
    def _handle_conversation(self, conversation_id, audio_data):
        """Handle a single conversation."""
        try:
            # Transcribe the audio
            transcription = transcribe_audio(audio_data)
            print(f"🗣️ [{conversation_id}] You said: {transcription}")
            
            # Process with LLM
            response, _ = run_conversation(transcription, conversation_id)
            
            # Speak response (this might overlap with other conversations)
            print(f"🤖 [{conversation_id}] Responding...")
            speak(f"From conversation {conversation_id[-4:]}: {response}")
            
        except Exception as e:
            print(f"❌ Error in conversation {conversation_id}: {str(e)}")
            speak(f"Sorry, there was an error in conversation {conversation_id[-4:]}")
        
        finally:
            # Clean up this conversation
            if conversation_id in self.active_conversations:
                del self.active_conversations[conversation_id]
            
            # Start queued conversation if any
            if not self.conversation_queue.empty():
                queued_audio = self.conversation_queue.get()
                self.start_conversation(queued_audio)
    
    def get_active_count(self):
        """Get the number of active conversations."""
        return len(self.active_conversations)
    
    def stop_all(self):
        """Stop all conversations."""
        self.should_stop.set()
        for conv_id, conv_info in self.active_conversations.items():
            if conv_info['thread'].is_alive():
                print(f"🛑 Stopping conversation {conv_id}")
                # Note: We can't forcefully stop threads in Python, 
                # but the should_stop event can be checked by conversation handlers

def main():
    # Load openWakeWord model
    oww_model = Model(
        wakeword_models=["data/hey_gert.onnx"],
        inference_framework="onnx",
        vad_threshold=0.5
    )

    pa = pyaudio.PyAudio()
    conversation_manager = VoiceConversationManager(max_concurrent_conversations=3)
    
    print("👂 Listening for wake word 'Hey GERT' (parallel mode)...")
    print("💡 Multiple conversations supported - say 'Hey GERT' multiple times for parallel processing")

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
                    audio_np = np.frombuffer(frame, dtype=np.int16)
                    prediction = oww_model.predict(audio_np)
                    
                    if prediction.get("hey_gert", 0) > 0.5:
                        active_count = conversation_manager.get_active_count()
                        print(f"🚨 Wake word detected! Active conversations: {active_count}")
                        
                        stream.close()
                        
                        # Record command after wake word
                        wav_buffer = record_command(
                            pa=pa,
                            chunk_size=int(SAMPLE_RATE * CHUNK_DURATION)
                        )
                        
                        # Start conversation in parallel
                        conversation_manager.start_conversation(wav_buffer)
                        break
                        
            finally:
                if 'stream' in locals():
                    try:
                        if stream.is_active():
                            stream.close()
                    except OSError:
                        pass  # Stream already closed
                    
    except KeyboardInterrupt:
        print("\n👋 Shutting down parallel conversation system...")
        conversation_manager.stop_all()
    finally:
        pa.terminate()

if __name__ == "__main__":
    main()