# setup.py
import os
import subprocess

print("Setting up Beru...")

# Install requirements
subprocess.run(['pip3', 'install', '-r', 'requirements.txt'])

# Create folders
os.makedirs('models', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Train Beru
print("Training Beru's brain...")
subprocess.run(['python3', 'beru.py', 'train'])

# Finetune
print("Upgrading Beru's brain...")
subprocess.run(['python3', 'beru.py', 'finetune'])

print("Beru is ready!")