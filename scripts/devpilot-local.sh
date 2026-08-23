#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT/.runtime"
WEB_PID_FILE="$RUNTIME_DIR/web.pid"
WEB_LOG="$RUNTIME_DIR/web.log"
API_LOG="$RUNTIME_DIR/api.log"
API_PORT="${API_PORT:-8000}"
WEB_PORT_START="${WEB_PORT_START:-5173}"
WEB_PORT_END="${WEB_PORT_END:-5190}"

mkdir -p "$RUNTIME_DIR"

log() { printf '\n[ Tela Viva ] %s\n' "$*"; }
fail() { printf '\n[ ERRO ] %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || fail "Docker não encontrado. A API requer Python 3.12 e será executada pelo Docker."
docker compose version >/dev/null 2>&1 || fail "Docker Compose não está disponível."
command -v curl >/dev/null 2>&1 || fail "curl não encontrado."
command -v npm >/dev/null 2>&1 || fail "npm não encontrado."

cd "$ROOT"

LAN_IP="${LAN_IP:-$(hostname -I 2>/dev/null | awk '{for (i=1;i<=NF;i++) if ($i !~ /^127\./ && $i !~ /^172\.(1[7-9]|2[0-9]|3[0-1])\./) {print $i; exit}}')}"
if [[ -z "${LAN_IP:-}" ]]; then
  LAN_IP="127.0.0.1"
fi

port_open() {
  (echo >/dev/tcp/127.0.0.1/"$1") >/dev/null 2>&1
}

find_web_port() {
  local port
  for ((port=WEB_PORT_START; port<=WEB_PORT_END; port++)); do
    if ! port_open "$port"; then
      echo "$port"
      return 0
    fi
  done
  return 1
}

cleanup_old_web() {
  if [[ -f "$WEB_PID_FILE" ]]; then
    local old_pid
    old_pid="$(cat "$WEB_PID_FILE" 2>/dev/null || true)"
    if [[ "$old_pid" =~ ^[0-9]+$ ]] && kill -0 "$old_pid" 2>/dev/null; then
      log "Encerrando frontend anterior controlado pelo Tela Viva (PID $old_pid)..."
      kill "$old_pid" 2>/dev/null || true
      for _ in {1..20}; do
        kill -0 "$old_pid" 2>/dev/null || break
        sleep .1
      done
    fi
    rm -f "$WEB_PID_FILE"
  fi
}

show_backend_failure() {
  printf '\n[ DIAGNÓSTICO API ]\n' >&2
  docker compose logs --no-color --tail=120 migrate api 2>&1 | tee "$API_LOG" >&2 || true
  printf '\nLog salvo em: %s\n' "$API_LOG" >&2
}

log "1/5 Pré-check de ambiente"
printf 'LAN detectada: %s\n' "$LAN_IP"
printf 'API esperada: http://%s:%s\n' "$LAN_IP" "$API_PORT"

log "2/5 Subindo PostgreSQL, Redis, migrações e API Python 3.12"
export API_CORS_ORIGINS="[\"http://localhost:${WEB_PORT_START}\",\"http://${LAN_IP}:${WEB_PORT_START}\"]"
if ! docker compose up -d --build postgres redis migrate api; then
  show_backend_failure
  fail "Falha ao construir/subir o backend. Veja o diagnóstico acima."
fi

log "3/5 Validando API"
API_READY=0
for _ in {1..60}; do
  if curl -fsS --max-time 2 "http://127.0.0.1:${API_PORT}/health/live" >/dev/null 2>&1; then
    API_READY=1
    break
  fi
  sleep 1
 done

if [[ "$API_READY" -ne 1 ]]; then
  show_backend_failure
  fail "A porta ${API_PORT} não respondeu ao health check /health/live."
fi

log "4/5 Preparando frontend com porta única e API correta"
cleanup_old_web
WEB_PORT="$(find_web_port)" || fail "Nenhuma porta livre entre ${WEB_PORT_START} e ${WEB_PORT_END}."
export API_CORS_ORIGINS="[\"http://localhost:${WEB_PORT}\",\"http://${LAN_IP}:${WEB_PORT}\"]"
export VITE_API_URL="http://${LAN_IP}:${API_PORT}"
export VITE_LIVE_SOCKET_URL="http://${LAN_IP}:${API_PORT}"

# Recria apenas a API para aplicar a origem real escolhida, sem reiniciar banco/redis.
docker compose up -d --no-deps --force-recreate api >/dev/null

cd "$ROOT/apps/web"
if [[ ! -d node_modules ]]; then
  npm install
fi
nohup npm run dev -- --host 0.0.0.0 --port "$WEB_PORT" --strictPort >"$WEB_LOG" 2>&1 &
WEB_PID=$!
echo "$WEB_PID" > "$WEB_PID_FILE"

WEB_READY=0
for _ in {1..40}; do
  if curl -fsS --max-time 2 "http://127.0.0.1:${WEB_PORT}/" >/dev/null 2>&1; then
    WEB_READY=1
    break
  fi
  if ! kill -0 "$WEB_PID" 2>/dev/null; then
    break
  fi
  sleep .5
 done

if [[ "$WEB_READY" -ne 1 ]]; then
  printf '\n[ DIAGNÓSTICO FRONTEND ]\n' >&2
  tail -120 "$WEB_LOG" >&2 || true
  fail "Frontend não respondeu. Log: $WEB_LOG"
fi

log "5/5 Smoke test final"
curl -fsS --max-time 3 "http://127.0.0.1:${API_PORT}/health/live" >/dev/null
curl -fsS --max-time 3 "http://127.0.0.1:${WEB_PORT}/" >/dev/null

cat <<EOF

✓ Tela Viva iniciado com sucesso

Frontend local : http://localhost:${WEB_PORT}/
Frontend celular: http://${LAN_IP}:${WEB_PORT}/
API local      : http://localhost:${API_PORT}/
API celular    : http://${LAN_IP}:${API_PORT}/
Health         : http://${LAN_IP}:${API_PORT}/health/live
Docs API       : http://${LAN_IP}:${API_PORT}/docs

PID frontend: ${WEB_PID}
Log frontend: ${WEB_LOG}
Log API em falha: ${API_LOG}

Metodologia aplicada: pré-check → build → health check → integração → smoke test.
EOF
