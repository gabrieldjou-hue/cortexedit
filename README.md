# CortexEdit — Plataforma de Pós-Produção de Vídeo com IA

**CortexEdit** é uma plataforma automatizada de pós-produção de vídeo com inteligência artificial. O sistema aceita arquivos de vídeo brutos (upload ou pasta local), executa um pipeline multi-estágio orquestrado por **22 agentes de IA especializados** e entrega versões finais em múltiplos formatos com legendas, normalização de áudio e otimizações de streaming.

---

## Stack Tecnológica

| Camada         | Tecnologia                              |
|----------------|----------------------------------------|
| Backend        | Python 3.14 + FastAPI 2.0              |
| Frontend       | HTML5 + CSS3 + JavaScript (Vanilla)    |
| Processamento  | FFmpeg / ffprobe (via subprocess)      |
| IA             | Simulada (placeholders p/ Whisper, YOLO, FaceNet) |
| Estado         | Em memória (sem banco de dados)        |

---

## Estrutura do Projeto

```
ai-video-editor-platform/
├── backend/
│   ├── app.py                           # Servidor FastAPI (endpoints REST)
│   ├── pipeline_orchestrator.py         # Fachada para o sistema multi-agente
│   ├── context.py                       # Memória compartilhada (SharedContext)
│   ├── agents/
│   │   ├── base_agent.py                # Classe abstrata BaseAgent
│   │   ├── master_orchestrator.py       # MOA — coordena os 22 agentes
│   │   ├── ingestion_agent.py           # 02 — Ingestão de Mídia
│   │   ├── project_organization_agent.py# 03 — Organização de Projeto
│   │   ├── computer_vision_agent.py     # 04 — Visão Computacional
│   │   ├── transcription_agent.py       # 05 — Transcrição
│   │   ├── semantic_analysis_agent.py   # 06 — Análise Semântica
│   │   ├── quality_detection_agent.py   # 07 — Detecção de Qualidade
│   │   ├── curation_agent.py            # 08 — Curadoria
│   │   ├── narrative_agent.py           # 09 — Narrativa
│   │   ├── scripting_agent.py           # 10 — Roteirização
│   │   ├── editing_agent.py             # 11 — Edição
│   │   ├── colorization_agent.py        # 12 — Colorista
│   │   ├── audio_agent.py               # 13 — Áudio
│   │   ├── music_agent.py               # 14 — Música
│   │   ├── subtitle_agent.py            # 15 — Legendas
│   │   ├── visual_identity_agent.py     # 16 — Identidade Visual
│   │   ├── motion_graphics_agent.py     # 17 — Motion Graphics
│   │   ├── export_agent.py              # 18 — Exportação
│   │   ├── quality_control_agent.py     # 19 — Controle de Qualidade (QA)
│   │   ├── logs_audit_agent.py          # 20 — Logs e Auditoria
│   │   ├── memory_agent.py              # 21 — Memória
│   │   ├── learning_agent.py            # 22 — Aprendizado
│   │   ├── narrative_analysis_agent.py  # Análise técnica (ffprobe)
│   │   └── definitions/                 # Definições JSON de cada agente
│   │       ├── 01_master_orchestrator.json
│   │       ├── 02_ingestao_midia.json
│   │       └── ... (22 arquivos)
│   └── modules/
│       ├── ingestion_module.py          # Validação e ingestão de arquivos
│       ├── analysis_module.py           # Análise técnica via ffprobe
│       ├── ai_module.py                 # Motor de IA (simulado)
│       ├── org_module.py                # Organização narrativa por perfil
│       ├── edit_module.py               # Geração de EDL
│       ├── subtitle_module.py           # Geração de legendas SRT
│       ├── audio_module.py              # Processamento de áudio (simulado)
│       ├── color_module.py              # Correção de cor (simulado)
│       ├── graphics_module.py           # Overlays gráficos (simulado)
│       ├── render_module.py             # Renderização via FFmpeg
│       ├── export_module.py             # Exportação multi-formato
│       └── ffmpeg_utils.py              # Utilitários FFmpeg/ffprobe
├── frontend/
│   ├── index.html                       # Página principal (SPA)
│   ├── style.css                        # Design system glass-morphism
│   └── app.js                           # Lógica do frontend
└── exports/                             # Arquivos exportados
```

---

## Catálogo de Agentes (22 Especialistas)

