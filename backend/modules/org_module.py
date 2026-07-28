"""
org_module.py
-------------
Módulo de Organização Narrativa.
Seleciona e ordena os takes da análise para construir a estrutura narrativa
que alimenta o EditingModule.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class OrganizationModule:
    """
    Organiza os cortes sugeridos pela análise + refinamentos do AI Engine
    numa estrutura narrativa coerente com o perfil de produção.
    """

    def build_narrative(
        self,
        combined_metadata: Dict[str, Any],
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        logger.info("OrganizationModule: Building narrative structure.")

        cut_suggestions: List[Dict] = combined_metadata.get("cut_suggestions", [])
        files_metadata: List[Dict] = combined_metadata.get("files_metadata", [])
        job_id: str = combined_metadata.get("job_id", "unknown")
        profile_name: str = profile.get("name", "default")

        # Seleção de takes baseada no perfil
        selected_takes = self._select_takes(cut_suggestions, files_metadata, profile_name)

        narrative = {
            "job_id": job_id,
            "profile": profile_name,
            "selected_takes": selected_takes,
            "total_segments": len(selected_takes),
        }

        logger.info(
            f"OrganizationModule: {len(selected_takes)} take(s) selected for profile '{profile_name}'."
        )
        return narrative

    def _select_takes(
        self,
        cuts: List[Dict],
        files_meta: List[Dict],
        profile: str,
    ) -> List[Dict]:
        """
        Aplica regras de seleção por perfil:
        - podcast: inclui todos os segmentos (conversa contínua)
        - youtube: pula os primeiros 5s de cada clipe (intro)
        - reels: pega só os primeiros 60s (short-form)
        - cinematic: segmentos longos (>= 20s)
        - institutional: todos os segmentos ordenados
        """
        if not cuts:
            # Fallback: usa os arquivos inteiros
            takes = []
            for m in files_meta:
                dur = m.get("duration", 0.0)
                if dur > 0:
                    takes.append({
                        "file": m["path"],
                        "start": 0.0,
                        "end": dur,
                    })
            return takes

        if profile == "podcast":
            return cuts  # Todos os segmentos
        elif profile == "youtube":
            # Pula primeiros 5s de cada arquivo
            return [
                {**c, "start": max(c["in"] + 5, c["in"]), "end": c["out"]}
                for c in cuts
            ]
        elif profile == "reels":
            # Pega os primeiros segmentos até 60s total
            selected, total = [], 0.0
            for c in cuts:
                dur = c["out"] - c["in"]
                if total + dur > 60:
                    break
                selected.append({"file": c["file"], "start": c["in"], "end": c["out"]})
                total += dur
            return selected or [{"file": cuts[0]["file"], "start": cuts[0]["in"], "end": cuts[0]["out"]}]
        elif profile == "cinematic":
            return [
                {"file": c["file"], "start": c["in"], "end": c["out"]}
                for c in cuts if (c["out"] - c["in"]) >= 20
            ] or [{"file": cuts[0]["file"], "start": cuts[0]["in"], "end": cuts[0]["out"]}]
        else:
            # institutional e padrão
            return [{"file": c["file"], "start": c["in"], "end": c["out"]} for c in cuts]
