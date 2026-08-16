# AGENTS.md — Tela Viva

## Objetivo

Construir uma plataforma segura de aprendizado ao vivo onde profissionais compartilham tela,
câmera e áudio com consentimento explícito. Nunca implemente acesso remoto ao computador.

## Regras de engenharia

- Preserve a separação entre `frontend/`, `backend/` e infraestrutura.
- Faça mudanças pequenas, testáveis e auditáveis.
- Valide autenticação, autorização e entitlement no backend.
- Não armazene segredos, tokens, dados bancários ou mídia privada no repositório ou em logs.
- Trate gravações, chat, pagamentos e identidade como dados sensíveis.
- Exija consentimento explícito para captura, gravação e publicação de áudio, vídeo ou tela.
- Use provedores por interfaces; evite acoplar pagamentos, streaming ou notificações.
- Adicione testes para regras de acesso, dinheiro, moderação e idempotência.
- Atualize `docs/` quando contratos, arquitetura ou escopo mudarem.

## Verificação mínima

- Backend: `pytest` e `python -m compileall -q app tests`.
- Frontend: `npm run typecheck` e `npm run build`.
- Infraestrutura: `docker compose config --quiet`.
