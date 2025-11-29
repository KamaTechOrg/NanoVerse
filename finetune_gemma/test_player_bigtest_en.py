from infer_runtime import generate_reply

model_path = "/srv/python_envs/shared_env/B/gemma-3-1b-it"
adapter_dir = "/srv/python_envs/shared_env/A/NanoVerse/finetune_gemma/adapters/player_bigtest/latest"

tests = [
    "What quest are you doing right now?",
    "Where should I go if I want better loot?",
    "Can you help me reach the northern forest?",
    "What are you exploring at the moment?",
    "Is there something fun we can do together?",
]

for prompt in tests:
    chat = [{"role": "user", "content": prompt}]

    answer = generate_reply(
        chatml=chat,
        adapter_dir=adapter_dir,
        max_new_tokens=48,
        temperature=0.3,
        top_p=0.9,
    )

    print("\n" + "="*40 + "\n")
    print("PROMPT:", prompt)
    print("REPLY:", answer)
