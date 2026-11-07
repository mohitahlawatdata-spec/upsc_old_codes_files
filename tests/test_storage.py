"""The local artifact adapter mirrors the S3-compatible storage contract."""

from dataclasses import replace
from pathlib import Path

import pytest

from mainsmaster.settings import Settings
from mainsmaster.storage.local import LocalArtifactStore
from mainsmaster.storage.s3 import S3ArtifactStore


def test_local_store_uploads_and_deletes_prefix(tmp_path: Path) -> None:
    source = tmp_path / "work"
    source.mkdir()
    (source / "report.json").write_text("{}", encoding="utf-8")
    store = LocalArtifactStore(tmp_path / "artifacts")

    keys = store.upload_tree(source, "users/one/run")

    assert keys == ["users/one/run/report.json"]
    assert (tmp_path / "artifacts/users/one/run/report.json").read_text() == "{}"
    store.delete_prefix("users/one/run")
    assert not (tmp_path / "artifacts/users/one/run").exists()


def test_local_store_refuses_to_delete_root(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path)
    with pytest.raises(ValueError, match="Refusing"):
        store.delete_prefix("")


def test_s3_store_uploads_with_portable_client_configuration(tmp_path: Path, monkeypatch) -> None:
    calls = []

    class FakeClient:
        def upload_file(self, *args, **kwargs):
            calls.append((args, kwargs))

    import boto3

    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: FakeClient())
    source = tmp_path / "work"
    source.mkdir()
    (source / "report.json").write_text("{}", encoding="utf-8")
    settings = Settings(
        database_url="",
        google_api_key="",
        ocr_model="test",
        eval_model="test",
        restructure_model="test",
        mentor_model="test",
        data_dir=tmp_path,
        poppler_path=None,
        max_upload_mb=1,
        max_pdf_pages=1,
    )
    settings = replace(
        settings,
        artifact_store="s3",
        s3_endpoint_url="http://minio:9000",
        s3_region="us-east-1",
        s3_bucket="mainsmaster",
        s3_access_key_id="test",
        s3_secret_access_key="test-secret",
    )

    keys = S3ArtifactStore(settings).upload_tree(source, "users/one/run")

    assert keys == ["users/one/run/report.json"]
    assert calls[0][0][1:3] == ("mainsmaster", "users/one/run/report.json")
    assert calls[0][1]["ExtraArgs"] == {"ContentType": "application/json"}
