import torch
import tiktoken
from src.config import TildConfig
from src.model import Tild

cfg = TildConfig()

# Smart fallbacks when Tild doesn't know
FALLBACKS = [
    "That is an interesting question. I am still learning about that.",
    "Hmm, I need to think about that more. Ask me something else!",
    "I do not have enough knowledge about that yet. Omar needs to train me more!",
    "Good question! I am not sure yet but I am learning every day.",
    "That is beyond what I know right now. But I am getting smarter!",
]

import random

def load_tild():
    checkpoint = torch.load(cfg.model_path, map_location=cfg.device)
    vocab_size = checkpoint['vocab_size']
    encoding = checkpoint['encoding']
    enc = tiktoken.get_encoding(encoding)
    model = Tild(vocab_size).to(cfg.device)
    model.load_state_dict(checkpoint['model_state'])
    model.eval()
    return model, enc

def is_good_response(response):
    # Check if response makes sense
    if len(response) < 3:
        return False
    if response.count('?') > 3:
        return False
    if len(set(response.split())) < 2:
        return False
    return True

def chat():
    print("Loading Tild's brain...")
    model, enc = load_tild()
    print("Tild is ready! Type your message (or 'quit' to exit)\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == 'quit':
            print("Tild: Goodbye! It was great talking with you.")
            break

        prompt = f"### Human: {user_input}\n### Tild:"
        tokens = enc.encode(prompt)
        context = torch.tensor([tokens], dtype=torch.long, device=cfg.device)

        with torch.no_grad():
            output = model.generate(context, max_new_tokens=60)

        generated = enc.decode(output[0].tolist())
        response = generated[len(prompt):].split('\n')[0].strip()

        # Use fallback if response is bad
        if not is_good_response(response):
            response = random.choice(FALLBACKS)

        print(f"Tild: {response}\n")

if __name__ == '__main__':
    chat()