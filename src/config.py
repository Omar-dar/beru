class TildConfig:
    # Model
    block_size = 128      # bigger context window
    n_embd     = 256      # bigger understanding
    n_head     = 8        # more attention heads
    n_layer    = 6        # deeper thinking
    dropout    = 0.1
    device     = 'cpu'
    
    # Training
    lr         = 3e-4
    epochs     = 5000
    batch_size = 16
    
    # Paths
    data_path  = 'E:\\Tild\\data\\data.txt'
    model_path = 'E:\\Tild\\models\\tild_brain.pt'
    
    # Tokenizer
    encoding   = 'gpt2'  # same tokenizer as GPT2