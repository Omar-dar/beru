import re

input_file = "data/en_train_human.txt"
output_file = "data/conversation_data.txt"

with open(input_file,"r",encoding="utf8") as f:
    lines = f.readlines()

with open(output_file,"w",encoding="utf8") as out:

    for line in lines:

        msgs = [
            m.strip()
            for m in line.split("__eou__")
            if m.strip()
        ]

        msgs = [
            m for m in msgs
            if not re.fullmatch(r'[\d\s]+', m)
        ]

        for i in range(0, len(msgs)-1, 2):

            human = msgs[i]
            tild = msgs[i+1]

            out.write(
f"""### Human: {human}
### Tild: {tild}

"""
)

print("Done")