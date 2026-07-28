/**
 * CortexEdit – Frontend Application
 * Gerencia upload de arquivos reais, polling de status, timeline
 * e renderização dos deliverables para download.
 */

document.addEventListener('DOMContentLoaded', () => {

    // ── DOM References ────────────────────────────────────────────────────
    const btnProduce         = document.getElementById('btnProduce');
    const btnCancel          = document.getElementById('btnCancel');
    const btnBrowse          = document.getElementById('btnBrowse');
    const fileInput          = document.getElementById('fileInput');
    const uploadZone         = document.getElementById('uploadZone');
    const uploadZoneContent  = document.getElementById('uploadZoneContent');
    const fileList           = document.getElementById('fileList');
    const terminalLog        = document.getElementById('terminalLog');
    const nodes              = document.querySelectorAll('.node');
    const connectors         = document.querySelectorAll('.connector');
    const subtitleOverlay    = document.getElementById('subtitleOverlay');
    const videoClips         = document.getElementById('videoClips');
    const audioClips         = document.getElementById('audioClips');
    const subClips           = document.getElementById('subClips');
    const stageProgressFill  = document.getElementById('stageProgressFill');
    const stageProgressLabel = document.getElementById('stageProgressLabel');
    const uploadProgressWrap = document.getElementById('uploadProgressWrap');
    const uploadProgressFill = document.getElementById('uploadProgressFill');
    const uploadProgressLabel= document.getElementById('uploadProgressLabel');
    const uploadProgressPct  = document.getElementById('uploadProgressPct');
    const outputsSection     = document.getElementById('outputsSection');
    const outputCards        = document.getElementById('outputCards');
    const outputsBadge       = document.getElementById('outputsBadge');
    const videoPlayer        = document.getElementById('videoPlayer');
    const mockVideoPlaceholder= document.getElementById('mockVideoPlaceholder');
    const chipsContainer     = document.getElementById('chipsContainer');
    const ffmpegStatus       = document.getElementById('ffmpegStatus');
    const profileSelector    = document.getElementById('profileSelector');

    // ── State ─────────────────────────────────────────────────────────────
    let selectedFiles   = [];
    let sessionId       = null;
    let currentJobId    = null;
    let pollInterval    = null;
    let lastLogCount    = 0;
    let subtitleTimer   = null;

    // ── On Load: check FFmpeg availability ────────────────────────────────
    checkFFmpegStatus();

    // ── Chip toggle ───────────────────────────────────────────────────────
    chipsContainer.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => chip.classList.toggle('active'));
    });

    // ── File Selection ────────────────────────────────────────────────────
    btnBrowse.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => handleFilesSelected(Array.from(e.target.files)));

    // Drag and Drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('drag-over');
    });
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        const dropped = Array.from(e.dataTransfer.files).filter(f => isVideoFile(f));
        handleFilesSelected(dropped);
    });

    function isVideoFile(file) {
        const exts = ['mp4', 'mov', 'mkv', 'avi', 'mxf', 'webm', 'm4v', 'ts', 'braw'];
        const ext = file.name.split('.').pop().toLowerCase();
        return file.type.startsWith('video/') || exts.includes(ext);
    }

    function handleFilesSelected(files) {
        if (!files.length) return;
        selectedFiles = files;
        sessionId = null; // Reset session – needs re-upload
        renderFileList(files);
    }

    function renderFileList(files) {
        if (!files.length) {
            fileList.style.display = 'none';
            return;
        }
        fileList.style.display = 'flex';
        fileList.innerHTML = '';
        files.forEach((f, i) => {
            const size = (f.size / (1024 * 1024)).toFixed(1);
            const item = document.createElement('div');
            item.className = 'file-item';
            item.innerHTML = `
                <i class="fa-solid fa-file-video"></i>
                <div class="file-info">
                    <span class="file-name">${f.name}</span>
                    <span class="file-size">${size} MB</span>
                </div>
                <button class="file-remove" data-index="${i}" title="Remove">
                    <i class="fa-solid fa-xmark"></i>
                </button>
            `;
            fileList.appendChild(item);
        });
        // Remove individual file
        fileList.querySelectorAll('.file-remove').forEach(btn => {
            btn.addEventListener('click', () => {
                const idx = parseInt(btn.dataset.index);
                selectedFiles.splice(idx, 1);
                sessionId = null;
                renderFileList(selectedFiles);
            });
        });
    }

    // ── Upload Files ──────────────────────────────────────────────────────
    async function uploadFiles() {
        if (!selectedFiles.length) {
            logMessage('Nenhum arquivo selecionado. Arraste vídeos ou clique em Browse.', 'error');
            return null;
        }

        // Show upload progress
        uploadProgressWrap.style.display = 'block';
        uploadProgressLabel.textContent = `Enviando ${selectedFiles.length} arquivo(s)...`;
        setUploadProgress(0);

        const formData = new FormData();
        selectedFiles.forEach(f => formData.append('files', f));

        try {
            // Use XHR for real upload progress
            const result = await new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/api/upload_files');

                xhr.upload.onprogress = (e) => {
                    if (e.lengthComputable) {
                        const pct = Math.round((e.loaded / e.total) * 100);
                        setUploadProgress(pct);
                        uploadProgressLabel.textContent = `Enviando... ${pct}%`;
                    }
                };

                xhr.onload = () => {
                    if (xhr.status === 200) {
                        resolve(JSON.parse(xhr.responseText));
                    } else {
                        reject(new Error(`Upload falhou: ${xhr.status}`));
                    }
                };
                xhr.onerror = () => reject(new Error('Erro de rede no upload.'));
                xhr.send(formData);
            });

            setUploadProgress(100);
            uploadProgressLabel.textContent = `✓ ${result.files.length} arquivo(s) enviado(s)`;
            logMessage(`Upload completo: ${result.files.length} arquivo(s) recebidos pelo servidor.`, 'success');
            return result.session_id;

        } catch (err) {
            logMessage(`Erro no upload: ${err.message}`, 'error');
            uploadProgressWrap.style.display = 'none';
            return null;
        }
    }

    function setUploadProgress(pct) {
        uploadProgressFill.style.width = `${pct}%`;
        uploadProgressPct.textContent = `${pct}%`;
    }

    // ── Start Production ──────────────────────────────────────────────────
    btnProduce.addEventListener('click', startProduction);

    async function startProduction() {
        resetUI();

        // 1. Upload se necessário
        if (!sessionId) {
            sessionId = await uploadFiles();
            if (!sessionId) return;
        }

        // 2. Coletar configuração
        const selectedFormats = Array.from(chipsContainer.querySelectorAll('.chip.active'))
            .map(c => c.dataset.format);

        if (!selectedFormats.length) {
            logMessage('Selecione pelo menos um formato de export.', 'error');
            return;
        }

        const profile = {
            name: profileSelector.value,
            style: "dynamic",
            exports: selectedFormats,
        };

        // 3. Iniciar job
        setBtnState('processing');
        btnCancel.style.display = 'inline-flex';

        try {
            const res = await fetch('/api/start_job', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    upload_session_id: sessionId,
                    profile,
                }),
            });
            const data = await res.json();
            if (!res.ok) {
                logMessage(`Erro: ${data.error || 'Falha ao iniciar job.'}`, 'error');
                setBtnState('idle');
                btnCancel.style.display = 'none';
                return;
            }

            logMessage(`Pipeline iniciado. FFmpeg: ${data.ffmpeg_available ? '✓ disponível' : '⚠ simulação'}`, 'info');
            pollInterval = setInterval(pollStatus, 1000);

        } catch (err) {
            logMessage(`Erro de conexão: ${err.message}`, 'error');
            setBtnState('idle');
            btnCancel.style.display = 'none';
        }
    }

    // ── Cancel ────────────────────────────────────────────────────────────
    btnCancel.addEventListener('click', async () => {
        try {
            await fetch('/api/cancel', { method: 'DELETE' });
            logMessage('Cancelamento solicitado.', 'warning');
        } catch (e) { /* ignore */ }
    });

    // ── Status Polling ────────────────────────────────────────────────────
    async function pollStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();

            currentJobId = data.job_id;

            // New logs
            if (data.logs && data.logs.length > lastLogCount) {
                for (let i = lastLogCount; i < data.logs.length; i++) {
                    const l = data.logs[i];
                    const type = l.level === 'error' ? 'error'
                        : (l.message.includes('✓') || l.message.includes('success') ? 'success'
                        : (l.message.includes('⚠') || l.message.includes('warning') ? 'warning' : 'info'));
                    logMessage(l.message, type);
                }
                lastLogCount = data.logs.length;
            }

            // Pipeline nodes
            if (data.current_stage >= 0) {
                updateNodesUpTo(data.current_stage);
                const pct = data.stage_percent || 0;
                setStageProgress(data.current_stage, data.current_stage_name, pct);
            }

            // Timeline (after editing stage = 3)
            if (data.current_stage >= 3 || (!data.is_running && data.logs?.length > 0)) {
                generateTimelineMock();
            }

            // Finished
            if (!data.is_running && data.logs?.length > 0) {
                clearInterval(pollInterval);
                updateNodesUpTo(5); // all done
                stageProgressFill.style.width = '100%';
                stageProgressLabel.textContent = 'Production Complete';

                setBtnState('complete');
                btnCancel.style.display = 'none';
                uploadProgressWrap.style.display = 'none';

                // Render output files
                if (data.output_files?.length > 0) {
                    renderOutputs(data.output_files);

                    // Preview master video
                    const masterFile = data.output_files.find(f => f.format === 'master');
                    if (masterFile) {
                        showVideoPreview(masterFile.job_id, masterFile.filename);
                    }
                }

                // Subtitle animation fallback
                startSubtitleAnimation();

                setTimeout(() => setBtnState('idle'), 8000);
            }

        } catch (err) {
            console.error('Polling error:', err);
        }
    }

    // ── Stage Progress ────────────────────────────────────────────────────
    function setStageProgress(stageIdx, stageName, percent) {
        // Each stage is 20% of the total bar
        const overall = (stageIdx * 20) + (percent * 0.2);
        stageProgressFill.style.width = `${Math.min(overall, 100)}%`;
        stageProgressLabel.textContent = stageName || `Stage ${stageIdx + 1}`;
    }

    // ── Pipeline Nodes ────────────────────────────────────────────────────
    function updateNodesUpTo(currentStage) {
        nodes.forEach((n, i) => {
            if (i < currentStage) {
                n.className = 'node completed';
                if (i < connectors.length) connectors[i].classList.add('active');
            } else if (i === currentStage) {
                n.className = 'node active';
            } else {
                n.className = 'node';
            }
        });
    }

    // ── Timeline Mock ─────────────────────────────────────────────────────
    function generateTimelineMock() {
        if (videoClips.innerHTML !== '') return;
        const addClip = (container, cls, start, width) => {
            const el = document.createElement('div');
            el.className = `clip ${cls}`;
            el.style.left = `${start}%`;
            el.style.width = `${width}%`;
            container.appendChild(el);
        };
        addClip(videoClips, 'clip-video', 5, 20);
        addClip(videoClips, 'clip-video', 26, 30);
        addClip(videoClips, 'clip-video', 57, 15);
        addClip(audioClips, 'clip-audio', 5, 67);
        addClip(subClips,   'clip-sub',   5, 5);
        addClip(subClips,   'clip-sub',   11, 8);
    }

    // ── Output Files ──────────────────────────────────────────────────────
    function renderOutputs(files) {
        outputsSection.style.display = 'block';
        outputsBadge.textContent = `${files.length} file${files.length !== 1 ? 's' : ''}`;
        outputCards.innerHTML = '';

        const iconMap = {
            'master':    'fa-crown',
            '16:9 4K':  'fa-tv',
            '9:16 1080p': 'fa-mobile-screen',
            '1:1 Square': 'fa-square',
            'Audio Only': 'fa-music',
            'subtitle':  'fa-closed-captioning',
        };

        files.forEach(file => {
            const icon = iconMap[file.format] || 'fa-file-video';
            const sizeStr = file.size_mb >= 1
                ? `${file.size_mb.toFixed(1)} MB`
                : `${(file.size_mb * 1024).toFixed(0)} KB`;

            const card = document.createElement('div');
            card.className = 'output-card';
            card.innerHTML = `
                <div class="output-card-icon"><i class="fa-solid ${icon}"></i></div>
                <div class="output-card-info">
                    <span class="output-card-label">${file.label}</span>
                    <span class="output-card-meta">${file.filename} · ${sizeStr}</span>
                </div>
                <a class="output-download-btn"
                   href="/api/download/${file.job_id}/${file.filename}"
                   download="${file.filename}"
                   title="Download">
                    <i class="fa-solid fa-download"></i>
                </a>
            `;
            outputCards.appendChild(card);
        });
    }

    // ── Video Preview ─────────────────────────────────────────────────────
    function showVideoPreview(jobId, filename) {
        const src = `/api/download/${jobId}/${filename}`;
        videoPlayer.src = src;
        videoPlayer.style.display = 'block';
        mockVideoPlaceholder.style.display = 'none';
    }

    // ── Subtitle Animation ────────────────────────────────────────────────
    function startSubtitleAnimation() {
        const subs = [
            "Produção <span class='highlight'>CortexEdit</span>",
            "Editado por <span class='highlight'>Inteligência Artificial</span>",
            "Export <span class='highlight'>multi-formato</span> completo!",
        ];
        let idx = 0;
        subtitleOverlay.innerHTML = subs[0];
        if (subtitleTimer) clearInterval(subtitleTimer);
        subtitleTimer = setInterval(() => {
            idx = (idx + 1) % subs.length;
            subtitleOverlay.innerHTML = subs[idx];
        }, 2500);
    }

    // ── FFmpeg Status ─────────────────────────────────────────────────────
    async function checkFFmpegStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            updateFFmpegBadge(data.ffmpeg_available);
        } catch {
            updateFFmpegBadge(null);
        }
    }

    function updateFFmpegBadge(available) {
        if (available === true) {
            ffmpegStatus.className = 'ffmpeg-status ok';
            ffmpegStatus.innerHTML = '<i class="fa-solid fa-circle-check"></i><span>FFmpeg Ready</span>';
        } else if (available === false) {
            ffmpegStatus.className = 'ffmpeg-status warn';
            ffmpegStatus.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i><span>Simulation Mode</span>';
        } else {
            ffmpegStatus.className = 'ffmpeg-status';
            ffmpegStatus.innerHTML = '<i class="fa-solid fa-circle-question"></i><span>Checking...</span>';
        }
    }

    // ── Terminal Log ──────────────────────────────────────────────────────
    function logMessage(msg, type = 'info') {
        const p = document.createElement('p');
        p.className = `log-${type}`;
        const timeStr = new Date().toLocaleTimeString();
        p.innerHTML = `<span class="log-time">[${timeStr}]</span> ${escapeHtml(msg)}`;
        terminalLog.appendChild(p);
        terminalLog.scrollTop = terminalLog.scrollHeight;
        // Keep last 200 lines
        while (terminalLog.children.length > 200) {
            terminalLog.removeChild(terminalLog.firstChild);
        }
    }

    function escapeHtml(str) {
        return str.replace(/&/g, '&amp;')
                  .replace(/</g, '&lt;')
                  .replace(/>/g, '&gt;');
    }

    // ── UI State ──────────────────────────────────────────────────────────
    function resetUI() {
        if (pollInterval) clearInterval(pollInterval);
        if (subtitleTimer) clearInterval(subtitleTimer);
        lastLogCount = 0;
        currentJobId = null;
        nodes.forEach(n => n.className = 'node');
        connectors.forEach(c => c.classList.remove('active'));
        terminalLog.innerHTML = '';
        subtitleOverlay.innerHTML = '';
        videoClips.innerHTML = '';
        audioClips.innerHTML = '';
        subClips.innerHTML = '';
        stageProgressFill.style.width = '0%';
        stageProgressLabel.textContent = 'Starting...';
        outputsSection.style.display = 'none';
        outputCards.innerHTML = '';
        videoPlayer.style.display = 'none';
        videoPlayer.src = '';
        mockVideoPlaceholder.style.display = 'flex';
    }

    function setBtnState(state) {
        const states = {
            idle:       { html: '<i class="fa-solid fa-bolt"></i> Start AI Production', disabled: false },
            processing: { html: '<i class="fa-solid fa-circle-notch fa-spin"></i> Processing...', disabled: true },
            complete:   { html: '<i class="fa-solid fa-check"></i> Production Complete!', disabled: false },
        };
        const s = states[state] || states.idle;
        btnProduce.innerHTML = s.html;
        btnProduce.disabled = s.disabled;
    }

    // ══════════════════════════════════════════════════════════════════════
    //  TRANSCRIPTION MODULE
    // ══════════════════════════════════════════════════════════════════════

    const transcribeView        = document.getElementById('transcribeView');
    const navStudio             = document.getElementById('navStudio');
    const btnStartTranscribe    = document.getElementById('btnStartTranscribe');
    const btnBackToStudio       = document.getElementById('btnBackToStudio');
    const dashboardGrid         = document.querySelector('.dashboard-grid');
    const studioTabs            = document.getElementById('studioTabs');
    const transcribeUploadZone  = document.getElementById('transcribeUploadZone');
    const transcribeFileInput   = document.getElementById('transcribeFileInput');
    const transcribeVideoPlayer = document.getElementById('transcribeVideoPlayer');
    const transcribeSubtitle    = document.getElementById('transcribeSubtitleOverlay');
    const transcribeControls    = document.getElementById('transcribeControls');
    const btnTranscribe         = document.getElementById('btnTranscribe');
    const transcribeTextBody    = document.getElementById('transcribeTextBody');
    const transcribeLangBadge   = document.getElementById('transcribeLangBadge');
    const transcribeToolbar     = document.getElementById('transcribeToolbar');
    const btnSaveSrt            = document.getElementById('btnSaveSrt');
    const btnBurnSubs           = document.getElementById('btnBurnSubs');
    const btnNewTranscribe      = document.getElementById('btnNewTranscribe');
    const btnNewVideo           = document.getElementById('btnNewVideo');

    // Progress panel elements
    const tpProgress            = document.getElementById('transcribeProgress');
    const tpIcon                = document.getElementById('tpIcon');
    const tpRingFill            = document.getElementById('tpRingFill');
    const tpStage               = document.getElementById('tpStage');
    const tpEta                 = document.getElementById('tpEta');
    const tpPct                 = document.getElementById('tpPct');
    const tpBarFill             = document.getElementById('tpBarFill');

    let transcribeSelectedFile  = null;
    let transcribeSrtEntries    = [];
    let transcribeActiveIdx     = -1;
    let transcribePollInterval  = null;
    let transcribeStartTime     = 0;
    let transcribeCurrentJobId  = null;
    let transcribeIsDirty       = false;

    // Ring circumference (2 * PI * r = 2 * PI * 20 ≈ 125.66)
    const RING_CIRCUMFERENCE = 125.66;

    // ── Studio Tabs ────────────────────────────────────────────────────
    studioTabs.querySelectorAll('.studio-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.dataset.tab;

            // Update tab active state
            studioTabs.querySelectorAll('.studio-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Show/hide tab content
            document.querySelectorAll('.tab-content').forEach(tc => {
                tc.classList.remove('active');
                tc.style.display = 'none';
            });
            const target = document.getElementById('tab' + tabId.charAt(0).toUpperCase() + tabId.slice(1));
            if (target) {
                target.classList.add('active');
                target.style.display = '';
            }

            // Switch right panel
            if (tabId === 'transcribe') {
                dashboardGrid.classList.add('transcribe-mode');
                transcribeView.style.display = 'flex';
            } else {
                dashboardGrid.classList.remove('transcribe-mode');
                transcribeView.style.display = 'none';
            }
        });
    });

    // ── Navigation: Transcrição ↔ Studio ───────────────────────────────
    btnStartTranscribe.addEventListener('click', () => {
        dashboardGrid.classList.add('transcribe-mode');
        transcribeView.style.display = 'flex';
    });

    btnBackToStudio.addEventListener('click', () => {
        dashboardGrid.classList.remove('transcribe-mode');
        transcribeView.style.display = 'none';
        // Switch tab back to production
        const prodTab = studioTabs.querySelector('[data-tab="production"]');
        if (prodTab) prodTab.click();
    });

    // ── Upload Zone Click ──────────────────────────────────────────────
    transcribeUploadZone.addEventListener('click', () => transcribeFileInput.click());
    transcribeUploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        transcribeUploadZone.style.borderColor = 'var(--accent)';
    });
    transcribeUploadZone.addEventListener('dragleave', () => {
        transcribeUploadZone.style.borderColor = '';
    });
    transcribeUploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        transcribeUploadZone.style.borderColor = '';
        const files = Array.from(e.dataTransfer.files).filter(f => isVideoFile(f));
        if (files.length) handleTranscribeFile(files[0]);
    });
    transcribeFileInput.addEventListener('change', (e) => {
        if (e.target.files.length) handleTranscribeFile(e.target.files[0]);
    });

    function handleTranscribeFile(file) {
        transcribeSelectedFile = file;
        const url = URL.createObjectURL(file);
        transcribeVideoPlayer.src = url;
        transcribeVideoPlayer.style.display = 'block';
        transcribeUploadZone.style.display = 'none';
        transcribeControls.style.display = 'flex';
        transcribeSrtEntries = [];
        transcribeActiveIdx = -1;
        transcribeIsDirty = false;
        transcribeCurrentJobId = null;
        transcribeSubtitle.innerHTML = '';
        transcribeTextBody.innerHTML = '<p class="transcribe-empty-msg">Clique em "Transcrever Vídeo" para iniciar.</p>';
        transcribeLangBadge.style.display = 'none';
        transcribeToolbar.style.display = 'none';
        btnSaveSrt.disabled = true;
        btnSaveSrt.classList.remove('has-changes');
    }

    // ── Transcribe Button ──────────────────────────────────────────────
    btnTranscribe.addEventListener('click', startTranscription);

    async function startTranscription() {
        if (!transcribeSelectedFile) return;

        btnTranscribe.disabled = true;
        btnTranscribe.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Transcrevendo...';
        showTranscribeProgress(0, 'init', 'Enviando vídeo...');
        transcribeStartTime = Date.now();

        const formData = new FormData();
        formData.append('file', transcribeSelectedFile);

        try {
            const res = await fetch('/api/transcribe', {
                method: 'POST',
                body: formData,
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: 'Falha ao iniciar transcrição.' }));
                throw new Error(err.detail || 'Falha ao iniciar transcrição.');
            }

            const { job_id } = await res.json();
            showTranscribeProgress(5, 'init', 'Transcrição iniciada...');
            startTranscribePoll(job_id);

        } catch (err) {
            hideTranscribeProgress();
            showTranscribeError(err.message);
            btnTranscribe.disabled = false;
            btnTranscribe.innerHTML = '<i class="fa-solid fa-closed-captioning"></i> Transcrever Vídeo';
        }
    }

    // ── Progress Polling ────────────────────────────────────────────────
    function startTranscribePoll(jobId) {
        if (transcribePollInterval) clearInterval(transcribePollInterval);
        transcribePollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/transcribe/progress/${jobId}`);
                if (!res.ok) return;
                const data = await res.json();

                updateTranscribeProgress(data.percent, data.stage, data.message);

                if (data.stage === 'done' && data.result) {
                    clearInterval(transcribePollInterval);
                    transcribePollInterval = null;
                    onTranscriptionComplete(data.result);
                } else if (data.stage === 'error') {
                    clearInterval(transcribePollInterval);
                    transcribePollInterval = null;
                    hideTranscribeProgress();
                    showTranscribeError(data.message || 'Erro desconhecido.');
                    btnTranscribe.disabled = false;
                    btnTranscribe.innerHTML = '<i class="fa-solid fa-closed-captioning"></i> Transcrever Vídeo';
                }
            } catch {
                // Network hiccup — keep polling
            }
        }, 400);
    }

    // ── Progress Display ────────────────────────────────────────────────
    const STAGE_ICONS = {
        init:            'fa-solid fa-circle-notch fa-spin',
        audio_extract:   'fa-solid fa-headphones',
        transcribing:    'fa-solid fa-closed-captioning fa-spin',
        transcribing_done: 'fa-solid fa-closed-captioning',
        srt:             'fa-solid fa-file-lines fa-spin',
        done:            'fa-solid fa-circle-check',
        error:           'fa-solid fa-circle-exclamation',
    };

    const STAGE_CLASSES = {
        init:            '',
        audio_extract:   'stage-audio',
        transcribing:    'stage-transcribe',
        transcribing_done: 'stage-transcribe',
        srt:             'stage-srt',
        done:            'stage-done',
        error:           'stage-error',
    };

    function showTranscribeProgress(pct, stage, message) {
        tpProgress.style.display = 'flex';
        updateTranscribeProgress(pct, stage, message);
    }

    function updateTranscribeProgress(pct, stage, message) {
        const pctVal = Math.max(0, Math.min(100, pct));

        // Percentage text
        tpPct.textContent = `${pctVal}%`;

        // Progress bar
        tpBarFill.style.width = `${pctVal}%`;

        // SVG ring
        const offset = RING_CIRCUMFERENCE - (pctVal / 100) * RING_CIRCUMFERENCE;
        tpRingFill.style.strokeDashoffset = offset;

        // Stage icon
        const iconClass = STAGE_ICONS[stage] || 'fa-solid fa-circle-notch fa-spin';
        tpIcon.className = `tp-icon ${iconClass}`;

        // Stage message
        tpStage.textContent = message || 'Processando...';

        // Stage color class
        const stageClass = STAGE_CLASSES[stage] || '';
        [tpIcon, tpRingFill, tpPct, tpBarFill].forEach(el => {
            el.classList.remove('stage-audio', 'stage-transcribe', 'stage-srt', 'stage-done', 'stage-error');
            if (stageClass) el.classList.add(stageClass);
        });

        // ETA calculation
        if (pctVal > 2 && transcribeStartTime > 0) {
            const elapsed = (Date.now() - transcribeStartTime) / 1000;
            const rate = pctVal / elapsed;
            const remaining = (100 - pctVal) / rate;
            tpEta.textContent = `~${formatEta(remaining)} restante`;
        } else {
            tpEta.textContent = '';
        }
    }

    function hideTranscribeProgress() {
        tpProgress.style.display = 'none';
        tpBarFill.style.width = '0%';
        tpRingFill.style.strokeDashoffset = RING_CIRCUMFERENCE;
        tpPct.textContent = '0%';
        tpStage.textContent = 'Preparando...';
        tpEta.textContent = '';
    }

    function formatEta(seconds) {
        seconds = Math.max(0, Math.round(seconds));
        if (seconds < 60) return `${seconds}s`;
        const m = Math.floor(seconds / 60);
        const s = seconds % 60;
        return `${m}m ${s}s`;
    }

    function showTranscribeError(msg) {
        showTranscribeProgress(100, 'error', msg);
        setTimeout(hideTranscribeProgress, 4000);
    }

    // ── On Transcription Complete ───────────────────────────────────────
    function onTranscriptionComplete(result) {
        updateTranscribeProgress(100, 'done', 'Concluído!');
        transcribeCurrentJobId = result.job_id;

        setTimeout(() => {
            hideTranscribeProgress();
            btnTranscribe.disabled = false;
            btnTranscribe.innerHTML = '<i class="fa-solid fa-closed-captioning"></i> Transcrever Vídeo';

            // Parse SRT
            transcribeSrtEntries = parseSrt(result.srt_content);
            transcribeLangBadge.textContent = result.language || 'pt-BR';
            transcribeLangBadge.style.display = 'inline';

            // Render editable segments
            renderTranscribeSegments(transcribeSrtEntries);

            // Load video from server
            transcribeVideoPlayer.src = result.video_url;
            transcribeVideoPlayer.load();

            // Setup subtitle sync
            setupSubtitleSync();

            // Show toolbar
            transcribeToolbar.style.display = 'flex';
            transcribeIsDirty = false;
            btnSaveSrt.disabled = true;
            btnSaveSrt.classList.remove('has-changes');
        }, 1200);
    }

    // ── SRT Parser ─────────────────────────────────────────────────────
    function parseSrt(srtContent) {
        const entries = [];
        if (!srtContent) return entries;

        const blocks = srtContent.trim().split(/\n\s*\n/);
        for (const block of blocks) {
            const lines = block.trim().split('\n');
            if (lines.length < 2) continue;

            // Find the timecode line (contains "-->")
            let timeLine = -1;
            for (let i = 0; i < lines.length; i++) {
                if (lines[i].includes('-->')) {
                    timeLine = i;
                    break;
                }
            }
            if (timeLine < 0) continue;

            const timeParts = lines[timeLine].split('-->');
            if (timeParts.length < 2) continue;

            const start = srtTimeToSeconds(timeParts[0].trim());
            const end   = srtTimeToSeconds(timeParts[1].trim());
            const text  = lines.slice(timeLine + 1).join(' ').trim();

            if (text) {
                entries.push({ start, end, text });
            }
        }
        return entries;
    }

    function srtTimeToSeconds(timeStr) {
        // Format: HH:MM:SS,mmm or HH:MM:SS.mmm
        const cleaned = timeStr.replace(',', '.');
        const parts = cleaned.split(':');
        if (parts.length !== 3) return 0;
        const h = parseInt(parts[0], 10) || 0;
        const m = parseInt(parts[1], 10) || 0;
        const s = parseFloat(parts[2]) || 0;
        return h * 3600 + m * 60 + s;
    }

    function secondsToTimecode(sec) {
        sec = Math.max(0, sec);
        const h = Math.floor(sec / 3600);
        const m = Math.floor((sec % 3600) / 60);
        const s = Math.floor(sec % 60);
        return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
    }

    // ── Render Editable Segments ────────────────────────────────────────
    function renderTranscribeSegments(entries) {
        transcribeTextBody.innerHTML = '';
        if (!entries.length) {
            transcribeTextBody.innerHTML = '<p class="transcribe-empty-msg">Nenhuma fala detectada.</p>';
            return;
        }
        entries.forEach((entry, i) => {
            const seg = document.createElement('div');
            seg.className = 'transcribe-segment';
            seg.dataset.index = i;

            const timeSpan = document.createElement('span');
            timeSpan.className = 'transcribe-seg-time';
            timeSpan.textContent = secondsToTimecode(entry.start);
            timeSpan.addEventListener('click', (e) => {
                e.stopPropagation();
                transcribeVideoPlayer.currentTime = entry.start;
                transcribeVideoPlayer.play();
            });

            const textSpan = document.createElement('span');
            textSpan.className = 'transcribe-seg-text';
            textSpan.contentEditable = 'true';
            textSpan.spellcheck = false;
            textSpan.textContent = entry.text;
            textSpan.dataset.index = i;

            textSpan.addEventListener('input', onSegmentTextEdit);
            textSpan.addEventListener('keydown', onSegmentKeyDown);
            textSpan.addEventListener('paste', onSegmentPaste);
            textSpan.addEventListener('click', (e) => e.stopPropagation());
            textSpan.addEventListener('focus', () => seg.classList.add('editing'));
            textSpan.addEventListener('blur', () => seg.classList.remove('editing'));

            const dot = document.createElement('span');
            dot.className = 'transcribe-seg-edited-dot';
            dot.style.display = 'none';

            seg.appendChild(timeSpan);
            seg.appendChild(textSpan);
            seg.appendChild(dot);
            transcribeTextBody.appendChild(seg);
        });
    }

    function onSegmentTextEdit(e) {
        const idx = parseInt(e.target.dataset.index, 10);
        if (isNaN(idx)) return;
        const newText = e.target.textContent.trim();
        if (transcribeSrtEntries[idx] && transcribeSrtEntries[idx].text !== newText) {
            transcribeSrtEntries[idx].text = newText;
            markDirty();
            const seg = e.target.closest('.transcribe-segment');
            if (seg) {
                seg.classList.add('edited');
                const dot = seg.querySelector('.transcribe-seg-edited-dot');
                if (dot) dot.style.display = '';
            }
        }
    }

    function onSegmentKeyDown(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            e.target.blur();
        }
    }

    function onSegmentPaste(e) {
        e.preventDefault();
        const text = (e.clipboardData || window.clipboardData).getData('text/plain');
        document.execCommand('insertText', false, text.replace(/\n/g, ' '));
    }

    function markDirty() {
        if (!transcribeIsDirty) {
            transcribeIsDirty = true;
            btnSaveSrt.disabled = false;
            btnSaveSrt.classList.add('has-changes');
        }
    }

    // ── SRT Generator ──────────────────────────────────────────────────
    function secondsToSrtTimecode(sec) {
        sec = Math.max(0, sec);
        const h = Math.floor(sec / 3600);
        const m = Math.floor((sec % 3600) / 60);
        const s = Math.floor(sec % 60);
        const ms = Math.round((sec - Math.floor(sec)) * 1000);
        return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')},${String(ms).padStart(3,'0')}`;
    }

    function generateSrtContent() {
        return transcribeSrtEntries.map((entry, i) => {
            return `${i + 1}\n${secondsToSrtTimecode(entry.start)} --> ${secondsToSrtTimecode(entry.end)}\n${entry.text}`;
        }).join('\n\n') + '\n';
    }

    // ── Save SRT ────────────────────────────────────────────────────────
    btnSaveSrt.addEventListener('click', saveSrtFile);

    async function saveSrtFile() {
        const srtContent = generateSrtContent();
        const blob = new Blob([srtContent], { type: 'text/plain;charset=utf-8' });
        const defaultName = (transcribeSelectedFile?.name?.replace(/\.[^.]+$/, '') || 'transcricao') + '.srt';

        if (window.showSaveFilePicker) {
            try {
                const handle = await window.showSaveFilePicker({
                    suggestedName: defaultName,
                    types: [
                        { description: 'SubRip Subtitle', accept: { 'text/plain': ['.srt'] } },
                    ],
                });
                const writable = await handle.createWritable();
                await writable.write(blob);
                await writable.close();
                showSaveToast('SRT salvo com sucesso!');
            } catch (err) {
                if (err.name !== 'AbortError') {
                    fallbackDownload(blob, defaultName);
                }
            }
        } else {
            fallbackDownload(blob, defaultName);
        }
    }

    function fallbackDownload(blob, filename) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(() => URL.revokeObjectURL(url), 1000);
        showSaveToast('SRT baixado!');
    }

    function showSaveToast(msg) {
        const existing = document.querySelector('.tp-toast');
        if (existing) existing.remove();
        const toast = document.createElement('div');
        toast.className = 'tp-toast';
        toast.innerHTML = `<i class="fa-solid fa-check-circle"></i> ${msg}`;
        document.body.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('visible'));
        setTimeout(() => {
            toast.classList.remove('visible');
            setTimeout(() => toast.remove(), 400);
        }, 2500);
    }

    // ── Burn Subtitles into Video ───────────────────────────────────────
    btnBurnSubs.addEventListener('click', burnSubtitles);

    let burnPollInterval = null;

    async function burnSubtitles() {
        if (!transcribeCurrentJobId) {
            showSaveToast('Nenhuma transcrição disponível.');
            return;
        }

        btnBurnSubs.disabled = true;
        btnBurnSubs.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Gerando...';

        const srtContent = generateSrtContent();
        const formData = new FormData();
        formData.append('job_id', transcribeCurrentJobId);
        formData.append('srt_content', srtContent);

        try {
            const res = await fetch('/api/burn-subtitles', {
                method: 'POST',
                body: formData,
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: 'Erro ao iniciar geração.' }));
                throw new Error(err.detail || 'Erro ao iniciar geração.');
            }

            const { burn_job_id } = await res.json();
            startBurnPoll(burn_job_id);

        } catch (err) {
            btnBurnSubs.disabled = false;
            btnBurnSubs.innerHTML = '<i class="fa-solid fa-film"></i> Gerar Vídeo c/ Legenda';
            showSaveToast(`Erro: ${err.message}`);
        }
    }

    function startBurnPoll(burnId) {
        if (burnPollInterval) clearInterval(burnPollInterval);
        burnPollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/burn-progress/${burnId}`);
                if (!res.ok) return;
                const data = await res.json();

                if (data.stage === 'done' && data.result) {
                    clearInterval(burnPollInterval);
                    burnPollInterval = null;
                    btnBurnSubs.disabled = false;
                    btnBurnSubs.innerHTML = '<i class="fa-solid fa-film"></i> Gerar Vídeo c/ Legenda';

                    const a = document.createElement('a');
                    a.href = data.result.video_url;
                    a.download = data.result.filename;
                    a.click();
                    showSaveToast('Vídeo com legendas pronto!');
                } else if (data.stage === 'error') {
                    clearInterval(burnPollInterval);
                    burnPollInterval = null;
                    btnBurnSubs.disabled = false;
                    btnBurnSubs.innerHTML = '<i class="fa-solid fa-film"></i> Gerar Vídeo c/ Legenda';
                    showSaveToast(`Erro: ${data.message || 'Falha ao gerar vídeo.'}`);
                } else {
                    btnBurnSubs.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ${data.message || 'Processando...'} ${data.percent || 0}%`;
                }
            } catch {
                // keep polling
            }
        }, 500);
    }

    // ── New Transcription (Reset) ──────────────────────────────────────
    btnNewTranscribe.addEventListener('click', resetTranscribeView);
    btnNewVideo.addEventListener('click', resetTranscribeView);

    function resetTranscribeView() {
        if (burnPollInterval) { clearInterval(burnPollInterval); burnPollInterval = null; }
        if (transcribePollInterval) { clearInterval(transcribePollInterval); transcribePollInterval = null; }

        transcribeSelectedFile = null;
        transcribeSrtEntries = [];
        transcribeActiveIdx = -1;
        transcribeCurrentJobId = null;
        transcribeIsDirty = false;
        transcribeStartTime = 0;

        transcribeVideoPlayer.pause();
        transcribeVideoPlayer.removeAttribute('src');
        transcribeVideoPlayer.load();
        transcribeVideoPlayer.style.display = 'none';

        transcribeUploadZone.style.display = '';
        transcribeControls.style.display = 'none';
        transcribeSubtitle.innerHTML = '';
        transcribeTextBody.innerHTML = '<p class="transcribe-empty-msg">Faça upload de um vídeo para iniciar a transcrição.</p>';
        transcribeLangBadge.style.display = 'none';
        transcribeToolbar.style.display = 'none';
        transcribeFileInput.value = '';

        hideTranscribeProgress();
        btnTranscribe.disabled = false;
        btnTranscribe.innerHTML = '<i class="fa-solid fa-closed-captioning"></i> Transcrever Vídeo';
        btnBurnSubs.disabled = false;
        btnBurnSubs.innerHTML = '<i class="fa-solid fa-film"></i> Gerar Vídeo c/ Legenda';
        btnSaveSrt.disabled = true;
        btnSaveSrt.classList.remove('has-changes');
    }

    // ── Subtitle Sync with Video ───────────────────────────────────────
    let transcribeSyncHandler = null;

    function setupSubtitleSync() {
        if (transcribeSyncHandler) {
            transcribeVideoPlayer.removeEventListener('timeupdate', transcribeSyncHandler);
        }
        transcribeSyncHandler = syncSubtitle;
        transcribeVideoPlayer.addEventListener('timeupdate', transcribeSyncHandler);
    }

    function syncSubtitle() {
        const t = transcribeVideoPlayer.currentTime;
        let foundIdx = -1;

        for (let i = 0; i < transcribeSrtEntries.length; i++) {
            const e = transcribeSrtEntries[i];
            if (t >= e.start && t <= e.end) {
                foundIdx = i;
                break;
            }
        }

        // Update overlay
        if (foundIdx >= 0) {
            transcribeSubtitle.innerHTML = escapeHtml(transcribeSrtEntries[foundIdx].text);
        } else {
            transcribeSubtitle.innerHTML = '';
        }

        // Highlight active segment in panel
        if (foundIdx !== transcribeActiveIdx) {
            const prev = transcribeTextBody.querySelector('.transcribe-segment.active');
            if (prev) prev.classList.remove('active');

            if (foundIdx >= 0) {
                const segs = transcribeTextBody.querySelectorAll('.transcribe-segment');
                if (segs[foundIdx]) {
                    segs[foundIdx].classList.add('active');
                    segs[foundIdx].scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            }
            transcribeActiveIdx = foundIdx;
        }
    }

    // ══════════════════════════════════════════════════════════════════════
    //  CUT EDITOR MODULE (via Transcrição)
    // ══════════════════════════════════════════════════════════════════════

    const cutUploadZone     = document.getElementById('cutUploadZone');
    const cutFileInput      = document.getElementById('cutFileInput');
    const btnAnalyzeCuts    = document.getElementById('btnAnalyzeCuts');
    const cutStepUpload     = document.getElementById('cutStepUpload');
    const cutStepSuggestions= document.getElementById('cutStepSuggestions');
    const cutStepProgress   = document.getElementById('cutStepProgress');
    const cutStepClips      = document.getElementById('cutStepClips');
    const cutSuggestionsList= document.getElementById('cutSuggestionsList');
    const cutSuggestionsCount= document.getElementById('cutSuggestionsCount');
    const cutSelectAll      = document.getElementById('cutSelectAll');
    const btnCutSelected    = document.getElementById('btnCutSelected');
    const btnAnalyzeAgain   = document.getElementById('btnAnalyzeAgain');
    const cutProgressIcon   = document.getElementById('cutProgressIcon');
    const cutProgressMsg    = document.getElementById('cutProgressMsg');
    const cutProgressPct    = document.getElementById('cutProgressPct');
    const cutProgressFill   = document.getElementById('cutProgressFill');
    const cutProgressDetail = document.getElementById('cutProgressDetail');
    const cutClipsList      = document.getElementById('cutClipsList');
    const cutClipsCount     = document.getElementById('cutClipsCount');
    const btnCutNewVideo    = document.getElementById('btnCutNewVideo');

    let cutSelectedFile     = null;
    let cutSessionId        = null;
    let cutSrtEntries       = [];
    let cutClipsGenerated   = [];

    // ── Upload Zone ───────────────────────────────────────────────────
    cutUploadZone.addEventListener('click', () => cutFileInput.click());
    cutUploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        cutUploadZone.classList.add('drag-over');
    });
    cutUploadZone.addEventListener('dragleave', () => cutUploadZone.classList.remove('drag-over'));
    cutUploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        cutUploadZone.classList.remove('drag-over');
        const files = Array.from(e.dataTransfer.files).filter(f => isVideoFile(f));
        if (files.length) handleCutFile(files[0]);
    });
    cutFileInput.addEventListener('change', (e) => {
        if (e.target.files.length) handleCutFile(e.target.files[0]);
    });

    function handleCutFile(file) {
        cutSelectedFile = file;
        cutSrtEntries = [];
        cutClipsGenerated = [];
        btnAnalyzeCuts.disabled = true;
        btnAnalyzeCuts.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Enviando vídeo...';
        cutUploadZone.innerHTML = `
            <i class="fa-solid fa-file-video cut-upload-icon"></i>
            <p class="cut-upload-title">${escapeHtml(file.name)}</p>
            <p class="cut-upload-sub">${(file.size / (1024 * 1024)).toFixed(1)} MB — Enviando...</p>
        `;

        // Upload to main session so batch-cut can access the file
        const formData = new FormData();
        formData.append('files', file);
        fetch('/api/upload_files', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                cutSessionId = data.session_id;
                btnAnalyzeCuts.disabled = false;
                btnAnalyzeCuts.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Analisar Transcrição';
                cutUploadZone.innerHTML = `
                    <i class="fa-solid fa-file-video cut-upload-icon"></i>
                    <p class="cut-upload-title">${escapeHtml(file.name)}</p>
                    <p class="cut-upload-sub">${(file.size / (1024 * 1024)).toFixed(1)} MB — Pronto para analisar</p>
                `;
            })
            .catch(() => {
                btnAnalyzeCuts.disabled = false;
                btnAnalyzeCuts.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Analisar Transcrição';
                showSaveToast('Erro no upload. Tente novamente.');
            });
    }

    // ── Analyze Transcription ─────────────────────────────────────────
    btnAnalyzeCuts.addEventListener('click', startCutAnalysis);

    async function startCutAnalysis() {
        if (!cutSelectedFile) return;

        btnAnalyzeCuts.disabled = true;
        btnAnalyzeCuts.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Analisando...';

        // 1. Transcribe via backend
        const formData = new FormData();
        formData.append('file', cutSelectedFile);

        try {
            const res = await fetch('/api/transcribe', { method: 'POST', body: formData });
            if (!res.ok) throw new Error('Falha ao iniciar transcrição.');
            const { job_id } = await res.json();

            // 2. Poll progress
            const result = await pollTranscribeProgress(job_id);
            if (!result) {
                btnAnalyzeCuts.disabled = false;
                btnAnalyzeCuts.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Analisar Transcrição';
                return;
            }

            // 3. Parse SRT and generate suggestions
            cutSrtEntries = parseSrt(result.srt_content);
            const suggestions = generateCutSuggestions(cutSrtEntries);

            // 4. Show suggestions
            renderCutSuggestions(suggestions);
            cutStepUpload.style.display = 'none';
            cutStepSuggestions.style.display = '';
        } catch (err) {
            showSaveToast(`Erro: ${err.message}`);
            btnAnalyzeCuts.disabled = false;
            btnAnalyzeCuts.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Analisar Transcrição';
        }
    }

    function pollTranscribeProgress(jobId) {
        return new Promise((resolve) => {
            let interval = setInterval(async () => {
                try {
                    const res = await fetch(`/api/transcribe/progress/${jobId}`);
                    if (!res.ok) return;
                    const data = await res.json();
                    if (data.stage === 'done' && data.result) {
                        clearInterval(interval);
                        resolve(data.result);
                    } else if (data.stage === 'error') {
                        clearInterval(interval);
                        showSaveToast(data.message || 'Erro na transcrição.');
                        resolve(null);
                    }
                } catch { /* keep polling */ }
            }, 500);
        });
    }

    // ── Generate Cut Suggestions from SRT ─────────────────────────────
    function generateCutSuggestions(entries) {
        if (!entries.length) return [];

        const GAP_THRESHOLD = 1.5;
        const MIN_SEGMENT_DUR = 2.0;
        const MAX_SEGMENT_DUR = 60.0;
        const PADDING = 0.3;

        // Group consecutive segments by pauses (group when gap < GAP_THRESHOLD)
        const groups = [];
        let currentGroup = [entries[0]];

        for (let i = 1; i < entries.length; i++) {
            const gap = entries[i].start - entries[i - 1].end;
            if (gap >= GAP_THRESHOLD) {
                groups.push(currentGroup);
                currentGroup = [entries[i]];
            } else {
                currentGroup.push(entries[i]);
            }
        }
        groups.push(currentGroup);

        // Build suggestions from groups, splitting oversized ones by sentences
        const suggestions = [];
        let clipIndex = 0;

        for (const group of groups) {
            const text = group.map(e => e.text).join(' ');
            const start = Math.max(0, group[0].start - PADDING);
            const end = group[group.length - 1].end + PADDING;
            const dur = end - start;

            if (dur < MIN_SEGMENT_DUR) continue;

            if (dur <= MAX_SEGMENT_DUR) {
                suggestions.push({
                    index: clipIndex++,
                    start,
                    end,
                    duration: dur,
                    text: text.trim(),
                    segCount: group.length,
                });
            } else {
                // Split by sentence boundaries (., !, ?)
                const sentences = splitIntoSentences(group);
                for (const sentence of sentences) {
                    const sDur = sentence.end - sentence.start;
                    if (sDur < MIN_SEGMENT_DUR) continue;
                    suggestions.push({
                        index: clipIndex++,
                        start: Math.max(0, sentence.start - PADDING),
                        end: sentence.end + PADDING,
                        duration: sDur,
                        text: sentence.text.trim(),
                        segCount: sentence.segCount,
                    });
                }
            }
        }

        return suggestions;
    }

    function splitIntoSentences(entries) {
        const SENTENCE_END = /[.!?;]\s*$/;
        const sentences = [];
        let currentText = [];
        let currentStart = entries[0].start;
        let currentSegCount = 0;

        for (const e of entries) {
            currentText.push(e.text);
            currentSegCount++;
            if (SENTENCE_END.test(e.text.trim())) {
                sentences.push({
                    text: currentText.join(' '),
                    start: currentStart,
                    end: e.end,
                    segCount: currentSegCount,
                });
                currentText = [];
                currentStart = e.end;
                currentSegCount = 0;
            }
        }
        // Remaining text
        if (currentText.length) {
            const last = entries[entries.length - 1];
            sentences.push({
                text: currentText.join(' '),
                start: currentStart,
                end: last.end,
                segCount: currentSegCount,
            });
        }
        return sentences;
    }

    // ── Render Suggestions ────────────────────────────────────────────
    function renderCutSuggestions(suggestions) {
        cutSuggestionsList.innerHTML = '';
        cutSuggestionsCount.textContent = `${suggestions.length} trecho${suggestions.length !== 1 ? 's' : ''}`;
        cutSelectAll.checked = true;

        for (const s of suggestions) {
            const card = document.createElement('div');
            card.className = 'cut-suggestion-card';
            card.innerHTML = `
                <label class="cut-checkbox-label">
                    <input type="checkbox" class="cut-suggest-check" data-index="${s.index}" checked>
                </label>
                <div class="cut-suggest-info">
                    <div class="cut-suggest-time">
                        <span class="cut-suggest-start">${secondsToTimecode(s.start)}</span>
                        <i class="fa-solid fa-arrow-right"></i>
                        <span class="cut-suggest-end">${secondsToTimecode(s.end)}</span>
                        <span class="cut-suggest-dur">${s.duration.toFixed(1)}s</span>
                    </div>
                    <p class="cut-suggest-text">${escapeHtml(s.text)}</p>
                </div>
            `;
            card.dataset.start = s.start;
            card.dataset.end = s.end;
            card.dataset.text = s.text;
            card.dataset.index = s.index;
            cutSuggestionsList.appendChild(card);
        }

        cutSelectAll.addEventListener('change', () => {
            cutSuggestionsList.querySelectorAll('.cut-suggest-check').forEach(cb => {
                cb.checked = cutSelectAll.checked;
            });
        });
    }

    // ── Batch Cut ─────────────────────────────────────────────────────
    btnCutSelected.addEventListener('click', batchCutClips);

    async function batchCutClips() {
        if (!cutSelectedFile || !cutSessionId) {
            showSaveToast('Envie um vídeo primeiro.');
            return;
        }

        // Collect selected clips
        const cards = cutSuggestionsList.querySelectorAll('.cut-suggestion-card');
        const selected = [];
        cards.forEach(card => {
            const cb = card.querySelector('.cut-suggest-check');
            if (cb && cb.checked) {
                selected.push({
                    start: parseFloat(card.dataset.start),
                    end: parseFloat(card.dataset.end),
                    text: card.dataset.text || '',
                });
            }
        });

        if (!selected.length) {
            showSaveToast('Selecione pelo menos um trecho.');
            return;
        }

        // Show progress
        cutStepSuggestions.style.display = 'none';
        cutStepProgress.style.display = '';
        cutProgressPct.textContent = '0%';
        cutProgressFill.style.width = '0%';
        cutProgressMsg.textContent = `Cortando ${selected.length} trecho(s)...`;
        cutProgressDetail.textContent = '';

        try {
            const res = await fetch('/api/batch-cut', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: cutSessionId,
                    filename: cutSelectedFile.name,
                    clips: selected,
                }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: 'Erro ao cortar.' }));
                throw new Error(err.detail || 'Erro ao cortar.');
            }

            const data = await res.json();

            // Poll progress
            await pollBatchCutProgress(data.job_id, selected.length);

            // Fetch final result
            const finalRes = await fetch(`/api/batch-cut/progress/${data.job_id}`);
            const finalData = await finalRes.json();

            if (finalData.clips && finalData.clips.length) {
                cutClipsGenerated = finalData.clips;
                renderCutClips(finalData.clips);
                cutStepProgress.style.display = 'none';
                cutStepClips.style.display = '';
            } else {
                throw new Error('Nenhum clip foi gerado.');
            }

        } catch (err) {
            showSaveToast(`Erro: ${err.message}`);
            cutStepProgress.style.display = 'none';
            cutStepSuggestions.style.display = '';
        }
    }

    function pollBatchCutProgress(jobId, total) {
        return new Promise((resolve) => {
            let interval = setInterval(async () => {
                try {
                    const res = await fetch(`/api/batch-cut/progress/${jobId}`);
                    if (!res.ok) return;
                    const data = await res.json();

                    const done = data.done || 0;
                    const pct = total > 0 ? Math.round((done / total) * 100) : 0;
                    cutProgressPct.textContent = `${pct}%`;
                    cutProgressFill.style.width = `${pct}%`;
                    cutProgressMsg.textContent = data.message || `Cortando... ${done}/${total}`;
                    cutProgressDetail.textContent = data.detail || '';

                    if (data.stage === 'done') {
                        clearInterval(interval);
                        resolve();
                    } else if (data.stage === 'error') {
                        clearInterval(interval);
                        throw new Error(data.message || 'Erro no corte em lote.');
                    }
                } catch (e) {
                    clearInterval(interval);
                    showSaveToast(`Erro: ${e.message}`);
                    resolve();
                }
            }, 400);
        });
    }

    function renderCutClips(clips) {
        cutClipsList.innerHTML = '';
        cutClipsCount.textContent = `${clips.length} arquivo${clips.length !== 1 ? 's' : ''}`;

        for (const clip of clips) {
            const card = document.createElement('div');
            card.className = 'cut-clip-card';
            const sizeStr = clip.size_mb >= 1
                ? `${clip.size_mb.toFixed(1)} MB`
                : `${(clip.size_mb * 1024).toFixed(0)} KB`;
            card.innerHTML = `
                <div class="cut-clip-icon"><i class="fa-solid fa-film"></i></div>
                <div class="cut-clip-info">
                    <span class="cut-clip-name">${escapeHtml(clip.filename)}</span>
                    <span class="cut-clip-meta">${clip.duration}s · ${sizeStr}</span>
                    <p class="cut-clip-text">${escapeHtml(clip.text || '')}</p>
                </div>
                <a class="cut-clip-download" href="${clip.clip_url}" download="${clip.filename}" title="Download">
                    <i class="fa-solid fa-download"></i>
                </a>
            `;
            cutClipsList.appendChild(card);
        }
    }

    // ── Reset Cut Module ──────────────────────────────────────────────
    btnCutNewVideo.addEventListener('click', resetCutModule);

    function resetCutModule() {
        cutSelectedFile = null;
        cutSessionId = null;
        cutSrtEntries = [];
        cutClipsGenerated = [];
        cutFileInput.value = '';
        btnAnalyzeCuts.disabled = true;
        btnAnalyzeCuts.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Analisar Transcrição';
        cutUploadZone.innerHTML = `
            <i class="fa-solid fa-cloud-arrow-up cut-upload-icon"></i>
            <p class="cut-upload-title">Arraste um vídeo ou clique para selecionar</p>
            <p class="cut-upload-sub">MP4 · MOV · MKV · AVI · WebM</p>
        `;
        cutStepUpload.style.display = '';
        cutStepSuggestions.style.display = 'none';
        cutStepProgress.style.display = 'none';
        cutStepClips.style.display = 'none';
        cutSuggestionsList.innerHTML = '';
        cutClipsList.innerHTML = '';
    }
});
