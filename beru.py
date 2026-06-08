import sys

from src.venv_bootstrap import ensure_project_venv

ensure_project_venv()

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 beru.py train   - Train Beru")
        print("  python3 beru.py finetune - Upgrade Beru's brain")
        print("  python3 beru.py chat    - Chat with Beru")
        print("  python3 beru.py voice   - Talk to Beru")
        print("  python3 beru.py api     - Start Beru API for GUI (port 8000, voice endpoints)")
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
        from beru_api import app
        app.run(port=8000, debug=False)

if __name__ == '__main__':
    main()