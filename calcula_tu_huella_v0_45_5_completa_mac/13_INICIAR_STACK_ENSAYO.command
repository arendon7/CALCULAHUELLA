#!/usr/bin/env bash
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT" || exit 1
clear 2>/dev/null || true
cat <<'BANNER'
============================================================
      CALCULA TU HUELLA V0.45 · STACK PRODUCTIVO CERTIFICABLE
============================================================
BANNER
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker Desktop no está instalado o no está iniciado."
  echo "Instálalo/ábrelo y vuelve a ejecutar este comando."
  read -r -p "Presiona Enter para cerrar..." _
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose no está disponible."
  read -r -p "Presiona Enter para cerrar..." _
  exit 1
fi
ENV_FILE="$ROOT/.env.trial"
RECEIPT="$ROOT/ENSAYO_DOCKER_CREDENCIALES.txt"
if [ ! -f "$ENV_FILE" ]; then
  PYTHON="python3"
  command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python"
  SESSION_SECRET="$($PYTHON -c 'import secrets; print(secrets.token_urlsafe(48))')"
  POSTGRES_PASSWORD="$($PYTHON -c 'import secrets; print(secrets.token_urlsafe(24))')"
  MINIO_PASSWORD="$($PYTHON -c 'import secrets; print(secrets.token_urlsafe(24))')"
  METRICS_TOKEN="$($PYTHON -c 'import secrets; print(secrets.token_urlsafe(32))')"
  ALERT_SECRET="$($PYTHON -c 'import secrets; print(secrets.token_urlsafe(32))')"
  ADMIN_PASSWORD="$($PYTHON -c 'import secrets; print("Cth!"+secrets.token_urlsafe(14))')"
  GRAFANA_PASSWORD="$($PYTHON -c 'import secrets; print("Graf!"+secrets.token_urlsafe(12))')"
  cat > "$ENV_FILE" <<EOF
SESSION_SECRET=$SESSION_SECRET
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
MINIO_ROOT_USER=calculatuhuella
MINIO_ROOT_PASSWORD=$MINIO_PASSWORD
METRICS_TOKEN=$METRICS_TOKEN
ALERT_WEBHOOK_SECRET=$ALERT_SECRET
BOOTSTRAP_ADMIN_EMAIL=admin@calculatuhuella.local
BOOTSTRAP_ADMIN_PASSWORD=$ADMIN_PASSWORD
GRAFANA_ADMIN_PASSWORD=$GRAFANA_PASSWORD
EOF
  chmod 600 "$ENV_FILE"
  cat > "$RECEIPT" <<EOF
Calcula tu Huella V0.45 · credenciales del ensayo Docker
Aplicación: https://localhost:8443
Usuario: admin@calculatuhuella.local
Contraseña: $ADMIN_PASSWORD
Grafana: http://localhost:3000
Usuario Grafana: admin
Contraseña Grafana: $GRAFANA_PASSWORD
MinIO: http://localhost:9001
Prometheus: http://localhost:9090
Alertmanager: http://localhost:9093
EOF
  chmod 600 "$RECEIPT"
fi
echo "Construyendo y levantando PostgreSQL, MinIO, aplicación, Caddy, Prometheus, Alertmanager y Grafana..."
docker compose --env-file "$ENV_FILE" -f docker-compose.trial.yml up -d --build || {
  echo "No fue posible iniciar el stack. Revisa Docker Desktop."
  read -r -p "Presiona Enter para cerrar..." _
  exit 1
}
echo "Esperando la aplicación..."
READY=0
for _ in $(seq 1 90); do
  if curl -kfsS https://localhost:8443/api/health >/dev/null 2>&1; then READY=1; break; fi
  sleep 2
done
if [ "$READY" -ne 1 ]; then
  echo "La aplicación no respondió. Mostrando logs:"
  docker compose --env-file "$ENV_FILE" -f docker-compose.trial.yml logs --tail=80 app
  read -r -p "Presiona Enter para cerrar..." _
  exit 1
fi
echo "Esperando PostgreSQL, MinIO, Prometheus, Alertmanager y Grafana..."
SERVICES_READY=0
for _ in $(seq 1 90); do
  if curl -fsS http://localhost:9000/minio/health/ready >/dev/null 2>&1 \
    && curl -fsS http://localhost:9090/-/ready >/dev/null 2>&1 \
    && curl -fsS http://localhost:9093/-/ready >/dev/null 2>&1 \
    && curl -fsS http://localhost:3000/api/health >/dev/null 2>&1; then
    SERVICES_READY=1
    break
  fi
  sleep 2
done
if [ "$SERVICES_READY" -ne 1 ]; then
  echo "Uno o más servicios externos no quedaron disponibles."
  docker compose --env-file "$ENV_FILE" -f docker-compose.trial.yml ps
  read -r -p "Presiona Enter para cerrar..." _
  exit 1
fi
echo "Ejecutando certificación productiva de la versión..."
if docker compose --env-file "$ENV_FILE" -f docker-compose.trial.yml exec -T app python scripts/certify_release.py --strict --notes "Stack Docker V0.45"; then
  echo "Certificación estricta aprobada y evidencia almacenada en MinIO."
else
  echo "La certificación quedó bloqueada. Consulta Operación y seguridad."
fi
echo
echo "Stack disponible: https://localhost:8443"
echo "Credenciales: $RECEIPT"
open https://localhost:8443 2>/dev/null || true
read -r -p "Presiona Enter para cerrar..." _
