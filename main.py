"""
AI Doctor's Office Receptionist -- fully local, fully free.

Run this after completing the setup steps in README.md:
    python main.py

Each run simulates one incoming call: greeting -> name -> reason for visit ->
available slots -> booking -> confirmation.
"""

from conversation import run_call

if __name__ == "__main__":
    print("=" * 60)
    print("AI Receptionist starting. Press Ctrl+C to hang up at any time.")
    print("=" * 60)
    try:
        run_call()
    except KeyboardInterrupt:
        print("\nCall ended.")
