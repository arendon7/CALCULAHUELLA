from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from .config import INSTANCE_DIR, settings


class StorageError(RuntimeError):
    pass


class StorageService:
    """Almacenamiento local, filesystem externo o S3-compatible.

    La construcción del servicio no depende de red ni de un volumen externo.
    Los recursos externos se validan en la primera operación o en
    ``verified_probe``. El cliente operativo conserva reintentos acotados;
    el probe de readiness usa un cliente independiente y fail-fast.
    """

    def __init__(self) -> None:
        self.backend = settings.storage_backend
        self.local_root = (
            Path(settings.external_storage_root).expanduser().resolve()
            if self.backend == "filesystem" and settings.external_storage_root
            else INSTANCE_DIR
        )
        self._client = None

    @staticmethod
    def normalize_key(key: str) -> str:
        clean = key.strip().lstrip("/").replace("..", "_")
        if not clean:
            raise StorageError("La clave de almacenamiento está vacía")
        return clean

    def _ensure_local_root(self) -> Path:
        if self.backend == "filesystem" and not settings.external_storage_root:
            raise StorageError("EXTERNAL_STORAGE_ROOT es obligatorio para filesystem")
        try:
            self.local_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError(f"No fue posible preparar el almacenamiento filesystem: {exc}") from exc
        return self.local_root

    @staticmethod
    def _validate_s3_configuration() -> None:
        if not settings.s3_bucket:
            raise StorageError("S3_BUCKET es obligatorio para S3")
        if settings.s3_endpoint_url and (not settings.s3_access_key or not settings.s3_secret_key):
            raise StorageError("S3_ACCESS_KEY y S3_SECRET_KEY son obligatorios para endpoints S3 personalizados")
        if bool(settings.s3_access_key) != bool(settings.s3_secret_key):
            raise StorageError("S3_ACCESS_KEY y S3_SECRET_KEY deben configurarse como pareja")

    def _build_s3_client(self, *, probe: bool = False):
        try:
            import boto3
            from botocore.config import Config
        except ImportError as exc:  # pragma: no cover - solo producción S3
            raise StorageError("Instala boto3 para usar STORAGE_BACKEND=s3") from exc
        self._validate_s3_configuration()
        if probe:
            timeout = max(float(settings.external_probe_timeout_seconds), 0.1)
            connect_timeout = timeout
            read_timeout = timeout
            attempts = 1
        else:
            connect_timeout = max(float(settings.s3_connect_timeout_seconds), 0.1)
            read_timeout = max(float(settings.s3_read_timeout_seconds), 0.1)
            attempts = max(1, int(settings.s3_max_attempts))
        client_config = Config(
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
            retries={"total_max_attempts": attempts, "mode": "standard"},
        )
        return boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            region_name=settings.s3_region or None,
            aws_access_key_id=settings.s3_access_key or None,
            aws_secret_access_key=settings.s3_secret_key or None,
            config=client_config,
        )

    def _s3_client(self):
        if self._client is None:
            self._client = self._build_s3_client()
        return self._client

    def put_bytes(self, key: str, content: bytes, content_type: str = "application/octet-stream") -> str:
        key = self.normalize_key(key)
        if self.backend in {"local", "filesystem"}:
            root = self._ensure_local_root()
            path = (root / key).resolve()
            if root not in path.parents and path != root:
                raise StorageError("Ruta de almacenamiento no permitida")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            return key
        self._s3_client().put_object(Bucket=settings.s3_bucket, Key=key, Body=content, ContentType=content_type)
        return key

    def put_file(self, key: str, source: Path, content_type: str = "application/octet-stream") -> str:
        """Store a file without reading the complete payload into memory."""
        key = self.normalize_key(key)
        source = source.resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        if self.backend in {"local", "filesystem"}:
            root = self._ensure_local_root()
            destination = (root / key).resolve()
            if root not in destination.parents and destination != root:
                raise StorageError("Ruta de almacenamiento no permitida")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source != destination:
                shutil.copy2(source, destination)
            return key
        client = self._s3_client()
        extra = {"ContentType": content_type} if content_type else None
        if extra:
            client.upload_file(str(source), settings.s3_bucket, key, ExtraArgs=extra)
        else:
            client.upload_file(str(source), settings.s3_bucket, key)
        return key

    def local_path(self, key: str) -> Path | None:
        if self.backend not in {"local", "filesystem"}:
            return None
        root = self._ensure_local_root()
        path = (root / self.normalize_key(key)).resolve()
        if root not in path.parents and path != root:
            return None
        return path

    def get_bytes(self, key: str) -> bytes:
        key = self.normalize_key(key)
        if self.backend in {"local", "filesystem"}:
            path = self.local_path(key)
            if not path or not path.is_file():
                raise FileNotFoundError(key)
            return path.read_bytes()
        response = self._s3_client().get_object(Bucket=settings.s3_bucket, Key=key)
        return response["Body"].read()

    def exists(self, key: str) -> bool:
        if self.backend in {"local", "filesystem"}:
            try:
                path = self.local_path(key)
            except StorageError:
                return False
            return bool(path and path.is_file())
        try:
            self._s3_client().head_object(Bucket=settings.s3_bucket, Key=self.normalize_key(key))
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
        self._s3_client().delete_object(Bucket=settings.s3_bucket, Key=key)

    def list_objects(self, prefix: str = "") -> list[dict[str, object]]:
        """Return a deterministic object inventory used by continuity checks."""
        prefix = prefix.strip().lstrip("/")
        if self.backend in {"local", "filesystem"}:
            root = self._ensure_local_root()
            base = (root / prefix).resolve() if prefix else root
            if root not in base.parents and base != root:
                raise StorageError("Prefijo de almacenamiento no permitido")
            if not base.exists():
                return []
            rows = []
            for path in sorted(base.rglob("*")):
                if path.is_file():
                    rows.append({
                        "key": str(path.relative_to(root)).replace("\\", "/"),
                        "size": path.stat().st_size,
                        "etag": "",
                    })
            return rows
        client = self._s3_client()
        rows: list[dict[str, object]] = []
        token = None
        while True:
            kwargs = {"Bucket": settings.s3_bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            response = client.list_objects_v2(**kwargs)
            for item in response.get("Contents", []):
                rows.append({"key": item["Key"], "size": int(item.get("Size", 0)), "etag": str(item.get("ETag", "")).strip('"')})
            if not response.get("IsTruncated"):
                break
            token = response.get("NextContinuationToken")
        return sorted(rows, key=lambda item: str(item["key"]))

    def presigned_url(self, key: str, expires: int = 900) -> str:
        if self.backend != "s3":
            raise StorageError("Las URL firmadas solo aplican a S3")
        return self._s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": self.normalize_key(key)},
            ExpiresIn=expires,
        )

    def verified_probe(self) -> dict[str, object]:
        payload = b"Calcula tu Huella storage probe v1.0"
        expected = hashlib.sha256(payload).hexdigest()
        key = ".health/storage-v100final.probe"
        if self.backend == "s3":
            client = None
            try:
                client = self._build_s3_client(probe=True)
                client.put_object(Bucket=settings.s3_bucket, Key=key, Body=payload, ContentType="text/plain")
                response = client.get_object(Bucket=settings.s3_bucket, Key=key)
                restored = response["Body"].read()
                actual = hashlib.sha256(restored).hexdigest()
                return {
                    "backend": self.backend,
                    "ok": actual == expected,
                    "sha256": actual,
                    "detail": settings.s3_bucket,
                }
            except Exception as exc:
                return {"backend": self.backend, "ok": False, "sha256": "", "detail": str(exc)}
            finally:
                if client is not None:
                    try:
                        client.delete_object(Bucket=settings.s3_bucket, Key=key)
                    except Exception:
                        pass
        try:
            self.put_bytes(key, payload, "text/plain")
            restored = self.get_bytes(key)
            actual = hashlib.sha256(restored).hexdigest()
            return {
                "backend": self.backend,
                "ok": actual == expected,
                "sha256": actual,
                "detail": str(self.local_root),
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
