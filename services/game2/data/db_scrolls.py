# services/game2/data/db_scrolls.py  
import aiosqlite
from pathlib import Path
from datetime import datetime

from ..core.settings import DATA_DIR


class ScrollDB:
    """
    Scrolls storage backed by SQLite with an atomic "mark found once" update.
    Schema:
      id INTEGER PK AUTOINCREMENT
      chunk_id TEXT, row INT, col INT (יחודיים יחד)
      content TEXT
      author_user_id TEXT
      found_by_user_id TEXT NULL
      found_at TEXT NULL (ISO datetime)
    """

    def __init__(self, path: str | Path | None = None):
        if path is None:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            path = DATA_DIR / "scrolls.sqlite3"
        self.path = str(path)
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        if self.conn is None:
            self.conn = await aiosqlite.connect(self.path)
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA foreign_keys=ON;")
            await self.conn.commit()

    async def ensure_schema(self):
        # ודאי שיש חיבור
        if self.conn is None:
            await self.connect()

        await self.conn.execute("""
        CREATE TABLE IF NOT EXISTS scrolls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chunk_id TEXT NOT NULL,
            row INTEGER NOT NULL,
            col INTEGER NOT NULL,
            content TEXT NOT NULL,
            author_user_id TEXT NOT NULL,
            found_by_user_id TEXT NULL,
            found_at TEXT NULL
        );
        """)
        # ייחוד לפי מיקום
        await self.conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_scrolls_position
        ON scrolls(chunk_id, row, col);
        """)
        await self.conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_scrolls_pos
        ON scrolls(chunk_id, row, col);
        """)
        await self.conn.commit()

    async def load_scroll(self, chunk_id: str, row: int, col: int):
        """
        החזרת dict של ההודעה במיקום הנתון, או None.
        """
        if self.conn is None:
            await self.connect()
        sql = """SELECT id, chunk_id, row, col, content, author_user_id, found_by_user_id, found_at
                 FROM scrolls WHERE chunk_id=? AND row=? AND col=? LIMIT 1"""
        async with self.conn.execute(sql, (chunk_id, row, col)) as cur:
            r = await cur.fetchone()
        if not r:
            return None
        keys = ["id","chunk_id","row","col","content","author_user_id","found_by_user_id","found_at"]
        d = {k: r[i] for i,k in enumerate(keys)}
        # תאימות לאחור: לפעמים בקוד קוראים לשדה 'author'
        d["author"] = d["author_user_id"]
        return d

    async def save_scroll(self, scroll) -> int:
        """
        יצירה/עדכון לפי מיקום:
        אם כבר קיימת הודעה באותו (chunk,row,col) — נעדכן את התוכן והמחבר.
        מחזירה id של הרשומה אחרי הפעולה.
        scroll: אובייקט עם .chunk_id, .position = (row, col), .content, .author (user_id)
        """
        if self.conn is None:
            await self.connect()

        chunk_id = scroll.chunk_id
        row, col = scroll.position
        content = scroll.content
        author_user_id = getattr(scroll, "author", getattr(scroll, "author_user_id", ""))

        # UPSERT לפי מיקום
        sql = """
        INSERT INTO scrolls (chunk_id,row,col,content,author_user_id)
        VALUES (?,?,?,?,?)
        ON CONFLICT(chunk_id,row,col) DO UPDATE SET
            content=excluded.content,
            author_user_id=excluded.author_user_id
        """
        cur = await self.conn.execute(sql, (chunk_id, row, col, content, author_user_id))
        await self.conn.commit()

        # אם נוצרה חדשה: lastrowid, אם עודכנה — צריך לשלוף את ה-id
        if cur.lastrowid:
            return cur.lastrowid
        async with self.conn.execute(
            "SELECT id FROM scrolls WHERE chunk_id=? AND row=? AND col=?",
            (chunk_id, row, col)
        ) as c2:
            r = await c2.fetchone()
        return r[0] if r else None

    async def mark_found_if_null(self, msg_id: int, found_by_user_id: str) -> bool:
        """
        מסמן הודעה כ"נמצאה" רק אם טרם נמצאה. מחזיר True אם עודכן, אחרת False.
        """
        if self.conn is None:
            await self.connect()
        now = datetime.utcnow().isoformat()
        sql = """
        UPDATE scrolls
        SET found_by_user_id = ?, found_at = ?
        WHERE id = ? AND found_by_user_id IS NULL
        """
        cur = await self.conn.execute(sql, (found_by_user_id, now, msg_id))
        await self.conn.commit()
        return cur.rowcount > 0

    async def delete_scroll_by_id(self, msg_id: int):
        if self.conn is None:
            await self.connect()
        await self.conn.execute("DELETE FROM scrolls WHERE id = ?", (msg_id,))
        await self.conn.commit()
