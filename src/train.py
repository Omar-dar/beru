import torch
import tiktoken
from src.config import BeruConfig
from src.model import Beru

cfg = BeruConfig()


def load_data():
    text = ''

    paths = (
        cfg.data_path
        if isinstance(cfg.data_path, list)
        else [cfg.data_path]
    )

    for path in paths:
        with open(path, 'r', encoding='utf-8') as f:
            text += f.read() + '\n'

    enc = tiktoken.get_encoding(cfg.encoding)
    tokens = enc.encode(text, disallowed_special=())

    vocab_size = enc.n_vocab

    print(f"Beru found {len(tokens)} tokens in training data")
    print(f"Vocabulary size: {vocab_size}")

    data = torch.tensor(tokens, dtype=torch.long)

    return data, vocab_size, enc


def get_batch(train_data, val_data, split):

    d = train_data if split == 'train' else val_data

    ix = torch.randint(
        len(d) - cfg.block_size,
        (cfg.batch_size,)
    )

    x = torch.stack([
        d[i:i + cfg.block_size]
        for i in ix
    ])

    y = torch.stack([
        d[i + 1:i + cfg.block_size + 1]
        for i in ix
    ])

    return x.to(cfg.device), y.to(cfg.device)


def train():

    data, vocab_size, enc = load_data()

    n = int(0.9 * len(data))

    train_data = data[:n]
    val_data = data[n:]

    model = Beru(vocab_size).to(cfg.device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=cfg.lr
    )

    params = sum(
        p.numel()
        for p in model.parameters()
    ) / 1e6

    print(f"Beru has {params:.2f}M parameters")
    print(f"Epochs: {cfg.epochs}")
    print(f"Batch size: {cfg.batch_size}")
    print("Beru is starting to learn...\n")

    model.train()

    for epoch in range(cfg.epochs):

        xb, yb = get_batch(
            train_data,
            val_data,
            'train'
        )

        logits, loss = model(xb, yb)

        optimizer.zero_grad()

        loss.backward()

        optimizer.step()

        if epoch % 100 == 0:

            print(
                f"Epoch {epoch}/{cfg.epochs} "
                f"| Loss: {loss.item():.4f}"
            )

    print("\nTraining finished")
    print(f"Final loss: {loss.item():.4f}")

    torch.save(
        {
            'model_state': model.state_dict(),
            'vocab_size': vocab_size,
            'encoding': cfg.encoding,
        },
        cfg.model_path
    )

    print("Beru's brain saved!")