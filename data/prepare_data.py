from datasets import load_dataset

print("Downloading OpenAssistant dataset...")
dataset = load_dataset("OpenAssistant/oasst1", split="train")

output = []

for item in dataset:
    if item["role"] == "prompter" and item["lang"] == "en":
        human = item["text"].strip()
        output.append(f"### Human: {human}")
    elif item["role"] == "assistant" and item["lang"] == "en":
        tild = item["text"].strip()
        output.append(f"### Tild: {tild}")
        output.append("")

print(f"Processed {len(output)} lines!")

with open("data/conversations.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print("Saved!")