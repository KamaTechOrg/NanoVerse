
from __future__ import annotations
from pathlib import Path
import sqlite3
import sys

PLAYERS_DB = Path("/srv/python_envs/shared_env/A/NanoVerse/project/NanoVerse/data/players.dev.db")

FT_ROOT = Path(__file__).resolve().parent

def adapter_dir_for(player_id: str) -> Path:
    return FT_ROOT / "adapters" / f"player{player_id}" / "latest"

def link_adapter(player_id: str) -> str:
   
    adapter_dir = adapter_dir_for(player_id)
    adapter_dir.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(PLAYERS_DB))
    cur = con.cursor()

    cur.execute("PRAGMA table_info(players)")
    cols = {r[1] for r in cur.fetchall()}
    required = {"user_id", "chunk_id", "row", "col"}
    if not required.issubset(cols) or "adapter_path" not in cols:
        con.close()
        raise RuntimeError(
            f"[ERROR] players table does not match expected schema. "
            f"Expected columns: {sorted(required | {'adapter_path'})}, got: {sorted(cols)}"
        )

    cur.execute("SELECT 1 FROM players WHERE user_id = ?", (player_id,))
    exists = cur.fetchone() is not None
    if not exists:
        cur.execute(
            "INSERT INTO players (user_id, chunk_id, row, col) VALUES (?, ?, ?, ?)",
            (player_id, "", 0, 0),
        )

    cur.execute(
        "UPDATE players SET adapter_path = ? WHERE user_id = ?",
        (str(adapter_dir), player_id),
    )

    con.commit()
    con.close()
    print(f"[OK] adapter_path set for {player_id}: {adapter_dir}")
    return str(adapter_dir)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 link_adapter_to_db.py <PLAYER_ID>")
        sys.exit(1)
    link_adapter(sys.argv[1])
