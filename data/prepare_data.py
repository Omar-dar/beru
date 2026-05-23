from datasets import load_dataset

print("Downloading dataset...")
dataset = load_dataset("Amod/mental_health_counseling_conversations", split="train")

output = []

for item in dataset:
    human = item["Context"].strip()
    tild = item["Response"].strip()
    if len(human) > 5 and len(tild) > 5:
        output.append(f"### Human: {human}")
        output.append(f"### Tild: {tild}")
        output.append("")

print(f"Processed {len(output)} lines!")

with open("data/daily_dialog.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print("Saved to data/daily_dialog.txt!")