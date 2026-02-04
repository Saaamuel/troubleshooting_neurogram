# Troubleshooting Neurogram

Este repositório contém a **base estruturada de troubleshooting da Neurogram**.

O objetivo é uma **base de conhecimento**, pronta para:
- suporte interno
- auxílio a usuários
- automação (RAG / LLM / SLM)
- governança de conhecimento operacional

Toda alteração é validada automaticamente por **schema + taxonomia + CI**. ou "validators"



# Estrutura do repositório




# “caso”
Um caso representa um problema único e recorrente que temos na neurogram, descrito de forma que:
- humanos entendam
- máquinas consigam classificar e recuperar

Cada arquivo em `cases/` deve conter **apenas um problema**.
Cada arquivo `cases/` deve ser bem descrito (ainda esta em desenvolvimento e afinamento de detalhes)



#Campos obrigatórios de um caso

Todo arquivo em `cases/*.yaml` **DEVE** conter:

```yaml
id: NG-TROUBLE-XXX
title: "Título curto e claro"

problem_summary: >
  Resumo em linguagem natural do problema.
  Deve explicar o que o usuário percebe e em que contexto ocorre.

user_symptoms:
  - "Como o usuário descreve o problema"
  - "Frases reais usadas em tickets ou mensagens"

origin:
  - configuracao
  - integridade_de_arquivo
  - autenticacao
  # (valores válidos em taxonomy/origin.yaml)

layer:
  - ingestao
  - processamento
  - visualizacao
  # (valores válidos em taxonomy/layer.yaml)

severity:
  user_impact: baixa | media | alta
  system_impact: baixa | media | alta

owner_team:
  - suporte
  - infra
  - produto

root_causes:
  - description: "Causa raiz provável"
    confidence: alta | media | baixa

business_rule:
  - "Regra fixa do sistema"
  - description: "Regra com contexto adicional"
    scope: ingestao | laudo | visualizacao

resolution_steps:
  - "Passo 1"
  - "Passo 2"

triage_questions:
  - "Pergunta para entender o contexto"

evidence_to_collect:
  - "Logs"
  - "Arquivo EDF"

do_not_do:
  - "Não apagar arquivos do bucket"

#OBS: é uma boa prática que os arquivos `cases/*.yaml` sejam bem detalhados. (Está ainda em processo de desenvolvimento e testes)
