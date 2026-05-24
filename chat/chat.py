import torch
import random
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from src.rag import TildRAG
from src.memory import TildMemory

FALLBACKS = [
    "That is an interesting question! I am still learning about that topic.",
    "Hmm I am not sure about that yet. Ask me something else!",
    "Good question! I need to learn more about that.",
    "I do not have enough knowledge about that yet but I am always learning!",
    "That is beyond what I know right now. But tell me more!",
]

FALLBACKS_AR = [
    "هذا سؤال مثير للاهتمام! لا أزال أتعلم عن هذا الموضوع.",
    "لست متأكداً من ذلك بعد. اسألني شيئاً آخر!",
]

FALLBACKS_SV = [
    "Det är en intressant fråga! Jag lär mig fortfarande.",
    "Jag är inte säker på det ännu. Fråga mig något annat!",
]

def load_tild():
    print("Loading Tild's brain...")
    tokenizer = GPT2Tokenizer.from_pretrained('models/tild_v2')
    model = GPT2LMHeadModel.from_pretrained('models/tild_v2')
    model.eval()
    return model, tokenizer

def is_good_response(response):
    if len(response) < 3:
        return False
    if len(response.split()) < 2:
        return False
    if '###' in response:
        return False
    if len(set(response.split())) < 2:
        return False
    return True

def get_response(model, tokenizer, rag, memory, user_input, language='en'):
    # Check if it is a correction
    if memory.is_correction(user_input):
        # Get last Tild response
        last_exchange = [m for m in memory.conversation_history if m['role'] == 'tild']
        last_question = [m for m in memory.conversation_history if m['role'] == 'human']

        if last_exchange and last_question:
            wrong_answer = last_exchange[-1]['text']
            question = last_question[-2]['text'] if len(last_question) >= 2 else last_question[-1]['text']
            correct = memory.extract_correction(user_input)

            if correct:
                memory.add_correction(wrong_answer, correct, question)
                return "Thank you for correcting me! I will remember that and learn from it."
            else:
                return "I understand I was wrong! Can you tell me the correct answer so I can learn?"

    # First try corrections memory
    for correction in memory.corrections:
        if correction['question'].lower() in user_input.lower():
            return correction['correct']

    # Then try RAG
    rag_answer, score = rag.find_answer(user_input, threshold=0.65)
    if rag_answer:
        print(f"[RAG match: {score:.2f}]")
        return rag_answer

    # Use context + language model
    context = memory.get_context()
    prompt = f"{context}### Human: {user_input}\n### Tild:"
    inputs = tokenizer.encode(prompt, return_tensors='pt')

    with torch.no_grad():
        outputs = model.generate(
            inputs,
            max_new_tokens=80,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.encode('\n')[0]
        )

    generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
    response = generated[len(prompt):].split('\n')[0].strip()

    if not is_good_response(response):
        if language == 'ar':
            response = random.choice(FALLBACKS_AR)
        elif language == 'sv':
            response = random.choice(FALLBACKS_SV)
        else:
            response = random.choice(FALLBACKS)

    return response

def chat():
    model, tokenizer = load_tild()
    rag = TildRAG()
    memory = TildMemory()
    print("Tild is ready! Type your message (or 'quit' to exit)\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == 'quit':
            print("Tild: Goodbye! It was great talking with you.")
            break

        memory.add_to_conversation('human', user_input)
        response = get_response(model, tokenizer, rag, memory, user_input)
        memory.add_to_conversation('tild', response)
        print(f"Tild: {response}\n")

if __name__ == '__main__':
    chat()