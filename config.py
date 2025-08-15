
# Setup constants for audio
CHUNK_DURATION = 0.5  # seconds per chunk
SILENCE_THRESHOLD = 280  # Increased from 200 to reduce noise sensitivity
SILENCE_DURATION = 4.25
MINIMUM_RECORDING_TIME = 4.0  # Minimum seconds before silence detection starts
SAMPLE_RATE = 16000
FRAME_LENGTH = 1280  # 80ms at 16kHz for openWakeWord
