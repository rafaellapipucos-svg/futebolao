"""Resolução do chaveamento com preenchimento preditivo antecipado.

Fontes de slot: 'BRA' (código), '1A'/'2B' (posição no grupo), '3:ABCDF'
(melhor 3º — Annex C), 'W73'/'L101' (vencedor/perdedor de jogo).

Um slot resolve assim que for matematicamente decidível:
- '1X'/'2X': grupo encerrado (ordem exata) OU posição garantida só por pontos (clinch).
- '3:*': todos os 12 grupos encerrados (conjunto dos 8 melhores 3ºs definido).
- 'W/L': jogo encerrado com vencedor conhecido (empate de mata-mata exige
  winner_team_id explícito).
A cascata é automática: resolvido um lado, jogos futuros que dependem dele exibem o time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import clinch as clinch_mod
from .entities import GROUPS, MATCH_TO_THIRD_SLOT, Match, Stage
from .standings import Row, compute_group


@dataclass
class GroupState:
    finished: bool
    rows: List[Row]  # ordem final (se finished) ou corrente
    outlook: Dict[int, clinch_mod.Outlook]

    def position_team(self, pos: int) -> Optional[int]:
        if self.finished:
            return self.rows[pos - 1].team_id
        for t, o in self.outlook.items():
            if o.guaranteed_position == pos:
                return t
        return None


@dataclass
class BracketContext:
    team_by_code: Dict[str, int]
    groups: Dict[str, GroupState]
    matches_by_id: Dict[int, Match]
    third_assignment: Optional[Dict[str, int]] = None  # {slot('1A'): team_id}

    def all_groups_finished(self) -> bool:
        return all(self.groups[g].finished for g in GROUPS)


def build_context(
    teams: Dict[int, "object"],  # {team_id: Team}
    matches: List[Match],
    third_assignment: Optional[Dict[str, int]] = None,
) -> BracketContext:
    by_group: Dict[str, Dict[int, str]] = {g: {} for g in GROUPS}
    team_by_code: Dict[str, int] = {}
    for tid, t in teams.items():
        team_by_code[t.code] = tid
        by_group[t.group][tid] = t.code
    groups: Dict[str, GroupState] = {}
    group_matches = [m for m in matches if m.stage == Stage.GROUP]
    for g in GROUPS:
        ids = by_group[g]
        mine = [m for m in group_matches if m.group == g]
        finished = clinch_mod.group_finished(ids.keys(), mine)
        rows = compute_group(ids, mine, include_live=False)
        outlook = clinch_mod.analyze(ids.keys(), mine)
        groups[g] = GroupState(finished=finished, rows=rows, outlook=outlook)
    return BracketContext(
        team_by_code=team_by_code,
        groups=groups,
        matches_by_id={m.id: m for m in matches},
        third_assignment=third_assignment,
    )


def resolve_source(ctx: BracketContext, source: str, match_id: int) -> Optional[int]:
    if source.startswith("3:"):
        if ctx.third_assignment is None:
            return None
        slot = MATCH_TO_THIRD_SLOT.get(match_id)
        if slot is None:
            raise ValueError(f"jogo {match_id} não tem slot de 3º colocado")
        return ctx.third_assignment.get(slot)
    if source.startswith("W") or source.startswith("L"):
        ref = ctx.matches_by_id.get(int(source[1:]))
        if ref is None:
            raise ValueError(f"referência inválida: {source}")
        return ref.winner_id() if source.startswith("W") else ref.loser_id()
    if source[0] in "12" and len(source) == 2 and source[1] in GROUPS:
        return ctx.groups[source[1]].position_team(int(source[0]))
    team_id = ctx.team_by_code.get(source)
    if team_id is None:
        raise ValueError(f"fonte de slot desconhecida: {source}")
    return team_id


def resolve_all(ctx: BracketContext) -> Dict[int, tuple]:
    """{match_id: (home_team_id|None, away_team_id|None)} para jogos não-grupo."""
    out: Dict[int, tuple] = {}
    for mid in sorted(ctx.matches_by_id):
        m = ctx.matches_by_id[mid]
        if m.stage == Stage.GROUP:
            continue
        home = m.home_team_id or resolve_source(ctx, m.home_source, mid)
        away = m.away_team_id or resolve_source(ctx, m.away_source, mid)
        out[mid] = (home, away)
    return out
