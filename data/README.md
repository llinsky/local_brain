# Voice Models and Data

This directory contains the voice models and data files needed for the voice assistant.

## Required Files

### Wake Word Model
You need a wake word detection model for "Hey GERT" (or your chosen wake word):

**Option 1: Use provided model (if available)**
- `hey_gert.onnx` - ONNX format wake word model
- `hey_gert.tflite` - TensorFlow Lite format wake word model

**Option 2: Train your own model**
Follow the [openWakeWord documentation](https://github.com/dscripka/openWakeWord) to train a custom wake word model:

1. Install openWakeWord training dependencies
2. Record training samples of your wake word
3. Train the model using their training scripts
4. Place the resulting `.onnx` file in this directory

### Text-to-Speech Model
Download a Piper TTS voice model:

**`en_US-kusal-medium.onnx`** and **`en_US-kusal-medium.onnx.json`**
- Download from: https://huggingface.co/rhasspy/piper-voices
- Choose any English voice model you prefer
- Both the `.onnx` and `.onnx.json` files are required
- Update `speech.py` line 16 with your chosen model path

## Example Downloads

```bash
# Download Piper TTS model (example)
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/kusal/medium/en_US-kusal-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/kusal/medium/en_US-kusal-medium.onnx.json
```

## Security Note

⚠️ **Personal voice models are automatically ignored by git** to protect privacy.

## Model Configuration

Update the model path in `speech.py`:
```python
piper_model_path = "data/your_chosen_voice_model.onnx"
```

And update the wake word model path in `client.py`:
```python
wakeword_models=["data/your_wake_word_model.onnx"]
```