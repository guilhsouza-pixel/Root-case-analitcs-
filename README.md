# ROOT CAUSE ANALYTICS — Lean Six Sigma

Aplicação Streamlit para importar Excel/CSV, analisar ocorrências e organizar investigações de causa raiz com evidências.

## Funcionalidades

- Importação de `.xls`, `.xlsx` e `.csv`, escolha de aba e prévia
- Detecção automática e mapeamento manual de colunas
- Filtros globais por período, fornecedor, processo, categoria e demais dimensões disponíveis
- Visão executiva, indicadores, insights e Pareto 80/20
- Estratificação com heatmap, barras e tabela dinâmica
- Tendências, média móvel e carta de controle exploratória
- Estatística descritiva, Cp e Cpk com limites de especificação informados pelo usuário
- Ishikawa 6M com hipótese, evidência e situação da validação
- 5 Porquês, matriz causa e efeito 0/1/3/9 e FMEA
- Plano 5W2H, cronograma, ações vencidas e progresso
- Projeto DMAIC completo
- Comparação antes × depois e matriz esforço × impacto
- Relatório executivo em PDF e exportação dos dados filtrados
- Persistência local em SQLite

## Executar localmente

Requer Python 3.11 ou superior.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

No Windows, ative o ambiente com:

```powershell
.venv\Scripts\activate
```

O banco `root_cause_analytics.db` é criado automaticamente na primeira execução.

## Publicar no Streamlit Community Cloud

1. Envie esta pasta para um repositório no GitHub.
2. Entre em `share.streamlit.io` com a conta do GitHub.
3. Selecione o repositório, a branch e indique `app.py` como arquivo principal.
4. Clique em **Deploy**.

## Publicar na Vercel

O projeto inclui `Dockerfile.vercel` para executar o Streamlit em um contêiner. O SQLite é gravado em `/tmp` quando a variável `VERCEL` está presente, evitando escrita no código empacotado. Esse armazenamento é temporário; use PostgreSQL/Supabase para manter projetos e planos de ação entre reinicializações.

### Observação sobre SQLite na nuvem

O SQLite funciona normalmente durante a sessão. Entretanto, no Streamlit Community Cloud, o disco do contêiner não é armazenamento permanente e pode ser recriado. Para uso corporativo com histórico compartilhado, substitua a persistência por PostgreSQL/Supabase. A análise de planilhas e o download dos relatórios continuam funcionando sem essa mudança.

## Estrutura

```text
root_cause_analytics/
├── .streamlit/config.toml
├── app.py
├── Dockerfile.vercel
├── vercel.json
├── core/
│   ├── analytics.py
│   ├── database.py
│   ├── report.py
│   └── schema.py
├── requirements.txt
└── tests/test_analytics.py
```

## Testes

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Regras de interpretação

- Correlação não é tratada como causalidade.
- Causas do Ishikawa começam como hipóteses e precisam de evidência.
- Cp/Cpk só são exibidos com dados suficientes e limites de especificação válidos.
- O NPR apoia a priorização do FMEA, mas severidade alta permanece destacada.
- Insights são descritivos; decisões devem considerar o processo real e a validação em campo.
