import torch
import tiktoken
from src.config import TildConfig
from src.model import Tild

cfg = TildConfig()

def load_data():
    with open(cfg.data_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Use tiktoken instead of character level
    enc = tiktoken.get_encoding(cfg.encoding)
    tokens = enc.encode(text, disallowed_special=())
    vocab_size = enc.n_vocab
    
    print(f"Tild found {len(tokens)} tokens in training data")
    print(f"Vocabulary size: {vocab_size}")
    
    data = torch.tensor(tokens, dtype=torch.long)
    return data, vocab_size, enc

def get_batch(train_data, val_data, split):
    d = train_data if split == 'train' else val_data
    ix = torch.randint(len(d) - cfg.block_size, (cfg.batch_size,))
    x = torch.stack([d[i:i+cfg.block_size] for i in ix])
    y = torch.stack([d[i+1:i+cfg.block_size+1] for i in ix])
    return x.to(cfg.device), y.to(cfg.device)

def train():
    data, vocab_size, enc = load_data()

    n = int(0.9 * len(data))
    train_data = data[:n]
    val_data   = data[n:]

    model = Tild(vocab_size).to(cfg.device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg.lr)

    print(f"Tild has {sum(p.numel() for p in model.parameters())/1e6:.2f}M parameters")
    print("Tild is starting to learn...\n")

    for epoch in range(cfg.epochs):
        xb, yb = get_batch(train_data, val_data, 'train')
        logits, loss = model(xb, yb)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if epoch % 500 == 0:
            print(f"Epoch {epoch} | Loss: {loss.item():.4f}")

    print("\nTild has finished learning!")
    torch.save({
        'model_state': model.state_dict(),
        'vocab_size': vocab_size,
        'encoding': cfg.encoding,
    }, cfg.model_path)
    print("Tild's brain saved!")