# CortexEdit — Histórico de Desenvolvimento

Registro de todas as sessões de trabalho e alterações realizadas no projeto.

---

## Sessão 0 — Estado Inicial (antes de 2026-07-26)

### O que foi implementado

**Backend:**
- Servidor FastAPI completo (`app.py`) com 10+ endpoints REST
- Sistema multi-agente SIPA com 22 agentes especializados + Master Orchestrator
- Memória compartilhada thread-safe (`SharedContext`)
- Pipeline de 5 estágios: Ingestão → Análise → AI Engine → Edição → Render & Export
- Módulos funcionais: ingestion, analysis, editing, subtitles, render, export, ffmpeg_utils, whisper
- Agentes com definições JSON individuais (22 arquivos em `agents/definitions/`)

**Frontend:**
- SPA completa com design glass-morphism
- Upload com progresso em tempo real (XHR)
- Visualização do pipeline em tempo real (polling a cada 1s)
- Preview de vídeo integrado
- Cut Editor para extração de clipes

**Funcionalidades implementadas (reais):**
- Ingestão e validação de arquivos de vídeo
- Extração de metadados via ffprobe
- Organização de projeto por câmeras/datas/cenas (heurística)
- Detecção de qualidade técnica (blur, shake, áudio)
- Curadoria por perfil (podcast, youtube, reels, cinematic, institutional)
- Narrativa em 3 atos
- Roteirização com ganchos e momentos de impacto
- Geração de EDL com jump/L/J cuts, speed ramp, zoom
- Legendas SRT reais com timestamps
- Transcrição via faster-whisper (com fallback mock)
- Renderização FFmpeg (single-file fast-path + multi-file concat)
- Exportação multi-formato (4 presets: 16:9 4K, 9:16 1080p, 1:1 Square, Audio Only)
- Burn-in de legendas com estilos
- Extração de clipes (single e batch)
- Controle de qualidade baseado em regras
- Relatórios de auditoria em JSON
- Memory agent (preferências em RAM)

**Simulado (mock):**
- Visão computacional (detecção de pessoas/objetos/rostos)
- Análise semântica (tópicos, palavras-chave, resumo)
- Colorização (color grading)
- Áudio (mix)
- Música (seleção de trilha)
- Identidade visual (logo, vinheta, watermark)
- Motion graphics (animações, títulos)
- Aprendizado (sugestões de melhoria)

**Artefatos de execução anteriores:**
- 16 pastas de jobs em `exports/` com vídeos processados
- 2 relatórios de auditoria completos (jobs `3072f164` e `a718556c`)
- 3 sessões de upload em `uploads/`
- 3 scripts de teste na raiz: `test_agent.py`, `test_cut.py`, `test_whisper.py`

---

## Sessão 1 — 2026-07-27

### Tarefa
- Revisão completa do projeto
- Criação do registro de histórico

### Alterações realizadas
- Criado este arquivo `HISTORY.md` para registro de sessões
- Revisada a estrutura completa do projeto
- Mapeado estado atual: o que funciona, o que é simulado, o que falta

### Estado do projeto
- Backend funcional e servível via `uvicorn backend.app:app --reload --port 8000`
- Frontend completo e funcional
- Pipeline de 22 agentes operacional (9 reais, 13 simulados)
- 16 jobs anteriores documentados em `exports/`
- Sem controle de versão (sem .git)
- Sem testes automatizados
- Sem banco de dados
- Sem autenticação

### Pendências conhecidas
- [x] Adicionar banco de dados (SQLite/PostgreSQL) para persistência ✅ Sessão 2
- [ ] Implementar autenticação JWT
- [ ] Substituir módulos simulados por integrações reais (Whisper, YOLO, etc.)
- [ ] Adicionar testes automatizados (pytest)
- [ ] Adicionar Dockerfile + docker-compose
- [ ] Suporte a jobs paralelos
- [ ] Adicionar `requirements.txt` na raiz do projeto
- [ ] Configurar lint (ruff) e type checking (mypy)
- [ ] CI/CD com GitHub Actions
- [ ] Internacionalização (i18n)
- [ ] Inicializar repositório Git

---

## Sessão 2 — 2026-07-27

### Tarefa
- Implementação do banco de dados SQLite com SQLAlchemy
- Persistência de jobs, logs, erros, resultados de agentes, sessões de upload e preferências

### Alterações realizadas

**Arquivos criados:**
- `backend/database.py` — Engine SQLite, session factory, inicialização do banco (WAL mode, foreign keys)
- `backend/models.py` — 6 modelos SQLAlchemy: Job, AgentResult, JobLog, JobError, UploadSession, UserPreference
- `backend/crud.py` — Operações CRUD completas para todas as tabelas

**Arquivos modificados:**
- `backend/pipeline_orchestrator.py` — Integração com DB: criação de job no início, atualização ao finalizar, persistência de logs e erros
- `backend/agents/master_orchestrator.py` — Salva resultado de cada agente no banco após execução; DB session gerenciada com try/finally
- `backend/agents/memory_agent.py` — Preferências agora persistem no SQLite (antes: apenas RAM)
- `backend/agents/logs_audit_agent.py` — Simplificado, sem dependência de DB (o MOA já persiste os dados)
- `backend/app.py` — Inicializa DB no startup; salva sessões de upload; 4 novos endpoints de consulta
- `backend/requirements.txt` — Adicionado `sqlalchemy>=2.0.0`

**Novos endpoints:**
- `GET /api/jobs` — Lista histórico de jobs (com paginação)
- `GET /api/jobs/{job_id}` — Detalhes de um job
- `GET /api/jobs/{job_id}/logs` — Logs de um job
- `GET /api/jobs/{job_id}/agents` — Resultados dos 22 agentes

**Schema do banco (6 tabelas):**
```
jobs              → dados principais do job (id, status, profile, stages, timestamps)
agent_results     → resultado de cada agente por job (data JSON, timing, confiança)
job_logs          → logs granulares por job
job_errors        → erros registrados por job
upload_sessions   → sessões de upload com metadados dos arquivos
user_preferences  → preferências de perfil (Memory Agent)
```

### Estado do projeto
- Banco SQLite criado automaticamente na inicialização (`cortexedit.db`)
- Todos os dados do pipeline persistem entre reinícios do servidor
- Compatibilidade total com a API existente (nenhum endpoint quebrado)
- Agentes de auditoria e memória agora usam o banco

### Pendências conhecidas
- [x] Adicionar banco de dados (SQLite/PostgreSQL) para persistência ✅
- [ ] Implementar autenticação JWT
- [ ] Substituir módulos simulados por integrações reais (Whisper, YOLO, etc.)
- [ ] Adicionar testes automatizados (pytest)
- [ ] Adicionar Dockerfile + docker-compose
- [ ] Suporte a jobs paralelos
- [ ] Adicionar `requirements.txt` na raiz do projeto
- [ ] Configurar lint (ruff) e type checking (mypy)
- [ ] CI/CD com GitHub Actions
- [ ] Internacionalização (i18n)
- [ ] Inicializar repositório Git
- [ ] Adicionar frontend de histórico de jobs (visualização)
- [ ] Migrar dados existentes de exports/ para o banco

---