O sistema SIPA (Sistema Inteligente de Produção Audiovisual) é composto por 22 agentes coordenados pelo **Master Orchestrator Agent (MOA)**. As definições completas de cada agente estão em `backend/agents/definitions/*.json`.

| # | Agente | Status | Entrega |
|---|--------|--------|---------|
| 01 | **Master Orchestrator (MOA)** | Real | Coordenação estratégica |
| 02 | **Ingestão de Mídia** | Real | Pacote de mídia validado |
| 03 | **Organização de Projeto** | Heurístico | Projeto estruturado (câmeras, datas) |
| 04 | **Visão Computacional** | Simulado | Mapa visual (pessoas, objetos, faces) |
| 05 | **Transcrição** | Simulado | Transcrição com timestamps |
| 06 | **Análise Semântica** | Simulado | Tópicos, palavras-chave, resumo |
| 07 | **Detecção de Qualidade** | Métricas | Issues técnicas (blur, shake, áudio) |
| 08 | **Curadoria** | Real | Melhores takes selecionados |
| 09 | **Narrativa** | 3 atos | Sequência lógica organizada |
| 10 | **Roteirização** | Ganchos | Script com beats e impacto |
| 11 | **Edição** | Real | EDL com jump/L/J cuts, speed ramp |
| 12 | **Colorista** | Simulado | Color grading + LUTs |
| 13 | **Áudio** | Simulado | Mix finalizado |
| 14 | **Música** | Simulado | Trilha sincronizada |
| 15 | **Legendas** | Real | SRT com estilos |
| 16 | **Identidade Visual** | Simulado | Logo, vinheta, watermark |
| 17 | **Motion Graphics** | Simulado | Animações e títulos |
| 18 | **Exportação** | Real | Multi-formato + master |
| 19 | **Controle de Qualidade (QA)** | Regras | Relatório de aprovação |
| 20 | **Logs e Auditoria** | Real | Audit trail em JSON |
| 21 | **Memória** | RAM | Preferências armazenadas |
| 22 | **Aprendizado** | Simulado | Sugestões de melhoria |

---

## Pipeline de Produção

O pipeline é coordenado pelo **Master Orchestrator Agent (MOA)** em 5 estágios:

```
STAGE 0 — INGESTION
  Agente 02: Ingestion           → valida arquivos, extrai metadados
  Agente 03: Organização Projeto → estrutura projeto (câmeras, datas, cenas)

STAGE 1 — ANALYSIS
  Agente 04: Visão Computacional      → detecta pessoas, objetos, rostos
  Agente 05: Transcrição              → STT com timestamps
  Agente 06: Análise Semântica        → tópicos, palavras-chave, resumo
  Agente 07: Detecção de Qualidade    → detecta tremores, desfoque, ruído

STAGE 2 — AI ENGINE
  Agente 08: Curadoria     → seleciona melhores takes por perfil
  Agente 09: Narrativa     → organiza sequência lógica (3 atos)
  Agente 10: Roteirização  → roteiriza ganchos e momentos de impacto

STAGE 3 — EDITING
  Agente 11: Edição             → gera EDL com jump/L/J cuts, speed ramp, zoom
  Agente 12: Colorista          → color grading e LUTs
  Agente 13: Áudio              → mix de áudio e loudness
  Agente 14: Música             → seleção de trilha sonora
  Agente 15: Legendas           → gera legendas SRT
  Agente 16: Identidade Visual  → logo, vinheta, lower third
  Agente 17: Motion Graphics    → animações, títulos, transições

STAGE 4 — RENDER & EXPORT
  Agente 18: Exportação              → render FFmpeg + export multi-formato
  Agente 19: Controle de Qualidade   → valida entregas, aprova ou reprova
  Agente 20: Logs e Auditoria        → registra tudo em relatório JSON
  Agente 21: Memória                 → armazena preferências do perfil
  Agente 22: Aprendizado             → sugere melhorias para próxima execução
```

### Perfis de Edição

| Perfil         | Comportamento                                    |
|----------------|--------------------------------------------------|
| `podcast`      | Todos os segmentos incluídos                     |
| `youtube`      | Pula os primeiros 5s de cada clipe               |
| `reels`        | Apenas os primeiros 60s totais                   |
| `cinematic`    | Apenas segmentos >= 20s                          |
| `institutional`| Todos os segmentos em ordem                      |

### Formatos de Exportação

