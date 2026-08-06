from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

from .config import INSTANCE_DIR, settings


class StorageError(RuntimeError):
    pass


class StorageService:
    """Almacenamiento local, filesystem externo o S3-compatible.

    Los métodos de archivo evitan cargar respaldos completos en memoria y la
    enumeración se utiliza para inventarios de continuidad, no para exponer
    documentos al usuario.
    """

    def __init__(self) -> None:
        self.backend = settings.storage_backend
        if self.backend == "filesystem":
            if not settings.external_storage_root:
                raise StorageError("EXTERNAL_STORAGE_ROOT es obligatorio para filesystem")
            self.local_root = Path(settings.external_storage_root).expanduser().resolve()
        else:
            self.local_root = INSTANCE_DIR
        self.local_root.mkdir(parents=True, exist_ok=True)
        self._client = None
        if self.backend == "s3":
            try:
                import boto3
                from botocore.config import Config
            except ImportError as exc:  # pragma: no cover - solo producción S3
                raise StorageError("Instala boto3 para usar STORAGE_BACKEND=s3") from exc
            connect_timeout = float(os.getenv("S3_CONNECT_TIMEOUT_SECONDS", "5"))
            read_timeout = float(os.getenv("S3_READ_TIMEOUT_SECONDS", "10"))
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url or None,
                region_name=settings.s3_region or None,
                aws_access_key_id=settings.s3_access_key or None,
                aws_secret_access_key=settings.s3_secret_key or None,
                config=Config(
                    signature_version="s3v4",
                    connect_timeout=connect_timeout,
                    read_timeout=read_timeout,
                    retries={"max_attempts": 1, "mode": "standard"},
                    tcp_keepalive=True,
                    s3={"addressing_style": "path"},
                ),
            )

    @staticmethod
    def normalize_key(key: str) -> str:
        clean = key.strip().lstrip("/").replace("..", "_")
        if not clean:
            raise StorageError("La clave de almacenamiento está vacía")
        return clean

    def put_bytes(self, key: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        key = self.normalize_key(key)
        if self.backend in {"local", "filesystem"}:
            path = (self.local_root / key).resolve()
            if self.local_root not in path.parents and path != self.local_root:
                raise StorageError("Ruta de almacenamiento no permitida")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            return key
        assert self._client is not None
        self._client.put_object(Bucket=settings.s3_bucket, Key=key, Body=content, ContentType=content_type)
        return key

    def put_file(self, key: str, source: Path, content_type: str = "application/octet-stream") -> str:
        """Store a file without reading the complete payload into memory."""
        key = self.normalize_key(key)
        source = source.resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        if self.backend in {"local", "filesystem"}:
            destination = (self.local_root / key).resolve()
            if self.local_root not in destination.parents and destination != self.local_root:
                raise StorageError("Ruta de almacenamiento no permitida")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source != destination:
                shutil.copy2(source, destination)
            return key
        assert self._client is not None
        extra = {"ContentType": content_type} if content_type else None
        if extra:
            self._client.upload_file(str(source), settings.s3_bucket, key, ExtraArgs=extra)
        else:
            self._client.upload_file(str(source), settings.s3_bucket, key)
        return key

    def local_path(self, key: str) -> Path | None:
        if self.backend not in {"local", "filesystem"}:
            return None
        path = (self.local_root / self.normalize_key(key)).resolve()
        if self.local_root not in path.parents and path != self.local_root:
            return None
        return path

    def get_bytes(self, key: str) -> bytes:
        key = self.normalize_key(key)
        if self.backend in {"local", "filesystem"}:
            path = self.local_path(key)
            if not path or not path.is_file():
                raise FileNotFoundError(key)
            return path.read_bytes()
        assert self._client is not None
        response = self._client.get_object(Bucket=settings.s3_bucket, Key=key)
        return response["Body"].read()

    def exists(self, key: str) -> bool:
        if self.backend in {"local", "filesystem"}:
            path = self.local_path(key)
            return bool(path and path.is_file())
        assert self._client is not None
        try:
            self._client.head_object(Bucket=settings.s3_bucket, Key=self.normalize_key(key))
            return True
        except Exception:
            return False

    def delete(self, key: str) -> None:
        key = self.normalize_key(key)
        if self.backend in {"local", "filesystem"}:
            path = self.local_path(key)
            if path:
                path.unlink(missing_ok=True)
            return
        assert self._client is not None
        self._client.delete_object(Bucket=settings.s3_bucket, Key=key)

    def list_objects(self, prefix: str = "") -> list[dict[str, object]]:
        """Return a deterministic object inventory used by continuity checks."""
        prefix = prefix.strip().lstrip("/")
        if self.backend in {"local", "filesystem"}:
            base = (self.local_root / prefix).resolve() if prefix else self.local_root
            if self.local_root not in base.parents and base != self.local_root:
                raise StorageError("Prefijo de almacenamiento no permitido")
            if not base.exists():
                return []
            rows = []
            for path in sorted(base.rglob("*")):
                if path.is_file():
                    rows.append({
                        "key": str(path.relative_to(self.local_root)).replace("\\", "/"),
                        "size": path.stat().st_size,
                        "etag": "",
                    })
            return rows
        assert self._client is not None
        rows: list[dict[str, object]] = []
        token = None
        while True:
            kwargs = {"Bucket": settings.s3_bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            response = self._client.list_objects_v2(**kwargs)
            for item in response.get("Contents", []):
                rows.append({"key": item["Key"], "size": int(item.get("Size", 0)), "etag": str(item.get("ETag", "")).strip('"')})
            if not response.get("IsTruncated"):
                break
            token = response.get("NextContinuationToken")
        return sorted(rows, key=lambda item: str(item["key"]))

    def presigned_url(self, key: str, expires: int = 900) -> str:
        if self.backend != "s3":
            raise StorageError("Las URL firmadas solo aplican a S3")
        assert self._client is not None
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": self.normalize_key(key)},
            ExpiresIn=expires,
        )

    def verified_probe(self) -> dict[str, object]:
        payload = b"Calcula tu Huella storage probe v1.0"
        expected = hashlib.sha256(payload).hexdigest()
        key = ".health/storage-v100final.probe"
        try:
            self.put_bytes(key, payload, "text/plain")
            restored = self.get_bytes(key)
            actual = hashlib.sha256(restored).hexdigest()
            return {
                "backend": self.backend,
                "ok": actual == expected,
                "sha256": actual,
                "detail": str(self.local_root) if self.backend in {"local", "filesystem"} else settings.s3_bucket,
            }
        except Exception as exc:
            return {"backend": self.backend, "ok": False, "sha256": "", "detail": str(exc)}
        finally:
            try:
                self.delete(key)
            except Exception:
                pass

    def diagnostics(self) -> dict[str, object]:
        result = self.verified_probe()
        if result["ok"]:
            result["detail"] = f"{result['detail']} · lectura/escritura SHA-256 correcta"
        return result


storage = StorageService()
