// format.js — datas/horas no fuso do navegador, agrupamento por dia, countdown.
// Puro (sem DOM): testável com node:test.

const TIME_FMT = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' });
const DAY_FMT = new Intl.DateTimeFormat('pt-BR', {
  weekday: 'long', day: 'numeric', month: 'long',
});

export function fmtTime(iso) {
  return TIME_FMT.format(new Date(iso));
}

export function fmtDayLong(iso) {
  return DAY_FMT.format(new Date(iso));
}

export function dayKey(iso) {
  const d = new Date(iso);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function groupByDay(items, getIso = (x) => x.kickoff_utc) {
  const groups = [];
  const index = new Map();
  for (const item of items) {
    const key = dayKey(getIso(item));
    if (!index.has(key)) {
      const group = { key, label: fmtDayLong(getIso(item)), items: [] };
      index.set(key, group);
      groups.push(group);
    }
    index.get(key).items.push(item);
  }
  return groups;
}

export function countdown(toIso, nowMs = Date.now()) {
  const diff = new Date(toIso).getTime() - nowMs;
  if (diff <= 0) return null;
  const totalSec = Math.floor(diff / 1000);
  const d = Math.floor(totalSec / 86400);
  const h = Math.floor((totalSec % 86400) / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`;
  if (m > 0) return `${m}m ${String(s).padStart(2, '0')}s`;
  return `${s}s`;
}

export function minuteLabel(status, minute) {
  if (status !== 'live') return '';
  if (minute == null) return 'AO VIVO';
  return `${minute}′`;
}

export function statusLabel(status) {
  return { scheduled: 'Agendado', live: 'Ao vivo', finished: 'Encerrado' }[status] || status;
}

// Bandeiras — padrão do site é IMAGEM Twemoji local (emoji de bandeira não
// renderiza no Windows). flagSrc converte o emoji do seed no caminho do asset:
// /assets/flags/<codepoints hex minúsculos separados por hífen>.svg.
// Funciona também para Inglaterra/Escócia (🏴 + tag sequence) — o Twemoji tem
// esses assets. fe0f (variation selector) é omitido nos nomes do Twemoji.
export function flagSrc(team) {
  const flag = (team && team.flag) || '';
  if (!flag) return '';
  const codes = [...flag]
    .map((ch) => ch.codePointAt(0).toString(16))
    .filter((code) => code !== 'fe0f');
  return `/assets/flags/${codes.join('-')}.svg`;
}

// Fallback textual (ex.: asset ausente, falha de rede): sigla curta de 2
// letras (.flag-abbr) para sub-divisões 🏴 (ENG/SCO) ou emoji puro nos demais.
const SUBDIV_ABBR = { ENG: 'IN', SCO: 'SC', WAL: 'GA', NIR: 'IN' };

export function flagIsAbbr(team) {
  if (!team) return false;
  const f = team.flag || '';
  return !f || f.codePointAt(0) === 0x1F3F4;
}

export function teamFlag(team) {
  if (!team) return '';
  if (!flagIsAbbr(team)) return team.flag;
  const code = team.code || '';
  return SUBDIV_ABBR[code] || code.slice(0, 2).toUpperCase() || '?';
}
