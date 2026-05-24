# setup.py
import os
import subprocess

print("Setting up Tild...")

# Install requirements
subprocess.run(['pip3', 'install', '-r', 'requirements.txt'])

# Create folders
os.makedirs('models', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Train Tild
print("Training Tild's brain...")
subprocess.run(['python3', 'tild.py', 'train'])

# Finetune
print("Upgrading Tild's brain...")
subprocess.run(['python3', 'tild.py', 'finetune'])

print("Tild is ready!")