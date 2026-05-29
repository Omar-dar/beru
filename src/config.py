import torch

class TildConfig:

    block_size = 128
    n_embd     = 384
    n_head     = 6
    n_layer    = 8
    dropout    = 0.1
    device     = 'mps'
    lr         = 3e-4
    epochs     = 1000
    batch_size = 16
    data_path = [
        'data/data.txt',
        'data/conversation_data.txt',
        'data/personality_data.txt'
    ]

    model_path = 'models/tild_brain.pt'
    encoding   = 'gpt2'