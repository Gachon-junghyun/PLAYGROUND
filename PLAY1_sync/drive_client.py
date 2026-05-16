"""
Google Drive API 래퍼.

OAuth 2.0 (Desktop app flow) — 첫 실행 시 브라우저로 인증, token.json 저장.
이후엔 token.json 자동 갱신.

scope: drive.file (앱이 만들거나 열어준 파일만 접근, 보안)
"""
from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CHUNK_SIZE = 10 * 1024 * 1024  # 10MB resumable chunks


class DriveClient:
    def __init__(self, credentials_path: Path, token_path: Path):
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self.creds = self._auth()
        self.service = build("drive", "v3", credentials=self.creds, cache_discovery=False)

    def _auth(self) -> Credentials:
        creds: Credentials | None = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"credentials.json not found at {self.credentials_path}.\n"
                        "Get it from https://console.cloud.google.com/ → "
                        "APIs & Services → Credentials → OAuth 2.0 Client (Desktop)."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
            self.token_path.write_text(creds.to_json(), encoding="utf-8")
            os.chmod(self.token_path, 0o600) if os.name != "nt" else None
        return creds

    # ── Upload / Update ──────────────────────────────────────────────

    def upload_or_update(
        self,
        local_path: str | Path,
        remote_name: str,
        folder_id: str | None = None,
        file_id: str | None = None,
        progress_cb=None,
    ) -> str:
        """파일 업로드. file_id 주어지면 update(같은 ID 유지), 없으면 create."""
        local_path = str(local_path)
        media = MediaFileUpload(
            local_path, resumable=True, chunksize=CHUNK_SIZE
        )
        if file_id:
            request = self.service.files().update(
                fileId=file_id, media_body=media, fields="id,name,modifiedTime,size,md5Checksum"
            )
        else:
            metadata: dict = {"name": remote_name}
            if folder_id:
                metadata["parents"] = [folder_id]
            request = self.service.files().create(
                body=metadata,
                media_body=media,
                fields="id,name,modifiedTime,size,md5Checksum",
            )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status and progress_cb:
                progress_cb(status.progress())
        return response

    # ── Download ─────────────────────────────────────────────────────

    def download(
        self,
        file_id: str,
        local_path: str | Path,
        progress_cb=None,
    ) -> None:
        local_path = Path(local_path)
        request = self.service.files().get_media(fileId=file_id)
        with open(local_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request, chunksize=CHUNK_SIZE)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status and progress_cb:
                    progress_cb(status.progress())

    # ── Lookup ───────────────────────────────────────────────────────

    def find_by_name(self, name: str, folder_id: str | None = None) -> list[dict]:
        # drive.file scope: 본 앱이 만들거나 열어준 파일만 보임
        q_parts = [f"name = '{name}'", "trashed = false"]
        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")
        q = " and ".join(q_parts)
        result = self.service.files().list(
            q=q,
            fields="files(id,name,modifiedTime,size,md5Checksum,parents)",
            pageSize=10,
        ).execute()
        return result.get("files", [])

    def get_meta(self, file_id: str) -> dict:
        return self.service.files().get(
            fileId=file_id,
            fields="id,name,modifiedTime,size,md5Checksum,parents",
        ).execute()

    def ensure_folder(self, name: str, parent_id: str | None = None) -> str:
        """이름으로 폴더 찾고 없으면 생성. drive.file scope에선 앱이 만든 폴더만 보임."""
        q = (
            f"name = '{name}' and "
            "mimeType = 'application/vnd.google-apps.folder' and "
            "trashed = false"
        )
        if parent_id:
            q += f" and '{parent_id}' in parents"
        result = self.service.files().list(
            q=q, fields="files(id,name)", pageSize=5
        ).execute()
        files = result.get("files", [])
        if files:
            return files[0]["id"]
        metadata: dict = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            metadata["parents"] = [parent_id]
        folder = self.service.files().create(body=metadata, fields="id").execute()
        return folder["id"]
