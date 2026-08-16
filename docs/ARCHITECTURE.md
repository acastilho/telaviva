# Arquitetura inicial

## Componentes

- `frontend`: React/TypeScript, interface responsiva e APIs nativas de mídia do navegador.
- `backend`: FastAPI, contratos REST e futura comunicação em tempo real.
- `postgres`: identidade, catálogo, agenda, pedidos, entitlement e auditoria.
- `redis`: presença, rate limits, filas e eventos efêmeros.
- Provedor de streaming: interface futura para WebRTC/SFU e gravação.
- Provedor de pagamento: interface com implementação fake no desenvolvimento.

## Limites

O primeiro incremento entrega a fundação executável. Autenticação, transmissão, pagamentos e
gravação serão adicionados em PRs separados, com threat model e testes próprios.

## Direções técnicas

- monólito modular no backend antes de decomposição em serviços;
- comunicação assíncrona apenas quando houver necessidade observável;
- eventos financeiros e de moderação auditáveis;
- mídia fora do banco relacional, com URLs curtas e controle de acesso;
- observabilidade por logs estruturados, métricas e tracing.
