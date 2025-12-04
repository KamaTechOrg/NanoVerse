

import subprocess
import sqlite3
import shlex
import time
import sys
from pathlib import Path
from typing import Optional
import shutil  
ROOT = Path("/srv/python_envs/shared_env/A/NanoVerse")
PROJ = ROOT / "project" / "NanoVerse"
FT = ROOT / "finetune_gemma"

sys.path.append(str(ROOT)) 
from finetune_gemma.config_adapters import adapter_dir_for  

PLAYERS_DB = PROJ / "data" / "players.db"

USERS_DIR = FT / "data" / "users"
ADAPTERS = FT / "adapters"
SFT_TRAIN = FT / "sft_train.py"
BASE_MODEL = Path("/srv/python_envs/shared_env/B/gemma-3-1b-it")

MIN_TRAIN = 5
PY = "/srv/python_envs/shared_env/venv/bin/python"
NOW = time.strftime("%Y%m%d-%H%M%S")


def run(cmd: str, cwd: Optional[Path] = None, check: bool = True):
    print("[RUN]", cmd)
    return subprocess.run(cmd, cwd=cwd, shell=True, check=check)


def prepare_data_all_users():
    print("[PREPARE] converting raw chats to JSONL per user ...")
    cmd = f"{shlex.quote(PY)} {shlex.quote(str(FT / 'prepare_user_jsonl.py'))}"
    run(cmd)


def sync_users():
    print("[SYNC] syncing train/val splits for existing users ...")
    cmd = f"{shlex.quote(PY)} {shlex.quote(str(FT / 'auto_sync_players.py'))}"
    run(cmd)


def count_lines(p: Path) -> int:
    if not p.exists():
        return 0
    with p.open(encoding="utf-8") as f:
        return sum(1 for _ in f)


def _existing_split_dir_for(user_id: str) -> Optional[Path]:
    candidates = [
        USERS_DIR / f"player{user_id}_split",  
        USERS_DIR / f"{user_id}_split",        
    ]

    best_dir, best_lines = None, -1
    for d in candidates:
        if not d.exists():
            continue
        n = count_lines(d / "train.jsonl")
        if n > best_lines:
            best_dir, best_lines = d, n

    if best_dir is None or best_lines <= 0:
        return None
    return best_dir


def list_players():
    con = sqlite3.connect(str(PLAYERS_DB))
    cur = con.cursor()
    try:
        cur.execute("SELECT user_id FROM players")
        rows = cur.fetchall()

    finally:
        con.close()

    players = []
    for (user_id,) in rows:
        user_id = str(user_id)
        split_dir = _existing_split_dir_for(user_id)
        if split_dir is None:
            print(f"[INFO] skip user {user_id}: no split dir found.")
            continue
        print(f"[INFO] using split for {user_id}: {split_dir}")
        players.append((user_id, split_dir))
    return players


def ensure_latest_symlink(adapter_root: Path, new_run_dir: Path):
    latest = adapter_root / "latest"

    try:
        if latest.is_symlink() or latest.is_file():
            latest.unlink()
        elif latest.exists() and latest.is_dir():
            shutil.rmtree(latest)
    except Exception as e:
        print(f"[WARN] unable to remove old 'latest': {e}")

    try:
        latest.symlink_to(new_run_dir, target_is_directory=True)
        print(f"[ADAPTER] latest -> {new_run_dir}")
    except Exception as e:
        print(f"[ERROR] failed to link latest -> {new_run_dir}: {e}")


def _adapter_root_for(user_id: str) -> Path:
    if user_id.startswith("player"):
        return ADAPTERS / user_id
    return ADAPTERS / f"player{user_id}"


def train_one(user_id: str, split_dir: Path):
    train_file = split_dir / "train.jsonl"
    n_train = count_lines(train_file)
    print(f"[CHECK] user {user_id}: train={n_train} ({train_file})")

    if n_train < MIN_TRAIN:
        print(f"[SKIP] {user_id}: not enough samples (<{MIN_TRAIN})")
        return

    user_adapter_root = _adapter_root_for(user_id)
    run_dir = user_adapter_root / f"run_{NOW}"
    run_dir.mkdir(parents=True, exist_ok=True)

    train_cmd = " ".join([
        shlex.quote(PY), shlex.quote(str(SFT_TRAIN)),
        "--model", shlex.quote(str(BASE_MODEL)),
        "--data_file", shlex.quote(str(train_file)),
        "--out_dir", shlex.quote(str(run_dir)),
        "--epochs", "1",
        "--bsz", "1",
        "--lr", "1e-4",
        "--max_len", "768",
        "--qlora",
    ])
    run(train_cmd)
    ensure_latest_symlink(user_adapter_root, run_dir)


def main():
    print(f"[NIGHTLY] started at {NOW}")
    prepare_data_all_users()
    sync_users()

    print("[NIGHTLY] enumerating players ...")
    players = list_players()

    for user_id, split_dir in players:
        try:
            train_one(user_id, split_dir)
        except subprocess.CalledProcessError as e:
            print(f"[ERR] training failed for {user_id}: {e}")
        except Exception as e:
            print(f"[ERR] unexpected error for {user_id}: {e}")

    print("[NIGHTLY] done.")


if __name__ == "__main__":
    main()
