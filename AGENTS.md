# CortexEdit — Anotações Técnicas

## Visão Geral

Sistema de pós-produção automatizada de vídeo. Backend em Python/FastAPI, frontend vanilla HTML/CSS/JS, processamento via FFmpeg. Toda UI e comentários em português.

---

## Convenções de Código

- **Linguagem:** Português (comentários, UI, nomes de arquivo)
- **Backend:** Python 3.14+ com type hints, FastAPI 2.0, Pydantic v2, SQLAlchemy 2.0
- **Frontend:** Vanilla JS (sem frameworks), CSS custom properties, design glass-morphism
- **Banco de dados:** SQLite via SQLAlchemy (WAL mode, foreign keys)
- **Sem testes, sem CI/CD**

---

## Backend

### app.py — Servidor FastAPI

- Porta padrão: 8000 (implícita, usar `uvicorn backend.app:app --reload --port 8000`)
- CORS aberto: `allow_origins=["*"]`
- Cria diretórios `uploads/` e `exports/` na raiz do projeto na inicialização
- Inicializa banco de dados SQLite na startup (`init_db()`)
- Apenas 1 job por vez (variável global `current_job`)
- Upload salva em `uploads/{session_id}/` com nome original do arquivo
- Salva sessões de upload no banco de dados

### database.py — Banco de Dados

- Engine SQLite com WAL mode e foreign keys habilitados
- Arquivo: `cortexedit.db` na raiz do projeto
- Session factory: `SessionLocal()` para cada requisição
- Função `init_db()` cria todas as tabelas na inicialização

### models.py — Modelos SQLAlchemy

- **Job** — Dados principais: id, status, profile, stages, timestamps, output_files, qc_report
- **AgentResult** — Resultado de cada agente: success, data (JSON), timing, confidence
- **JobLog** — Logs granulares: timestamp, level, message
- **JobError** — Erros: agent, error, timestamp
- **UploadSession** — Sessões de upload: files_data, total_size_mb
- **UserPreference** — Preferências de perfil: profile_name, preferences (JSON)

### crud.py — Operações CRUD

- Funções para criar, ler, atualizar e deletar registros
- `create_job()`, `get_job()`, `list_jobs()`, `update_job()`, `complete_job()`
- `save_agent_result()`, `get_agent_results()`
- `save_logs()`, `save_log()`, `get_logs()`
- `save_errors()`, `save_error()`, `get_errors()`
- `create_upload_session()`, `get_upload_session()`
- `save_preference()`, `get_preference()`, `list_preferences()`, `delete_preference()`

### pipeline_orchestrator.py — Orquestrador (Fachada)

- Fachada para o sistema multi-agente SIPA. Mantém compatibilidade com app.py
- Delega toda execução ao **Master Orchestrator Agent (MOA)**
- Estados: `current_stage` (índice 0-4), `stage_percent` (0-100), `logs` (lista), `is_running`
- 5 estágios: `["Ingestion", "Analysis", "AI Engine", "Editing", "Render & Export"]`
- Verifica FFmpeg via `ffmpeg_utils.check_ffmpeg()`
- Fallback para "modo simulação" se FFmpeg não estiver disponível

---

## Sistema Multi-Agente SIPA

Arquitetura baseada no **Contrato de Orquestração Oficial** — 22 agentes especializados + 1 Master Orchestrator.

### Hierarquia Completa

