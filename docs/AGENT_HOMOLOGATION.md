# Homologação dos Agentes Lean Six Sigma

Atualização: 23/11/2026

## Situação

Homologação parcial do Coordenador/Validador DMAIC em desenvolvimento.

### Resultado executado

- 54 testes aprovados no GitHub Actions após inclusão do Coordenador e persistência
- 0 falhas na suíte automatizada
- GitHub Actions executando em PR/push
- Coordenador ponta a ponta implementado em primeira versão
- Estado, evidências e histórico persistidos em SQLite

## Cobertura atual

### Regras gerais / gates — 19 testes

Cobrem:
- bloqueio de informação futura no Define;
- bloqueio de solução antecipada no problema;
- meta numérica sem baseline;
- fonte e baseline obrigatórios em Measure;
- MSA quando necessário;
- Analyze sem ferramenta obrigatória;
- causa validada somente com evidência;
- premissas materiais conflitantes;
- indicador primário Y versus driver X;
- piloto e avaliação de risco em Improve;
- sustentação e plano de reação em Control;
- saving realizado/aprovado com evidência;
- cost avoidance não tratado como saving direto;
- dupla contagem financeira;
- classificação válida das evidências;
- Cp/Cpk somente com estabilidade verificada;
- limites de especificação com fonte válida;
- mínimo/máximo observados não tratados como especificação;
- método de carta de controle declarado.

### Casos reais — 11 testes

#### Megatech
- Define aceita somente a oportunidade disponível no início;
- resultados posteriores são bloqueados quando vazam para Define;
- Analyze aceita validação técnica de QA sem obrigar Ishikawa/5 Porquês;
- Improve exige evidência de implementação.

#### Bosch
- conflito material de float/premissa bloqueia decisão até reconciliação;
- lead time/driver não substitui automaticamente o Y do problema;
- benefício pode permanecer estimado sem ser promovido a realizado.

#### Planmar
- inventário total pode ser evidência de contexto em Define;
- inventário total não vira automaticamente baseline da disponibilidade no preparo.

#### Governança
- dupla contagem de savings é bloqueada;
- melhorias de alto risco exigem análise de risco e piloto quando aplicável.

### Cálculos analíticos — 11 testes

Cobrem:
- Pareto por contagem;
- Pareto ponderado por custo e acumulado 100%;
- fórmula de Cp/Cpk contra referência;
- limites de especificação inválidos;
- variância zero;
- limites de controle exploratórios;
- série vazia;
- antes × depois;
- baseline zero sem divisão por zero;
- sugestão de mapeamento de colunas.

## Estado por fase

| Fase | Cobertura atual | Situação |
|---|---|---|
| Define | problema, escopo, indicador Y, meta/baseline, cronologia, benefício preliminar | boa |
| Measure | baseline, fonte, alinhamento do indicador, MSA, premissas | boa, falta MSA matemático |
| Analyze | pergunta, evidência, causa, ferramenta contextual, QA técnico | boa, faltam regressão/teste de hipótese |
| Improve | solução, piloto, risco, implementação | intermediária |
| Control | responsável, frequência, reação, sustentação, financeiro, CEP | boa, falta seleção automática de carta |
| Coordenador | orquestração, roteamento contextual, bloqueio de gate e avanço entre fases | primeira versão implementada e testada |

## Lacunas obrigatórias antes da homologação integrada

1. **Integração do Coordenador**
   - tela beta adicionada ao app;
   - validar uso manual em projeto real;
   - migrar persistência de SQLite local para armazenamento durável em nuvem antes de produção.

2. **Sistema de Medição**
   - implementar/validar MSA real quando aplicável;
   - distinguir dados administrativos de medições físicas;
   - não exigir MSA inadequadamente em toda base logística.

3. **Estatística avançada**
   - teste de hipótese;
   - regressão;
   - correlação sem causalidade;
   - seleção de carta de controle pelo tipo de dado/amostragem;
   - regras de causas especiais.

4. **Improve**
   - critérios de seleção de solução;
   - comparação de alternativas;
   - teste/piloto;
   - antes × depois com indicador de equilíbrio.

5. **Control**
   - janela mínima de sustentação definida por projeto;
   - evidência do novo padrão;
   - plano de reação;
   - distinção resultado operacional × HG5/validação financeira.

6. **Integração**
   - unir correção de upload do PR #5 com o validador após revisão;
   - persistir projetos sem depender de SQLite temporário em nuvem;
   - testes de interface com arquivos reais.

## Critério proposto para homologação

Um agente/fase só é considerado homologado quando:
- todos os testes críticos passam;
- nenhum teste permite dado inventado, causalidade falsa ou saving indevido;
- casos reais e casos sintéticos passam;
- saída registra fato, cálculo, estimativa, hipótese, recomendação ou A CONFIRMAR;
- cálculo quantitativo possui referência reproduzível;
- passagem de gate é rastreável.

O sistema completo só deve ser chamado de homologado após um projeto atravessar Define → Measure → Analyze → Improve → Control sem intervenção corretiva no comportamento do Coordenador.


## Atualização — Coordenador DMAIC

Componentes implementados:
- `core/dmaic_state.py`: estado estruturado do projeto e fase atual;
- `core/evidence_registry.py`: evidências com liberação por fase;
- `core/tool_router.py`: seleção contextual de ferramentas;
- `core/dmaic_coordinator.py`: avaliação de gate, avanço e histórico;
- persistência em `dmaic_projects`, `dmaic_evidence` e `dmaic_history`;
- página **Coordenador DMAIC — beta** no Streamlit.

Comportamentos comprovados:
- Megatech percorre D→M→A→I→C sem expor evidência futura;
- Bosch avança de Define e bloqueia em Measure com premissa material conflitante;
- Planmar bloqueia quando inventário total é usado como baseline de outro indicador;
- pendências não materiais podem resultar em **Pronto com pendências**;
- ferramentas são recomendadas por contexto, não por lista fixa.

Limite atual:
- em ambiente Vercel, o SQLite fica em `/tmp` e não é armazenamento persistente entre instâncias. Para produção será necessário banco durável.