| Preset        | Resolução   | Codec  |
|---------------|-------------|--------|
| 16:9 4K       | 3840×2160   | H.264  |
| 9:16 1080p    | 1080×1920   | H.264  |
| 1:1 Square    | 1080×1080   | H.264  |
| Audio Only    | —           | MP3    |

---

## Como Executar

### Pré-requisitos

- Python 3.14+
- FFmpeg + ffprobe no PATH (opcional — app funciona em modo simulado sem eles)

### Instalação

```bash
pip install fastapi uvicorn pydantic python-multipart
```

### Iniciar o servidor

```bash
# A partir do diretório backend/
cd backend && uvicorn app:app --reload --port 8000

# Ou da raiz do projeto:
uvicorn backend.app:app --reload --port 8000 --app-dir backend
```

Acesse `http://localhost:8000` no navegador.

### Endpoints da API

| Método | Rota                              | Descrição                          |
|--------|-----------------------------------|-------------------------------------|
| GET    | `/`                               | Serve a interface web              |
| POST   | `/api/upload_files`               | Upload de arquivos multipart       |
| POST   | `/api/start_job`                  | Inicia o pipeline de produção      |
| GET    | `/api/status`                     | Status atual do pipeline (polling) |
| GET    | `/api/download/{job_id}/{file}`   | Download de arquivo exportado      |
| DELETE | `/api/cancel`                     | Cancela o job em execução          |

---

## Arquitetura

```
Navegador (HTML/CSS/JS) ──HTTP──▶ FastAPI ──thread──▶ PipelineOrchestrator (fachada)
                                                            │
                                              Master Orchestrator Agent (MOA)
                                                            │
       ┌───────┬───────┬───────┬───────┬───────┬───────┬───────┼───────┬───────┬───────┬───────┐
       ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼
      Ing   ProjOrg  CVision  Transc  SemAnal QualDet Curation Narrat  Script   Edit   Color   Audio
       │       │       │       │       │       │       │       │       │       │       │       │
       ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼
      Music  Subtitl  VisIdent MGraph  Export    QA    LogsAud Memory  Learn
       │       │       │       │       │       │       │       │       │
       └───────┴───────┴───────┴───────┴───────┴───────┴───────┴───────┘
```

### Contrato de Orquestração

O comportamento de todos os agentes é regido por um **Contrato de Orquestração** com 12 artigos:

| Artigo | Descrição |
|--------|-----------|
| 1 | Hierarquia: MOA é a autoridade máxima |
| 2 | Responsabilidades exclusivas do Master |
| 3 | Comunicação sempre via Master (nunca direta) |
| 4 | Cada agente tem domínio exclusivo |
| 5 | 22 Agentes oficiais com missões definidas |
| 6 | Protocolo de execução obrigatório |
| 7 | Protocolo de erros: interromper e reportar |
| 8 | Padrão de entrega: resultado + logs + métricas |
| 9 | Memória compartilhada gerenciada pelo Master |
| 10 | Conflitos resolvidos pelo Master |
| 11 | Evolução: novos agentes devem seguir o contrato |
| 12 | Princípios: modularidade, rastreabilidade, auditabilidade |

---

## Regras Gerais (Todos os Agentes)

- Responsabilidade única
- Obedecer exclusivamente ao Master Orchestrator
- Manter isolamento funcional
- Registrar todas as ações em log
- Preservar os arquivos originais (trabalhar sobre cópias)
- Respeitar parâmetros do usuário (formato, duração, estilo)
- Devolver resultados estruturados com métricas de confiança
- Interromper em caso de erro crítico e reportar ao Master
- Operar de forma determinística (reprodutibilidade)
- Manter rastreabilidade completa das decisões

---

## Status do Projeto

**Prototype / Demonstração.** Módulos de IA (visão computacional, transcrição, análise semântica, áudio, cor, música, motion graphics) são simulados com dados mock. Os módulos de ingestão, organização de projeto, detecção de qualidade, curadoria, narrativa, roteirização, edição (EDL), legendas SRT, renderização, exportação via FFmpeg, QA, logs/auditoria e memória são reais e funcionais.

### Limitações Conhecidas

- Sem banco de dados (estado em memória — reiniciar o servidor perde jobs)
- Sem autenticação/autorização
- Sem testes automatizados
- Apenas um job por vez (execução sequencial)
- Sem Dockerfile ou configuração de deploy
- IA simulada (placeholders para Whisper, YOLO, FaceNet, BERT/GPT)
