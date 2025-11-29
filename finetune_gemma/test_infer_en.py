from infer_runtime import generate_reply

MODEL_PATH = "/srv/python_envs/shared_env/B/gemma-3-1b-it"
ADAPTER_DIR = "/srv/python_envs/shared_env/A/NanoVerse/finetune_gemma/adapters/player_bigtest/latest"

tests = [
    "Hey, what's up?",
    "I'm bored, what can we do?",
    "Where are you on the map right now?",
    "Do you want to start a new quest together?",
]

def run_test(msg: str):
    chat = [
        {"role": "user", "content": msg},
    ]
    print("========================================")
    print("PROMPT:", msg)
    answer = generate_reply(MODEL_PATH, ADAPTER_DIR, chat)
    print("REPLY:", answer)

if __name__ == "__main__":
    for m in tests:
        run_test(m)