```
MASTER ORCHESTRATOR AGENT (MOA) — 01
│
├── 02. INGESTÃO DE MÍDIA          ── ingestion_agent.py
├── 03. ORGANIZAÇÃO DE PROJETO     ── project_organization_agent.py
├── 04. VISÃO COMPUTACIONAL        ── computer_vision_agent.py
├── 05. TRANSCRIÇÃO                ── transcription_agent.py
├── 06. ANÁLISE SEMÂNTICA          ── semantic_analysis_agent.py
├── 07. DETECÇÃO DE QUALIDADE      ── quality_detection_agent.py
├── 08. CURADORIA                  ── curation_agent.py
├── 09. NARRATIVA                  ── narrative_agent.py
├── 10. ROTEIRIZAÇÃO               ── scripting_agent.py
├── 11. EDIÇÃO                     ── editing_agent.py
├── 12. COLORISTA                  ── colorization_agent.py
├── 13. ÁUDIO                      ── audio_agent.py
├── 14. MÚSICA                     ── music_agent.py
├── 15. LEGENDAS                   ── subtitle_agent.py
├── 16. IDENTIDADE VISUAL          ── visual_identity_agent.py
├── 17. MOTION GRAPHICS            ── motion_graphics_agent.py
├── 18. EXPORTAÇÃO                 ── export_agent.py
├── 19. CONTROLE DE QUALIDADE (QA) ── quality_control_agent.py
├── 20. LOGS E AUDITORIA           ── logs_audit_agent.py
├── 21. MEMÓRIA                    ── memory_agent.py
└── 22. APRENDIZADO                ── learning_agent.py
```

### Fluxo de Execução (5 Estágios)

```
STAGE 0 — INGESTION
  Agente 02: IngestionAgent           → valida arquivos, extrai metadados
  Agente 03: ProjectOrganizationAgent → estrutura projeto (câmeras, datas, cenas)

STAGE 1 — ANALYSIS
  Agente 04: ComputerVisionAgent      → detecta pessoas, objetos, rostos (simulado)
  Agente 05: TranscriptionAgent       → STT com timestamps (simulado)
  Agente 06: SemanticAnalysisAgent    → tópicos, palavras-chave, resumo (simulado)
  Agente 07: QualityDetectionAgent    → detecta tremores, desfoque, ruído (simulado)

STAGE 2 — AI ENGINE
  Agente 08: CurationAgent            → seleciona melhores takes por perfil
  Agente 09: NarrativeAgent           → organiza sequência lógica (3 atos)
  Agente 10: ScriptingAgent           → roteiriza ganchos e momentos de impacto

STAGE 3 — EDITING
  Agente 11: EditingAgent             → gera EDL com jump/L/J cuts, speed ramp, zoom
  Agente 12: ColorizationAgent        → color grading e LUTs (simulado)
  Agente 13: AudioAgent               → mix de áudio e loudness (simulado)
  Agente 14: MusicAgent               → seleção de trilha sonora (simulado)
  Agente 15: SubtitleAgent            → gera legendas SRT (real)
  Agente 16: VisualIdentityAgent      → logo, vinheta, lower third (simulado)
  Agente 17: MotionGraphicsAgent      → animações, títulos, transições (simulado)

STAGE 4 — RENDER & EXPORT
  Agente 18: ExportAgent              → render FFmpeg + export multi-formato (real)
  Agente 19: QualityControlAgent      → valida entregas, aprova ou reprova (real)
  Agente 20: LogsAuditAgent           → registra tudo em relatório JSON
  Agente 21: MemoryAgent              → armazena preferências do perfil
  Agente 22: LearningAgent            → sugere melhorias para próxima execução
```

### Regras do Contrato

- **Artigo 3:** Nenhum agente se comunica diretamente com outro — toda comunicação passa pelo Master
- **Artigo 4:** Cada agente tem responsabilidade exclusiva sobre seu domínio
- **Artigo 6:** Fluxo obrigatório: Receber → Interpretar → Planejar → Distribuir → Executar → Validar → Corrigir → Re-validar → Exportar → Entregar
- **Artigo 7:** Erro → interrompe → registra → relata ao Master → aguarda instrução
- **Artigo 8:** Todo agente entrega: resultado, arquivos, logs, tempo, confiança, limitações, sugestões
- **Artigo 9:** Memória compartilhada (`SharedContext`) gerenciada exclusivamente pelo Master
- **Artigo 10:** Conflitos resolvidos pelo Master (aceitar, repetir, combinar, arbitrar)

### context.py — Memória Compartilhada

- `SharedContext` — dicionário thread-safe com lock
- Chaves: `job_id`, `profile`, `project_assets`, `project_organization`, `cv_data`, `transcripts`, `semantic`, `quality_detection`, `curation`, `narrative`, `script`, `edl`, `audio_mix`, `color_data`, `subtitles`, `visual_identity`, `graphics`, `music`, `master_path`, `exports`, `qc_report`, `logs_audit`, `memory`, `learning`, `logs`, `errors`
- Agentes especializados apenas **leem** do contexto; apenas o Master **escreve**

