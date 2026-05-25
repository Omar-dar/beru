import torch

class TildConfig:
    # Bigger model
    block_size = 256      # bigger context
    n_embd     = 512      # bigger understanding
    n_head     = 8        # same attention heads
    n_layer    = 12       # deeper thinking (was 6)
    dropout    = 0.1
    device     = 'mps'    # M2 GPU

    lr         = 3e-4
    epochs     = 20000
    batch_size = 32

    data_path  = 'data/data.txt'
    model_path = 'models/tild_brain.pt'
    encoding   = 'gpt2'