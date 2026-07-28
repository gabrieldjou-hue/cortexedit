"""
edit_module.py
--------------
Módulo de Edição.
Gera a EDL (Edit Decision List) real a partir da narrative_structure,
com referências aos arquivos reais de vídeo uploadados.
"""

import logging
import os
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class EditingModule:
    """
    Gera a EDL que o RenderModule vai consumir.
    A EDL contém a lista de clipes (arquivo + in/out) na ordem correta.
    """

    def generate_edl(
        self, narrative_structure: Dict[str, Any], profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        logger.info("EditingModule: Generating EDL from narrative structure.")

        selected_takes: List[Dict[str, Any]] = narrative_structure.get("selected_takes", [])
        job_id: str = narrative_structure.get("job_id", "unknown")

        edl: Dict[str, Any] = {
            "job_id": job_id,
            "profile": profile.get("name", "default"),
            "resolution": "1920x1080",
            "clips": [],
            "total_duration": 0.0,
        }

        current_time = 0.0
        for take in selected_takes:
            src_file = take.get("file", "")
            t_in = take.get("start", 0.0)
            t_out = take.get("end", 0.0)
            duration = t_out - t_in

            if duration <= 0 or not os.path.exists(src_file):
                continue

            edl["clips"].append({
                "file": src_file,
                "in": t_in,
                "out": t_out,
                "duration": duration,
                "timeline_in": current_time,
                "timeline_out": current_time + duration,
            })
            current_time += duration

        edl["total_duration"] = round(current_time, 2)
        logger.info(
            f"EditingModule: EDL ready – {len(edl['clips'])} clip(s), "
            f"{edl['total_duration']:.1f}s total."
        )
        return edl
