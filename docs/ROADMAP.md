# Roadmap

O roadmap é orientado a resultados; datas serão definidas depois da validação de capacidade e riscos.

## 0. Fundação — atual

- monorepo com React/TypeScript e FastAPI;
- PostgreSQL e Redis no ambiente local;
- configuração por ambiente, health checks, testes e documentação;
- pipeline de qualidade preparado para CI.

## 1. Identidade e descoberta

- cadastro, login, recuperação e RBAC (`admin`, `creator`, `viewer`);
- perfis públicos e onboarding de criador;
- catálogo, categorias, busca e status ao vivo;
- migrações, telemetria e trilha de auditoria inicial.

## 2. Experiência ao vivo

- spike e escolha documentada do provedor/protocolo de vídeo;
- criação, agendamento, entrada e encerramento de transmissões;
- chat em tempo real, presença, reações e moderação;
- testes de carga, acessibilidade e degradação controlada.

## 3. Apoio financeiro

- spike jurídico/financeiro e escolha do provedor;
- checkout, confirmação por webhook idempotente e histórico;
- repasse ao criador, conciliação, reembolsos e antifraude;
- painéis de criador e administração.

## 4. Beta e escala

- denúncias, bloqueios e ferramentas operacionais;
- SLOs, alertas, backups e teste de restauração;
- hardening de segurança, privacidade/LGPD e resposta a incidentes;
- experimento beta, análise das métricas do PRD e ajustes de retenção.
