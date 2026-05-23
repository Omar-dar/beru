import torch

class TildConfig:
    block_size = 128
    n_embd     = 256
    n_head     = 8
    n_layer    = 6
    dropout    = 0.1
    device     = 'mps'  # M2 GPU!
    
    lr         = 3e-4
    epochs     = 5000
    batch_size = 16
    
    data_path = 'data/combined.txt'
    model_path = 'models/tild_brain.pt'
    encoding   = 'gpt2'