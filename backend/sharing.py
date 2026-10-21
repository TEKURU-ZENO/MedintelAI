"""Minimal expiring download links for MedIntel AI OCR Studio.

For production medical use, place behind authentication, HTTPS, rate limiting,
access logging, and an authorization policy. The URL is a bearer secret.
"""
import hashlib
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(tags=["secure sharing"])
DB_PATH = Path("./data/medintel_shares.sqlite3")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


with connect() as db:
    db.execute("""CREATE TABLE IF NOT EXISTS shares (
        token_hash TEXT PRIMARY KEY,
        content BLOB NOT NULL,
        filename TEXT NOT NULL,
        media_type TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        revoked INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        revoke_hash TEXT
    )""")
    # Safe migration for databases created by earlier versions.
    columns = {row[1] for row in db.execute("PRAGMA table_info(shares)").fetchall()}
    if "revoke_hash" not in columns:
        db.execute("ALTER TABLE shares ADD COLUMN revoke_hash TEXT")


class ShareRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5_000_000)
    format: Literal["txt", "json"]
    filename: str = Field(default="medintel-export", max_length=180)
    expires_in_hours: int = Field(default=24, ge=1, le=168)


@router.post("/shares", status_code=201)
def create_share(payload: ShareRequest, request: Request):
    token = secrets.token_urlsafe(32)
    revoke_token = secrets.token_urlsafe(32)
    revoke_hash = hashlib.sha256(revoke_token.encode("utf-8")).hexdigest()
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=payload.expires_in_hours)
    # Never accept a path from the client as the download filename.
    safe_name = re.sub(r"[^A-Za-z0-9._ -]", "_", Path(payload.filename).name).strip(" .") or f"medintel.{payload.format}"
    if not safe_name.lower().endswith(f".{payload.format}"):
        safe_name += f".{payload.format}"
    media_type = "text/plain; charset=utf-8" if payload.format == "txt" else "application/json; charset=utf-8"
    with connect() as db:
        db.execute("INSERT INTO shares(token_hash,content,filename,media_type,expires_at,created_at,revoke_hash) VALUES(?,?,?,?,?,?,?)",
                   (token_hash, payload.content.encode("utf-8"), safe_name, media_type, expiry.isoformat(), now.isoformat(), revoke_hash))
    base = str(request.base_url).rstrip("/")
    return {"share_url": f"{base}/shares/{token}", "revoke_token": revoke_token, "expires_at": expiry.isoformat(), "filename": safe_name}


@router.get("/shares/{token}")
def download_share(token: str):
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with connect() as db:
        row = db.execute("SELECT * FROM shares WHERE token_hash=? AND revoked=0", (token_hash,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Share link not found or revoked")
    if datetime.now(timezone.utc) >= datetime.fromisoformat(row["expires_at"]):
        raise HTTPException(status_code=410, detail="Share link expired")
    return StreamingResponse(BytesIO(row["content"]), media_type=row["media_type"], headers={
        "Content-Disposition": f'attachment; filename="{row["filename"]}"',
        "Cache-Control": "no-store, private", "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer"
    })


@router.delete("/shares/{token}", status_code=204)
def revoke_share(token: str, x_share_revocation_token: str = Header(default="")):
    """Revoke a link using the separate secret returned only at creation time.

    For production deployments, also enforce the app's authenticated user/tenant
    authorization policy and audit this operation.
    """
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    revoke_hash = hashlib.sha256(x_share_revocation_token.encode("utf-8")).hexdigest()
    with connect() as db:
        cur = db.execute(
            "UPDATE shares SET revoked=1 WHERE token_hash=? AND revoke_hash=? AND revoked=0",
            (token_hash, revoke_hash),
        )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Share link not found or revocation token invalid")
    return Response(status_code=204)
