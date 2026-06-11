"""Ranking dos terceiros colocados e alocação oficial FIFA (Annex C).

A tabela Annex C (495 combinações) mapeia o conjunto dos 8 grupos cujos 3ºs se
classificaram para os slots do R32, na ordem [1A,1B,1D,1E,1G,1I,1K,1L].
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .entities import THIRD_SLOTS
from .standings import Row


def parse_annex_c(text: str) -> Dict[str, Dict[str, str]]:
    """'EFGHIJKL:EJIFHGLK' → {'EFGHIJKL': {'1A':'E','1B':'J',...}}"""
    table: Dict[str, Dict[str, str]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        combo, assign = line.split(":")
        if len(combo) != 8 or len(assign) != 8:
            raise ValueError(f"linha Annex C inválida: {line}")
        table[combo] = dict(zip(THIRD_SLOTS, assign))
    if len(table) != 495:
        raise ValueError(f"Annex C deve ter 495 combinações, tem {len(table)}")
    return table


def rank_thirds(third_rows: Dict[str, Row]) -> List[Tuple[str, Row]]:
    """third_rows: {grupo: Row do 3º colocado}. Ordena melhor→pior."""
    return sorted(
        third_rows.items(),
        key=lambda kv: (-kv[1].points, -kv[1].gd, -kv[1].gf, kv[1].code),
    )


def qualified_thirds(third_rows: Dict[str, Row]) -> List[str]:
    """Letras dos 8 grupos com 3ºs classificados (melhores 8 de 12)."""
    ranked = rank_thirds(third_rows)
    return sorted(g for g, _ in ranked[:8])


def allocate(
    table: Dict[str, Dict[str, str]], third_team_by_group: Dict[str, int],
    qualified: List[str],
) -> Optional[Dict[str, int]]:
    """Retorna {slot: team_id} conforme Annex C, ou None se combo incompleto."""
    if len(qualified) != 8:
        return None
    combo = "".join(sorted(qualified))
    assignment = table.get(combo)
    if assignment is None:
        raise KeyError(f"combinação fora da Annex C: {combo}")
    return {slot: third_team_by_group[group] for slot, group in assignment.items()}
