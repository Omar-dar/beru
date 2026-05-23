import torch
import tiktoken
import random
from src.config import TildConfig
from src.model import Tild

cfg = TildConfig()

FALLBACKS = [
    "That is an interesting question! I am still learning about that topic.",
    "Hmm I am not sure about that yet. Ask me something else!",
    "Good question! Omar needs to train me more on that topic.",
    "I do not have enough knowledge about that yet but I am always learning!",
    "That is beyond what I know right now. But tell me more and maybe I can figure it out!",
    "Interesting! I have not learned enough about that yet. What else can I help with?",
    "Omar has not trained me on that yet! But I am getting smarter every day.",
    "I wish I could answer that better! More training will help me get there.",
]

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
    if len(response) < 3:
        return False
    if len(response.split()) < 2:
        return False
    if response.count('|') > 2:
        return False
    if '###' in response:
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
        tokens = enc.encode(prompt, disallowed_special=())
        context = torch.tensor([tokens], dtype=torch.long, device=cfg.device)

        with torch.no_grad():
            output = model.generate(context, max_new_tokens=80)

        generated = enc.decode(output[0].tolist())
        response = generated[len(prompt):].split('\n')[0].strip()

        if not is_good_response(response):
            response = random.choice(FALLBACKS)

        print(f"Tild: {response}\n")

if __name__ == '__main__':
    chat()