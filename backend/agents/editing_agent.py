"""
editing_agent.py
----------------
Agente 11 — Edicao.
Executa cortes, jump cuts, L cuts, J cuts, speed ramp,
zoom inteligente, reenquadramento e multicâmera.
Respeita o estilo definido.
"""

import logging
from typing import Dict, Any, List

from agents.base_agent import BaseAgent, AgentResult
from modules.edit_module import EditingModule

logger = logging.getLogger(__name__)


class EditingAgent(BaseAgent):
    def __init__(self):
        super().__init__("editing")
        self._module = EditingModule()

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []
        limitations = [
            "Efeitos avancados (speed ramp, zoom, multicam) sao metadados — nao renderizados.",
            "L/J cuts representados como estrutura de timeline, sem processamento real de audio/video.",
        ]

        narrative = task.get("narrative", {})
        profile = task.get("profile", {})
        script = task.get("script", {})

        # Gera EDL base
        edl = self._module.generate_edl(narrative, profile)
        clips: List[Dict] = edl.get("clips", [])

        # Aplica tecnicas de edicao avancada (metadados para o render)
        profile_name = profile.get("name", "default")
        techniques = []

        if clips:
            # Jump cuts: simulacao para perfil reels/youtube
            if profile_name in ("reels", "youtube"):
                for clip in clips:
                    clip["jump_cut"] = True
                    clip["speed"] = 1.0
                techniques.append("jump_cut (aceleracao de ritmo)")

            # Speed ramp: simulacao
            if profile_name == "cinematic":
                for i, clip in enumerate(clips):
                    if i == 0 or i == len(clips) - 1:
                        clip["speed_ramp"] = "slow_motion"
                        clip["speed"] = 0.5
                    else:
                        clip["speed_ramp"] = None
                        clip["speed"] = 1.0
                techniques.append("speed_ramp (slow motion nas bordas)")

            # L/J cuts: estrutura de transicao
            for i in range(len(clips) - 1):
                clips[i]["l_cut"] = 0.5
                clips[i + 1]["j_cut"] = 0.5
            techniques.append("L/J cuts (crossfade de audio)")

            # Zoom inteligente: baseado em qualidade
            for clip in clips:
                quality = clip.get("quality_score", 0.8)
                if quality < 0.7:
                    clip["smart_zoom"] = {"crop": "center", "scale": 1.1}
                else:
                    clip["smart_zoom"] = None
            techniques.append("smart_zoom (reenquadramento automatico)")

        edl["techniques"] = techniques
        edl["editing_profile"] = profile_name
        edl["multicam"] = len(set(c.get("file", "") for c in clips)) > 1

        n_clips = len(clips)
        total_dur = edl.get("total_duration", 0.0)
        logs.append(f"EDL gerada: {n_clips} clip(s), {total_dur:.1f}s total")
        logs.append(f"Tecnicas aplicadas: {', '.join(techniques) if techniques else 'nenhuma'}")
        if edl["multicam"]:
            logs.append("Multi-camera detectado")

        return self._make_result(
            success=True,
            data=edl,
            extra_logs=logs,
            confidence=0.9,
            limitations=limitations,
            suggestions=[
                "Implementar speed ramp real com FFmpeg setpts/atempo.",
                "Adicionar deteccao de take mais limpo em multicam.",
                "Renderizar zoom inteligente com FFmpeg zoompan.",
            ],
        )
