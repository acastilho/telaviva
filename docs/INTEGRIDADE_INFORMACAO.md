# Integridade da Informação

## Regra obrigatória

O Instituto Tela Viva não deve exibir, gerar ou apresentar informações falsas, inventadas, erradas, não confirmadas ou enganosas como se fossem fatos reais.

A interface deve sempre preferir **dados reais e verificáveis**. Quando uma fonte de dados não estiver disponível, quando uma operação ainda não tiver sido persistida ou quando não houver confirmação suficiente, o sistema deve mostrar explicitamente um estado como **“dados não carregados”**, **“informação não disponível”** ou **“alteração ainda não persistida”**.

## Regras de implementação

- Dados operacionais de usuários, criadores, aulas, transmissões, audiência, seguidores, vendas, pagamentos, receita, gorjetas, gravações, denúncias, auditoria e métricas devem vir de serviços, banco de dados ou integrações reais.
- É proibido preencher telas de homologação ou produção com nomes, e-mails, valores, contadores, depoimentos, eventos ou métricas fictícias apresentados como dados reais.
- Dados de exemplo só podem existir em testes automatizados, fixtures ou documentação quando estiverem identificados inequivocamente como exemplo e não forem renderizados como informação operacional real.
- Uma operação local não pode ser rotulada como “salva”, “cadastrada”, “processada”, “paga”, “publicada” ou equivalente sem confirmação da fonte responsável pela persistência.
- Falhas de carregamento não podem ser convertidas silenciosamente em `0`, lista vazia ou sucesso se isso puder induzir o usuário a acreditar que o resultado foi confirmado.
- Conteúdo produzido por IA deve distinguir fatos verificados, inferências e incertezas. Quando uma afirmação factual depender de uma fonte externa, a origem deve ser rastreável no fluxo que gerou a informação.
- A ausência de dados deve ser tratada como estado de interface válido, não como motivo para inventar conteúdo demonstrativo.

## Critério de aceite

Uma tela atende a esta regra quando qualquer informação apresentada como factual possui uma fonte real identificável ou é explicitamente marcada como indisponível, não carregada, estimada ou não persistida conforme o caso.

<!-- COMPROMISSO-GERAL-A-CASTILHO -->

---

## Compromisso Geral

**Sempre na melhor prática. No caminho do bem maior.**

**Ir até o fim sem sair do caminho, seja ele qual for.**
