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

// Minuto do jogo AO VIVO. Prefere o minuto do servidor (provider/admin); sem
// ele, ESTIMA pelo relógio desde o apito (considera ~15min de intervalo).
// Aproximação suficiente para exibir "23'", "Intervalo", "78'", "90+'".
export function liveMinute(kickoffIso, serverMinute = null, nowMs = Date.now()) {
  if (serverMinute != null) return `${serverMinute}'`;
  const start = new Date(kickoffIso).getTime();
  if (Number.isNaN(start)) return 'AO VIVO';
  const elapsed = Math.floor((nowMs - start) / 60000);
  if (elapsed < 0) return 'AO VIVO';
  if (elapsed <= 45) return `${Math.max(1, elapsed)}'`;
  if (elapsed <= 60) return 'Intervalo';
  if (elapsed <= 105) return `${Math.min(90, elapsed - 15)}'`;
  if (elapsed <= 130) return "90+'";
  return 'AO VIVO';
}

// "base+X" quando o relógio passa do fim de um tempo (acréscimos); senão o
// minuto corrente. base = 45 (1º T), 90 (2º T), 105 (1º T prorrog.), 120 (2º T).
function _periodPlus(base, minute, stoppage) {
  const over = (minute != null && minute > base)
    ? minute - base
    : (typeof stoppage === 'number' && stoppage > 0 ? stoppage : 0);
  if (over > 0) return `${base}+${over}'`;
  return `${minute != null ? minute : base}'`;
}

// Relógio do jogo AO VIVO ciente da FASE (period do servidor): 1º tempo "45+X",
// 2º tempo "90+X", prorrogação "105+X"/"120+X" e "Pênaltis". Sem period (sem
// provider), cai na estimativa por relógio (ancorada no kickoff REAL, que o
// poller mantém atualizado). Puro/testável.
export function liveClock(match, nowMs = Date.now()) {
  if (!match || match.status !== 'live') return '';
  const { period, minute, stoppage, kickoff_utc } = match;
  switch (period) {
    case '1H': return _periodPlus(45, minute, stoppage);
    case 'HT': return 'Intervalo';
    case '2H': return _periodPlus(90, minute, stoppage);
    case 'ET1': return _periodPlus(105, minute, stoppage);
    case 'ET_HT': return 'Intervalo da prorrogação';
    case 'ET2': return _periodPlus(120, minute, stoppage);
    case 'PENS': return 'Pênaltis';
    case 'FT': return '';
    default: return liveMinute(kickoff_utc, minute, nowMs);
  }
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

// Sigla de 3 letras EM PORTUGUÊS (estilo transmissão BR) p/ a tabela compacta
// quando o card é estreito. Onde o código FIFA já casa com o PT, repete (BRA,
// ARG, FRA…); onde difere, usa a sigla PT usual (Alemanha=ALE, Inglaterra=ING,
// Holanda=HOL, EUA, Coreia=COR…). Fallback: 3 letras do código. Pura/testável.
const SIGLA_PT = {
  MEX: 'MEX', RSA: 'AFS', KOR: 'COR', CZE: 'TCH', CAN: 'CAN', BIH: 'BOS',
  QAT: 'CAT', SUI: 'SUI', BRA: 'BRA', MAR: 'MAR', HAI: 'HAI', SCO: 'ESC',
  USA: 'EUA', PAR: 'PAR', AUS: 'AUS', TUR: 'TUR', GER: 'ALE', CUW: 'CUR',
  CIV: 'CDM', ECU: 'EQU', NED: 'HOL', JPN: 'JAP', SWE: 'SUE', TUN: 'TUN',
  BEL: 'BEL', EGY: 'EGI', IRN: 'IRA', NZL: 'NZL', ESP: 'ESP', CPV: 'CAB',
  KSA: 'ARA', URU: 'URU', FRA: 'FRA', SEN: 'SEN', IRQ: 'IRQ', NOR: 'NOR',
  ARG: 'ARG', ALG: 'ALG', AUT: 'AUT', JOR: 'JOR', POR: 'POR', COD: 'RDC',
  UZB: 'UZB', COL: 'COL', ENG: 'ING', CRO: 'CRO', GHA: 'GAN', PAN: 'PAN',
};

export function siglaPt(team) {
  if (!team) return '';
  const code = team.code || '';
  return SIGLA_PT[code] || code.slice(0, 3).toUpperCase();
}
