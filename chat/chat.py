import torch
import tiktoken
from src.config import TildConfig
from src.model import Tild

cfg = TildConfig()

def load_tild():
    checkpoint = torch.load(cfg.model_path, map_location=cfg.device)
    vocab_size = checkpoint['vocab_size']
    encoding = checkpoint['encoding']
    
    enc = tiktoken.get_encoding(encoding)
    
    model = Tild(vocab_size).to(cfg.device)
    model.load_state_dict(checkpoint['model_state'])
    model.eval()
    
    return model, enc

def chat():
    print("Loading Tild's brain...")
    model, enc = load_tild()
    print("Tild is ready! Type your message (or 'quit' to exit)\n")
    
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == 'quit':
            print("Tild: Goodbye!")
            break
        
        prompt = user_input + "\n"
        tokens = enc.encode(prompt)
        context = torch.tensor([tokens], dtype=torch.long, device=cfg.device)
        
        with torch.no_grad():
            output = model.generate(context, max_new_tokens=50)
        
        generated = enc.decode(output[0].tolist())
        response = generated[len(prompt):].split('\n')[0]
        print(f"Tild: {response}\n")

if __name__ == '__main__':
    chat()