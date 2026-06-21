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

// "base+X" quando o relógio passa do fim de um tempo (acréscimos); senão o
// minuto corrente. base = 45 (1º T), 90 (2º T), 105 (1º T prorrog.), 120 (2º T).
function _periodPlus(base, minute, stoppage) {
  const over = (minute != null && minute > base)
    ? minute - base
    : (typeof stoppage === 'number' && stoppage > 0 ? stoppage : 0);
  if (over > 0) return `${base}+${over}'`;
  return `${minute != null ? minute : base}'`;
}

// Mapa das fases que CORREM: period -> [base, limite]. base = minuto em que a
// fase começa (1ºT=0, 2ºT=45, ET1=90, ET2=105); limite = onde entram acréscimos.
const _RUNNING = { '1H': [0, 45], '2H': [45, 90], ET1: [90, 105], ET2: [105, 120] };

// Relógio do jogo AO VIVO dirigido pelo STATUS do provider (confiável), não por
// chute de tempo. As FRONTEIRAS de fase (intervalo, volta, fim) vêm do provider:
// "HT"/"ET_HT"/"PENS"/"FT" são estados parados/encerrados. Dentro de uma fase que
// corre, conta o minuto a partir de period_started_at (carimbado pelo backend na
// transição de status) e segue "45+X"/"90+X"/... até o provider mudar a fase —
// nunca adivinha o intervalo. Precedência: minuto do provider > contagem desde o
// início da fase > estimativa pelo kickoff (último recurso). Pura/testável.
export function liveClock(match, nowMs = Date.now()) {
  // Só esconde o relógio se o status for EXPLICITAMENTE não-live; sem status
  // (ex.: payload de /api/live/matches) assume contexto ao vivo e mostra.
  if (!match || (match.status && match.status !== 'live')) return '';
  const { period, minute, stoppage, kickoff_utc, period_started_at } = match;
  // Estados PARADOS/ENCERRADOS: confiáveis pelo status do provider.
  if (period === 'HT') return 'Intervalo';
  if (period === 'ET_HT') return 'Intervalo da prorrogação';
  if (period === 'PENS') return 'Pênaltis';
  const ph = _RUNNING[period]; // [base, limite] da fase corrente (ou undefined)
  // 1) Minuto exato do provider, se vier número plausível (>0).
  const sMin = (typeof minute === 'number' && minute > 0) ? minute : null;
  if (ph && sMin != null) return _periodPlus(ph[1], sMin, stoppage);
  // 2) Conta desde o INÍCIO DA FASE (carimbo do backend). Passou do limite →
  //    "limite+X" e segue subindo até o provider sinalizar pausa/fim.
  if (ph && period_started_at) {
    const start = new Date(period_started_at).getTime();
    if (!Number.isNaN(start)) {
      const gm = ph[0] + Math.floor((nowMs - start) / 60000);
      return gm > ph[1] ? `${ph[1]}+${gm - ph[1]}'` : `${Math.max(ph[0] + 1, gm)}'`;
    }
  }
  // 3) Último recurso (sem fase/carimbo confiável): estimativa pelo kickoff real.
  return _estimateClock(kickoff_utc, nowMs, period === 'ET1' || period === 'ET2');
}

// Estimativa do relógio pelo tempo decorrido (quando o provider não manda o
// minuto ao vivo). Modelo do antigo liveMinute + acréscimos. Intervalo ~15min.
// Pura/testável.
function _estimateClock(kickoffIso, nowMs, inET) {
  const start = new Date(kickoffIso).getTime();
  if (Number.isNaN(start)) return 'AO VIVO';
  const e = Math.floor((nowMs - start) / 60000);
  if (e < 0) return 'AO VIVO';
  if (inET) {
    const g = e - 18; // desconta intervalo + intervalo da prorrogação (aprox.)
    if (g <= 105) return `${Math.max(91, g)}'`;
    if (g <= 108) return `105+${g - 105}'`;
    if (g <= 120) return `${g}'`;
    return `120+${Math.max(1, g - 120)}'`;
  }
  if (e <= 45) return `${Math.max(1, e)}'`;
  if (e <= 48) return `45+${e - 45}'`;
  if (e <= 60) return 'Intervalo';
  const g = e - 15; // 2º tempo: desconta o intervalo
  if (g <= 90) return `${g}'`;
  if (g <= 95) return `90+${g - 90}'`;
  return "90+'";
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
