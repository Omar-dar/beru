import sys

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tild.py train  - Train Tild")
        print("  python tild.py chat   - Chat with Tild")
        return

    if sys.argv[1] == 'train':
        from src.train import train
        train()

    elif sys.argv[1] == 'chat':
        from chat.chat import chat
        chat()

if __name__ == '__main__':
    main()