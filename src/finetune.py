import torch
from transformers import GPT2LMHeadModel, GPT2Tokenizer, TextDataset, DataCollatorForLanguageModeling
from transformers import Trainer, TrainingArguments
import os

def finetune():
    print("Upgrading Tild's brain...")
    
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    tokenizer.pad_token = tokenizer.eos_token
    model = GPT2LMHeadModel.from_pretrained("gpt2")
    
    print(f"Tild has {sum(p.numel() for p in model.parameters())/1e6:.0f}M parameters now!")
    print("Preparing Tild's data...")
    
    with open('data/data.txt', 'r', encoding='utf-8') as f:
        text = f.read()
    
    with open('data/temp_train.txt', 'w', encoding='utf-8') as f:
        f.write(text)
    
    dataset = TextDataset(
        tokenizer=tokenizer,
        file_path='data/temp_train.txt',
        block_size=128
    )
    
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False
    )
    
    print(f"Tild found {len(dataset)} training samples!")
    
    training_args = TrainingArguments(
        output_dir='models/tild_v2',
        overwrite_output_dir=True,
        num_train_epochs=10,
        per_device_train_batch_size=4,
        save_steps=500,
        save_total_limit=2,
        logging_steps=100,
        learning_rate=5e-5,
        warmup_steps=100,
        use_cpu=True,
        no_cuda=True,
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=data_collator,
        train_dataset=dataset,
    )
    
    print("Tild is learning...")
    trainer.train()
    
    model.save_pretrained('models/tild_v2')
    tokenizer.save_pretrained('models/tild_v2')
    os.remove('data/temp_train.txt')
    
    print("Tild's brain upgraded and saved!")

if __name__ == '__main__':
    finetune()