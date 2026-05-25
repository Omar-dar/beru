# Tild - Personal AI 

Tild is a personal AI language model built completely from scratch by Omar Darwish using Python and PyTorch. Tild is a decoder-only transformer inspired by the GPT architecture.

## What Tild Can Do

### Conversation
- Chat in English, Swedish and Arabic
- Remember corrections and learn from them
- Remember conversation context
- Respond with personality and humor

### Text Analysis
- Identify persons, places and dates (NER)
- Extract events from text
- Create timelines
- Find patterns and anomalies
- Build relationship maps
- Summarize large texts
- Anonymize sensitive information
- Analyze chat logs

### Internet Search
- Search Wikipedia for factual questions
- Get real-time weather via OpenWeatherMap API

### Voice
- Listen via microphone (Whisper speech-to-text)
- Speak responses out loud (Mac TTS)
- Supports English, Swedish and Arabic voice input

## Project Structure

```
Tild/
├── chat/
│   ├── chat.py          # Text chat interface
│   └── voice_chat.py    # Voice chat interface
├── data/
│   └── data.txt         # Training data (Q&A pairs)
├── models/
│   └── tild_v2/         # Fine-tuned model (not in GitHub)
├── src/
│   ├── config.py        # Model configuration
│   ├── model.py         # Tild transformer architecture
│   ├── train.py         # Training from scratch
│   ├── finetune.py      # Fine-tuning with pre-trained weights
│   ├── rag.py           # Retrieval Augmented Generation
│   ├── memory.py        # Conversation memory and corrections
│   └── search.py        # Wikipedia and weather search
├── .env                 # API keys (not in GitHub)
├── .gitignore
├── requirements.txt
├── setup.py
└── tild.py              # Main entry point
```

## Architecture

Tild is a decoder-only transformer with:

| Setting | Value |
|---|---|
| Parameters | 89M |
| Layers | 12 |
| Embedding size | 512 |
| Attention heads | 8 |
| Context window | 256 tokens |
| Tokenizer | GPT-2 (tiktoken) |

## Response Pipeline

When you ask Tild something this is what happens:

```
Your question
      |
1. Correction check - did you correct Tild?
      |
2. Corrections memory - has Tild learned this before?
      |
3. Internet search - is this a factual question?
      |
4. RAG - find closest match in data.txt
      |
5. Language model - generate response
      |
6. Fallback - if nothing works give intelligent fallback
      |
Tild's response
```

## How To Run

### Install dependencies
```bash
pip3 install -r requirements.txt
```

### Train Tild from scratch
```bash
python3 tild.py train
```

### Fine-tune Tild
```bash
python3 tild.py finetune
```

### Chat with Tild (text)
```bash
python3 tild.py chat
```

### Talk to Tild (voice)
```bash
python3 tild.py voice
```

## Setup On New Machine

```bash
git clone git@github.com:Omar-dar/tild.git
cd tild
python3 setup.py
```

This automatically installs everything and trains Tild.

## Environment Variables

Create a `.env` file in the root:

```
OPENWEATHER_KEY=your_openweathermap_api_key
ELEVENLABS_KEY=your_elevenlabs_api_key
```

## Training Data Format

All training data is in `data/data.txt` using this format:

```
### Human: your question here
### Tild: Tild's response here
```

The more varied and comprehensive the data the smarter Tild becomes.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| PyTorch | Neural network framework |
| Transformers (HuggingFace) | Pre-trained model weights |
| tiktoken | GPT-2 tokenizer |
| sentence-transformers | RAG similarity search |
| Whisper (OpenAI) | Speech to text |
| Wikipedia API | Internet search |
| OpenWeatherMap API | Weather data |

## Roadmap

### Completed
- Transformer architecture from scratch
- Training pipeline
- Fine-tuning with pre-trained weights
- RAG system
- Conversation memory
- Active learning from corrections
- Internet search (Wikipedia + Weather)
- Voice input and output
- Swedish and Arabic support
- Text analysis (NER, events, timelines)
- Pattern recognition
- Relationship mapping
- Summarization
- Anonymization

### In Progress
- Larger model (120M+ parameters)
- Better Arabic support
- Robot integration (ESP32-S3)

### Future
- Home server deployment
- Real-time document analysis
- Knowledge graph visualization
- ElevenLabs voice integration
- Connect to robot brain

## About

Tild was built completely from scratch by Omar Darwish as a personal AI project. The name Tild is unique and given by Omar. Tild's architecture and training pipeline were developed independently. The project also experiments with fine-tuning and external NLP tooling where relevant. 
The architecture, training code and personality are all original.

GitHub: github.com/Omar-dar/tild