### agents/base_agent.py — Classe Base

- `BaseAgent(agent_id)` — classe abstrata com método `execute(task, context) -> AgentResult`
- `AgentResult` — dataclass com: `agent_id`, `success`, `data`, `files`, `logs`, `execution_time`, `confidence`, `limitations`, `suggestions`, `error`

### Catálogo Completo de Agentes

| # | Agente | Módulo Real | Status | Entrega |
|---|--------|------------|--------|---------|
| 01 | Master Orchestrator (MOA) | `master_orchestrator.py` | **Real** | Coordenação estratégica |
| 02 | Ingestão de Mídia | `ingestion_module.py` | **Real** | Pacote de mídia validado |
| 03 | Organização de Projeto | — | **Real** (heurística) | Projeto estruturado (câmeras, datas) |
| 04 | Visão Computacional | — | Simulado | Mapa visual (pessoas, objetos, faces) |
| 05 | Transcrição | — | Simulado | Transcrição com timestamps |
| 06 | Análise Semântica | — | Simulado | Tópicos, palavras-chave, resumo |
| 07 | Detecção de Qualidade | — | **Real** (métricas) | Issues técnicas (blur, shake, áudio) |
| 08 | Curadoria | `org_module.py` | **Real** | Melhores takes selecionados |
| 09 | Narrativa | — | **Real** (3 atos) | Sequência lógica organizada |
| 10 | Roteirização | — | **Real** (ganchos) | Script com beats e impacto |
| 11 | Edição | `edit_module.py` | **Real** | EDL com jump/LJ cuts, speed ramp |
| 12 | Colorista | `color_module.py` | Simulado | Color grading + LUTs |
| 13 | Áudio | `audio_module.py` | Simulado | Mix finalizado |
| 14 | Música | — | Simulado | Trilha sincronizada |
| 15 | Legendas | `subtitle_module.py` | **Real** | SRT com estilos |
| 16 | Identidade Visual | — | Simulado | Logo, vinheta, watermark |
| 17 | Motion Graphics | `graphics_module.py` | Simulado | Animações e títulos |
| 18 | Exportação | `render_module.py` + `export_module.py` | **Real** | Multi-formato + master |
| 19 | Controle de Qualidade (QA) | — | **Real** (regras) | Relatório de aprovação |
| 20 | Logs e Auditoria | — | **Real** | Audit trail em JSON + banco |
| 21 | Memória | — | **Real** (SQLite) | Preferências persistidas |
| 22 | Aprendizado | — | Simulado | Sugestões de melhoria |

### Modules

#### ffmpeg_utils.py — Utilitários FFmpeg

- `EXPORT_PRESETS` — dicionário com 4 presets de exportação
- `check_ffmpeg()` — busca `ffmpeg` e `ffprobe` no PATH
- `get_video_info(path)` — retorna dict com duration, width, height, fps, codec, size
- `run_ffmpeg(args, log_fn, timeout)` — executa FFmpeg, captura stderr em tempo real
- `build_export_args(master, output, preset, subtitle)` — monta args para exportação
- `create_concat_list(paths, output_txt)` — gera arquivo de concatenação FFmpeg

#### ingestion_module.py — Ingestão

- Formatos suportados: mp4, mov, mxf, avi, mkv, webm, m4v, ts, braw
- `ingest_uploaded_files(file_paths)` — valida existência e extensão
- `scan_and_group(folder_path)` — varre pasta local
- Retorna `project_data` com `video_files`, `files_metadata`, `total_duration_sec`

#### analysis_module.py — Análise Técnica

- `extract_features(project_assets)` — consolida metadados, computa stats agregados
- Gera `cut_suggestions` — segmentos de 30s por arquivo

#### ai_module.py — Motor de IA

- **Totalmente simulado** — retorna dados mock
- Placeholder para Whisper (transcrição), YOLO (detecção de objetos), FaceNet (reconhecimento facial)
- Transcripts mock com palavras em português e timestamps

