import sys

from src.venv_bootstrap import ensure_project_venv

ensure_project_venv()

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 tild.py train   - Train Tild")
        print("  python3 tild.py finetune - Upgrade Tild's brain")
        print("  python3 tild.py chat    - Chat with Tild")
        print("  python3 tild.py voice   - Talk to Tild")
        print("  python3 tild.py api     - Start Tild API for GUI (port 8000)")
        return

    if sys.argv[1] == 'train':
        from src.train import train
        train()

    elif sys.argv[1] == 'finetune':
        from src.finetune import finetune
        finetune()

    elif sys.argv[1] == 'chat':
        from chat.chat import chat
        chat()

    elif sys.argv[1] == 'voice':
        from chat.voice_chat import voice_chat
        voice_chat()

    elif sys.argv[1] == 'api':
        from tild_api import app
        app.run(port=8000, debug=False)

if __name__ == '__main__':
    main()