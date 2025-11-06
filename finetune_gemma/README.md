# Fine-Tuning and Inference for Player-Specific LoRA Adapters (NanoVerse)

This folder contains the scripts, datasets, and adapters used to fine-tune and run inference on *Gemma-3-1B-IT* models for personalized in-game chat agents.

---

## 🧩 Components

- **sft_train.py** — TRL-based Supervised Fine-Tuning (SFT) script with LoRA/QLoRA support  
- **adaptor_inference.py** — Loads the local base model and adapter for testing (no internet required)  
- **data/users/** — JSONL training/test splits per player  
- **adapters/** — Output directory for trained LoRA adapters  
- **preprocess/** — Optional dataset preprocessing utilities  

---

## 🚀 Example: Fine-tuning a Player Adapter

```bash
CUDA_VISIBLE_DEVICES=0 python3 sft_train.py \
  --model /srv/python_envs/shared_env/B/gemma-3-1b-it \
  --data_file data/users/player1_split/train.jsonl \
  --out_dir adapters/player1/latest \
  --epochs 1 \
  --bsz 1 \
  --lr 1e-4 \
  --max_len 768 \
  --qlora
```

### GPU Memory Notes (RTX 2080 Ti, 11 GB)

- **Full precision (bf16/fp16):** ~9 – 10 GB during training  
- **QLoRA 4-bit (nf4):** ~6 – 7 GB during training  

---

## 💬 Example: Local Inference

```bash
python3 adaptor_inference.py \
  --msg "מה נשמע?" \
  --temperature 0 \
  --max_new_tokens 48
```

Output example:
```
🔹 Base: /srv/python_envs/shared_env/B/gemma-3-1b-it
🔹 Adapter: adapters/player1/latest
אני בסדר, תודה!
```

---

## 🧠 How It Works

1. **Fine-tuning** uses TRL’s `SFTTrainer` with LoRA or QLoRA adapters.  
2. **Inference** runs entirely offline — the base model and adapter are loaded from disk.  
3. **System prompts** ensure responses stay concise, in Hebrew, and aligned with each player’s unique style.

---

## 📁 Directory Layout

```
finetune_gemma/
 ├── sft_train.py
 ├── adaptor_inference.py
 ├── preprocess/
 ├── data/users/player1_split/
 │    ├── train.jsonl
 │    └── test.jsonl
 └── adapters/player1/latest/
      ├── adapter_model.safetensors
      ├── adapter_config.json
      ├── tokenizer.json
      ├── tokenizer_config.json
      └── README.md
```

---

## 🧾 Requirements

- **Python 3.12+**
- **transformers >= 4.57**
- **trl >= 0.24**
- **peft >= 0.17**
- **torch >= 2.9**
- **datasets, accelerate**

---

## 🧰 Tips

- To run inference **without GPU**, set:
  ```bash
  CUDA_VISIBLE_DEVICES=""
  ```
- To continue training from a previous adapter:
  ```bash
  --resume_adapter_dir adapters/player1/latest
  ```
- Always verify GPU usage via:
  ```bash
  nvidia-smi
  ```

---

## 📜 License and Attribution

Based on **Gemma-3-1B-IT** by Google.  
Fine-tuning powered by **Hugging Face TRL** and **PEFT**.  
Developed for the **NanoVerse** project — adaptive AI player chats.