#### org_module.py — Organização Narrativa

- Lógica real de seleção por perfil:
  - `podcast`: inclui todos os segmentos
  - `youtube`: skip 5s iniciais de cada clipe
  - `reels`: apenas primeiros 60s
  - `cinematic`: apenas segmentos >= 20s
  - `institutional`/default: todos em ordem

#### edit_module.py — EDL

- Gera Edit Decision List: `{job_id, profile, resolution, clips[], total_duration}`
- Cada clip: `{file, in, out, duration, timeline_in, timeline_out}`
- Valida arquivos existentes e durações positivas

#### subtitle_module.py — Legendas SRT

- Gera arquivos SRT reais com formato `HH:MM:SS,mmm`
- Agrupa palavras em linhas de ~7 palavras
- Fallback para legendas demo em português se não houver transcrições
- `_fmt_tc(seconds)` — conversão de float para timecode SRT

#### render_module.py — Renderização

- Estratégias:
  - **Arquivo único:** fast-path com copy codec, normalização de áudio, legenda opcional
  - **Múltiplos arquivos:** concat demuxer (perde codec copy, recodifica)
- Filtros: `loudnorm` (I=-16, TP=-1.5, LRA=11), libx264 CRF 18, AAC 192k
- `-movflags +faststart` para streaming
- Saída: `master.mp4`

#### export_module.py — Exportação Multi-Formato

- Itera sobre presets, chama `build_export_args()` + `run_ffmpeg()`
- Exportação sequencial (comentário mostra opção paralela com ThreadPoolExecutor)
- Suporte opcional a burn-in de legendas

---

## Frontend

### index.html

- Idioma: português
- Glass-morphism com sidebar fixa de 340px
- Estrutura: Config Panel → Pipeline Panel → Preview Panel
- Dependências externas: Font Awesome 6.4, Google Fonts (Inter, Outfit)

### style.css (878 linhas)

- Design system com variáveis CSS: `--bg-dark: #0f111a`, `--primary: #6d28d9` (roxo), `--accent: #06b6d4` (ciano)
- Painéis com `backdrop-filter: blur(12px)`
- Animações: upload pulse, pipeline nodes flow, log slide-in, timeline tracks
- Scrollbar customizada

### app.js (489 linhas)

- Estado: `selectedFiles`, `sessionId`, `currentJobId`, `pollInterval`, `lastLogCount`
- Upload via XHR com progresso em tempo real
- Polling a cada 1s em `/api/status`
- Validação de upload: extensão de vídeo + MIME type
- UI states: idle / processing / complete

---

## Comandos Úteis

```bash
# Iniciar servidor (da raiz do projeto)
cd backend; uvicorn app:app --reload --port 8000

# Ou da raiz (ajustando o path):
uvicorn backend.app:app --reload --port 8000 --app-dir backend

# Dependências necessárias
pip install fastapi uvicorn pydantic python-multipart sqlalchemy
```

---

## Histórico de Sessões

- **Arquivo:** `HISTORY.md` na raiz do projeto
- **Convenção:** Toda sessão de trabalho deve ser registrada no `HISTORY.md` com:
  - Número da sessão e data
  - Tarefa executada
  - Alterações realizadas (arquivos modificados/criados)
  - Estado do projeto ao final da sessão
  - Pendências descobertas
- **Regra:** Sempre atualizar `HISTORY.md` ao final de cada tarefa significativa

---

## Notas de Desenvolvimento

- [x] Adicionar banco de dados (SQLite/PostgreSQL) para persistência
- [ ] Implementar autenticação JWT
- [ ] Substituir módulos simulados por integrações reais (Whisper, YOLO, etc.)
- [ ] Adicionar testes (pytest)
- [ ] Adicionar Dockerfile + docker-compose
- [ ] Suporte a jobs paralelos
- [ ] Adicionar `requirements.txt` ou `pyproject.toml`
- [ ] Configurar lint (ruff) e type checking (mypy)
- [ ] CI/CD com GitHub Actions
- [ ] Internacionalização (i18n) para suportar outros idiomas
