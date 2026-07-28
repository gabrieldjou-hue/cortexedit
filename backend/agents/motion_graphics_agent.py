"""
motion_graphics_agent.py
------------------------
Agente 17 — Motion Graphics.
Cria animacoes, titulos, transicoes graficas e overlays.
Elementos de branding (logo, vinheta) sao delegados ao Agente 16 (Identidade Visual).
"""

import logging
from typing import Dict, Any

from agents.base_agent import BaseAgent, AgentResult
from modules.graphics_module import GraphicsModule

logger = logging.getLogger(__name__)


class MotionGraphicsAgent(BaseAgent):
    def __init__(self):
        super().__init__("motion_graphics")
        self._module = GraphicsModule()

    def execute(self, task: Dict[str, Any], context) -> AgentResult:
        self._start_timer()
        logs = []
        limitations = [
            "Motion graphics simulado: sem engine de renderizacao de templates.",
            "Transicoes e titulos sao dados estruturais — sem render final.",
        ]

        narrative = task.get("narrative", {})
        profile = task.get("profile", {})
        script = task.get("script", {})

        # Usa modulo base para overlays
        base_overlays = self._module.create_overlays(narrative, profile)

        animations = []
        script_beats = script.get("script", []) if script else []

        if script_beats:
            for beat in script_beats[:5]:
                seq = beat.get("sequence", 1)
                animations.append({
                    "type": "title_animation",
                    "text": f"Sequencia {seq}",
                    "time": beat.get("start", 0.0),
                    "duration": 2.0,
                    "style": "fade_in_up",
                })

        animations.append({
            "type": "transition",
            "style": "cross_zoom",
            "duration": 0.5,
        })

        n_anim = len(animations)
        logs.append(f"Animacoes geradas: {n_anim}")
        logs.append(f"Transicoes: cross_zoom, fade")

        return self._make_result(
            success=True,
            data={
                "animations": animations,
                "titles": [a for a in animations if a["type"] == "title_animation"],
                "transitions": [a for a in animations if a["type"] == "transition"],
                "total_animations": n_anim,
            },
            extra_logs=logs,
            confidence=0.6,
            limitations=limitations,
            suggestions=[
                "Integrar engine de motion graphics (Motion / After Effects via API).",
                "Implementar titulos animados com FFmpeg drawtext.",
                "Adicionar templates de transicao personalizados.",
            ],
        )
