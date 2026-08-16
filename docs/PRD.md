# PRD — Tela Viva

## Visão

Permitir que pessoas aprendam observando profissionais em atividade real e possam interagir e
apoiá-los financeiramente. Slogan: **Veja. Aprenda. Apoie.**

## Perfis

- `ADMIN`: operação, confiança e segurança da plataforma.
- `CREATOR`: perfil profissional, agenda, transmissão, conteúdo e recebimentos.
- `VIEWER`: descoberta, participação, compras, assinaturas e apoio.

## MVP

1. Cadastro, autenticação e RBAC.
2. Perfis de criadores, categorias, busca e filtros.
3. Agenda e lembretes in-app.
4. Sala ao vivo com compartilhamento consentido de tela/câmera/microfone.
5. Chat, perguntas, reações e moderação.
6. Aulas gratuitas, pagas, privadas e para assinantes.
7. Pedidos, pagamentos, entitlements, gorjetas e comissão.
8. Gravação com consentimento e regras de retenção.

## Princípios de segurança

- Sem acesso remoto ao dispositivo do criador.
- Captura e gravação somente após consentimento explícito e revogável.
- Autorização e entitlement sempre verificados no servidor.
- Webhooks financeiros idempotentes e segredos fora do código.
