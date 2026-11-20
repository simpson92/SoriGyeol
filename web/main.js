// 소리결: 마이크 입력을 받아 소리 크기(dBFS)와 소리 종류를 화면에 보여 준다.
// 소리는 브라우저 안에서만 분석하고 저장·전송하지 않는다.

import { loadClassifier, loadTargets, analyze } from './classifier.js';
import { createStereoProbe, judgeStereo } from './stereo.js';
import { createAlertEngine } from './alert.js';
import { createApproachTracker, TREND_TEXT } from './approach.js';

// ── 소리 크기 표시 설정 ──
const MIN_DB = -80;          // 화면에 표시할 가장 작은 값
const QUIET_DB = -50;        // 이보다 작으면 '조용함'
const LOUD_DB = -20;         // 이보다 크면 '큼'
const HISTORY_SECONDS = 10;  // 그래프에 보여 줄 시간
const PEAK_HOLD_MS = 1500;   // 최대값 표시를 유지하는 시간

// ── 소리 분류 설정 ──
// YAMNet은 0.975초(16kHz 15,600샘플) 단위로 본다. 1초를 넣으면 남는 0.025초에 빈 소리를 채운
// 두 번째 결과가 생기므로, 최근 0.975초만 넣어 결과를 1개로 맞춘다. Python 평가·임베딩도 같은 방식 (11-20)
const WINDOW_SEC = 0.975;
const CLASSIFY_EVERY_SEC = 0.5; // 0.5초마다 최근 0.975초를 분석
// ── 알림 설정 ──
// 진동 패턴 (ms): 긴급 = 길게 3회, 주의 = 짧게 2회. iPhone Safari는 진동을 지원하지 않아 화면 깜빡임만 동작
const VIBRATE = { urgent: [500, 200, 500, 200, 500], normal: [100, 150, 100] };
const FLASH_MS = 1500;       // 화면 깜빡임 시간 (초당 2회 → 광과민 기준인 초당 3회 미만)

// ── 방향 실험 설정 ──
const STEREO_EVERY_MS = 250; // 측정값 갱신 간격
const STEREO_MIN_DB = -50;   // 이보다 작은 소리는 측정하지 않음 (잡음만 있을 때 값이 튀지 않게)

const el = {
  start: document.getElementById('startBtn'),
  stop: document.getElementById('stopBtn'),
  status: document.getElementById('status'),
  db: document.getElementById('dbValue'),
  label: document.getElementById('levelLabel'),
  meter: document.getElementById('meter'),
  fill: document.getElementById('meterFill'),
  peak: document.getElementById('meterPeak'),
  canvas: document.getElementById('history'),
  info: document.getElementById('info'),
  soundCard: document.getElementById('soundCard'),
  soundName: document.getElementById('soundName'),
  soundDetail: document.getElementById('soundDetail'),
  soundTrend: document.getElementById('soundTrend'),
  trendInfo: document.getElementById('trendInfo'),
  topList: document.getElementById('topList'),
  modelStatus: document.getElementById('modelStatus'),
  stVerdict: document.getElementById('stereoVerdict'),
  stChannels: document.getElementById('stChannels'),
  stLeft: document.getElementById('stLeft'),
  stRight: document.getElementById('stRight'),
  stDiff: document.getElementById('stDiff'),
  stCorr: document.getElementById('stCorr'),
  stLag: document.getElementById('stLag'),
  thresholds: document.getElementById('thresholds'),
  flash: document.getElementById('flash'),
  flashText: document.getElementById('flashText'),
};

// 오디오 상태
let stream = null;
let audioCtx = null;
let analyser = null;
let captureNode = null;
let samples = null;
let rafId = null;

// 소리 크기 상태
let history = [];            // [{t, db}]
let peakDb = MIN_DB;
let peakAt = 0;
let shownDb = MIN_DB;        // 숫자가 너무 빨리 바뀌지 않게 부드럽게 만든 값

// 소리 분류 상태
let classifier = null;
let targets = [];            // 알림 대상 클래스 (web/classes.json에서 읽음)
let ring = null;            // 최근 1초 오디오 (원형 버퍼)
let ringPos = 0;
let ringFilled = 0;
let sinceLastClassify = 0;
const alertEngine = createAlertEngine();
const approach = createApproachTracker(); // 가까워지는 중 / 멀어지는 중
let wakeLock = null;
let flashTimer = null;

// 방향 실험 상태
let stereoProbe = null;
let channelCount = null;
let lastStereoAt = 0;

// ─────────────────────────── 공통 ───────────────────────────

function setStatus(text, isError = false) {
  el.status.textContent = text;
  el.status.classList.toggle('is-error', isError);
}

function setModelStatus(text, isError = false) {
  el.modelStatus.textContent = text;
  el.modelStatus.classList.toggle('is-error', isError);
}

// ─────────────────────────── 소리 크기 ───────────────────────────

function toPercent(db) {
  const clamped = Math.max(MIN_DB, Math.min(0, db));
  return ((clamped - MIN_DB) / -MIN_DB) * 100;
}

function levelOf(db) {
  if (db < QUIET_DB) return { key: 'quiet', text: '조용함' };
  if (db < LOUD_DB) return { key: 'normal', text: '보통' };
  return { key: 'loud', text: '큼' };
}

// 한 프레임의 RMS를 dBFS로 바꾼다 (최대 크기 = 0 dBFS)
function measureDb() {
  analyser.getFloatTimeDomainData(samples);
  let sum = 0;
  for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
  const rms = Math.sqrt(sum / samples.length);
  return rms > 0 ? 20 * Math.log10(rms) : -Infinity;
}

function renderLevel(rawDb, now) {
  // 완전한 무음(-Infinity)도 화면 최솟값으로 맞춘다
  const db = Number.isFinite(rawDb) ? Math.max(rawDb, MIN_DB) : MIN_DB;

  // 표시용 값: 올라갈 때는 바로, 내려갈 때는 천천히
  shownDb = db > shownDb ? db : shownDb * 0.9 + db * 0.1;

  if (db > peakDb || now - peakAt > PEAK_HOLD_MS) {
    peakDb = db;
    peakAt = now;
  }

  const level = levelOf(shownDb);
  el.db.textContent = shownDb <= MIN_DB + 0.5 ? `≤${MIN_DB}` : shownDb.toFixed(0);
  el.label.textContent = level.text;
  el.label.className = `level-label is-${level.key}`;
  el.fill.className = `meter-fill is-${level.key}`;
  el.fill.style.width = `${toPercent(shownDb)}%`;
  el.peak.style.left = `calc(${toPercent(peakDb)}% - 3px)`;
  el.meter.setAttribute('aria-valuenow', Math.round(Math.max(MIN_DB, shownDb)));

  drawHistory(now);
}

function drawHistory(now) {
  const canvas = el.canvas;
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  if (canvas.width !== Math.round(w * dpr)) {
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  const y = (db) => h - (toPercent(db) / 100) * h;

  // '조용함'과 '큼' 기준선
  ctx.strokeStyle = '#d5dceb';
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);
  for (const ref of [QUIET_DB, LOUD_DB]) {
    ctx.beginPath();
    ctx.moveTo(0, y(ref));
    ctx.lineTo(w, y(ref));
    ctx.stroke();
  }
  ctx.setLineDash([]);

  // 최근 HISTORY_SECONDS 동안의 값
  const start = now - HISTORY_SECONDS * 1000;
  history = history.filter((p) => p.t >= start);
  if (history.length < 2) return;

  ctx.strokeStyle = '#2862c9';
  ctx.lineWidth = 2;
  ctx.beginPath();
  history.forEach((p, i) => {
    const x = ((p.t - start) / (HISTORY_SECONDS * 1000)) * w;
    const yy = y(p.db);
    if (i === 0) ctx.moveTo(x, yy);
    else ctx.lineTo(x, yy);
  });
  ctx.stroke();
}

function loop(now) {
  const db = measureDb();
  history.push({ t: now, db: Number.isFinite(db) ? Math.max(db, MIN_DB) : MIN_DB });
  approach.push(db, now);
  renderLevel(db, now);
  if (stereoProbe && now - lastStereoAt >= STEREO_EVERY_MS) {
    lastStereoAt = now;
    renderStereo(db);
  }
  rafId = requestAnimationFrame(loop);
}

// ─────────────────────────── 방향 실험 ───────────────────────────

function fmtDb(v) {
  return Number.isFinite(v) ? `${v.toFixed(1)} dBFS` : '무음';
}

function renderStereo(db) {
  el.stChannels.textContent = channelCount ?? '알 수 없음';
  if (!(db >= STEREO_MIN_DB)) return; // 소리가 작으면 이전 값을 유지

  const r = stereoProbe.read();
  const verdict = judgeStereo(channelCount, r);
  el.stVerdict.textContent = verdict.text;
  el.stVerdict.className = `dev-verdict is-${verdict.key}`;

  el.stLeft.textContent = fmtDb(r.dbL);
  el.stRight.textContent = fmtDb(r.dbR);
  el.stDiff.textContent = r.diffDb === null ? '—' : `${r.diffDb > 0 ? '+' : ''}${r.diffDb.toFixed(1)} dB`;
  el.stCorr.textContent = r.corr0.toFixed(3);
  el.stLag.textContent = verdict.key === 'stereo'
    ? `${r.bestLag > 0 ? '+' : ''}${r.bestLag} 샘플 (${r.bestLagUs.toFixed(0)}µs, 상관 ${r.bestCorr.toFixed(2)})`
    : '—';
}

function resetStereo() {
  el.stVerdict.textContent = '감지를 시작하면 이 기기가 마이크를 몇 채널로 주는지 확인해요.';
  el.stVerdict.className = 'dev-verdict';
  for (const k of ['stChannels', 'stLeft', 'stRight', 'stDiff', 'stCorr', 'stLag']) el[k].textContent = '—';
}

// ─────────────────────────── 소리 분류 ───────────────────────────

async function prepareClassifier() {
  try {
    const t0 = performance.now();
    [classifier, targets] = await Promise.all([loadClassifier(), loadTargets()]);
    const names = targets.map((t) => t.name).join(', ') || '없음';
    setModelStatus(`모델 준비 완료 (${((performance.now() - t0) / 1000).toFixed(1)}초) · 알림 대상: ${names}`);
  } catch (err) {
    console.error(err);
    setModelStatus('소리 분류 모델을 불러오지 못했어요. 인터넷 연결을 확인하고 새로고침해 주세요. (소리 크기는 계속 볼 수 있어요)', true);
  }
}

// AudioWorklet에서 2048 샘플씩 들어오는 소리를 최근 0.975초 버퍼에 쌓는다
function onAudioChunk(chunk) {
  for (let i = 0; i < chunk.length; i++) {
    ring[ringPos] = chunk[i];
    ringPos = (ringPos + 1) % ring.length;
  }
  ringFilled = Math.min(ring.length, ringFilled + chunk.length);
  sinceLastClassify += chunk.length;

  const every = Math.round(audioCtx.sampleRate * CLASSIFY_EVERY_SEC);
  if (classifier && ringFilled === ring.length && sinceLastClassify >= every) {
    sinceLastClassify = 0;
    classifyNow();
  }
}

function classifyNow() {
  // 원형 버퍼를 시간 순서대로 펼친다
  const windowed = new Float32Array(ring.length);
  windowed.set(ring.subarray(ringPos));
  windowed.set(ring.subarray(0, ringPos), ring.length - ringPos);

  const t0 = performance.now();
  const result = analyze(classifier, windowed, audioCtx.sampleRate, targets);
  const ms = performance.now() - t0;

  renderSound(result, ms);
}

function renderSound({ top, targets: scored, windows }, ms) {
  const now = performance.now();
  const { fire, showing, pending } = alertEngine.update(scored, now);

  if (fire) notify(showing);

  if (showing) {
    const score = scored.find((t) => t.id === showing.id)?.score ?? showing.score;
    el.soundCard.className = `sound-card is-${showing.level}`;
    el.soundName.textContent = showing.name;
    el.soundDetail.textContent =
      `${showing.level === 'urgent' ? '긴급' : '주의'} · 확신도 ${Math.round(score * 100)}%`;
  } else if (pending) {
    el.soundCard.className = 'sound-card';
    el.soundName.textContent = `${pending.name}?`;
    el.soundDetail.textContent = `확인 중… (${Math.round(pending.score * 100)}%)`;
  } else {
    el.soundCard.className = 'sound-card';
    el.soundName.textContent = top[0] ? top[0].name : '—';
    el.soundDetail.textContent = '알림 대상 아님';
  }

  el.topList.replaceChildren(
    ...top.map((t) => {
      const li = document.createElement('li');
      const name = document.createElement('span');
      name.className = 'name';
      name.textContent = t.name;
      li.title = `${t.name} ${Math.round(t.score * 100)}%`;
      li.append(name);
      const score = document.createElement('span');
      score.className = 'score';
      score.textContent = `${Math.round(t.score * 100)}%`;
      li.append(score);
      return li;
    }),
  );

  renderTrend(approach.judge(showing?.id ?? null));

  el.info.dataset.classifyMs = ms.toFixed(0);
  el.info.dataset.windows = String(windows);
  updateInfo();
}

// 확정된 사이렌·경적이 화면에 있을 때만 '가까워지는 중 / 멀어지는 중'을 덧붙인다 (애매하면 빈칸)
// 자리는 항상 잡아 두어 표시가 생기고 사라질 때 카드 높이가 바뀌지 않게 한다
function renderTrend({ state, slope, up, down, off = 0 }) {
  el.soundTrend.className = state ? `sound-trend is-${state}` : 'sound-trend';
  el.soundTrend.textContent = state ? TREND_TEXT[state] : '';
  el.trendInfo.textContent = slope === null
    ? '소리 크기 변화: 알림 대상이 확정되면 계산해요'
    : `소리 크기 변화: ${slope > 0 ? '+' : ''}${slope.toFixed(1)} dB/초` +
      ` · 커짐 연속 ${up}번(2번이면 표시) · 작아짐 연속 ${down}번(3번이면 표시)` +
      (state ? ` → ${TREND_TEXT[state]} (벗어남 ${off}/3)` : '');
}

function resetSound() {
  alertEngine.reset();
  approach.reset();
  renderTrend({ state: null, slope: null, up: 0, down: 0 });
  hideFlash();
  el.soundCard.className = 'sound-card';
  el.soundName.textContent = '—';
  el.soundDetail.textContent = '감지를 시작하면 약 1초마다 소리 종류를 판단해요.';
  const li = document.createElement('li');
  li.className = 'top-empty';
  li.textContent = '아직 결과가 없어요';
  el.topList.replaceChildren(li);
}

// ─────────────────────────── 알림 동작 ───────────────────────────

function notify(target) {
  // 진동 (Android Chrome 등 지원 기기만)
  if ('vibrate' in navigator) {
    navigator.vibrate(VIBRATE[target.level] ?? VIBRATE.normal);
  }
  // 화면 전체 깜빡임 (모든 기기). '지금 들리는 소리' 카드는 깜빡임 위에 그대로 보이게 둔다
  // (11-20 시험: 전체를 덮으면 '가까워지는 중' 같은 정보를 못 봄)
  document.body.classList.add('is-flashing');
  el.flashText.textContent = target.name;
  el.flash.className = `flash is-${target.level}`;
  el.flash.hidden = false;
  clearTimeout(flashTimer);
  flashTimer = setTimeout(hideFlash, FLASH_MS);
}

function hideFlash() {
  clearTimeout(flashTimer);
  document.body.classList.remove('is-flashing');
  el.flash.hidden = true;
  el.flash.className = 'flash';
}

// ─────────────────────────── 화면 켜짐 유지 ───────────────────────────
// 화면이 꺼지면 브라우저가 마이크를 멈추므로, 감지 중에는 화면이 꺼지지 않게 한다.

async function keepScreenOn() {
  if (!('wakeLock' in navigator)) return false;
  try {
    wakeLock = await navigator.wakeLock.request('screen');
    wakeLock.addEventListener('release', () => { wakeLock = null; });
    return true;
  } catch (err) {
    console.warn('화면 켜짐 유지 실패:', err);
    return false;
  }
}

function releaseScreen() {
  wakeLock?.release();
  wakeLock = null;
}

// 다른 앱에 갔다가 돌아오면 화면 켜짐 유지가 풀려 있으므로 다시 요청한다
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && stream && !wakeLock) keepScreenOn().then(updateStatusLine);
});

function updateStatusLine() {
  if (!stream) return;
  const base = classifier ? '소리를 듣고 있어요.' : '소리를 듣고 있어요. 분류 모델이 준비되면 소리 종류도 보여 드려요.';
  setStatus(wakeLock ? `${base} 화면 켜짐 유지 중` : `${base} 화면이 꺼지면 감지가 멈춰요`);
}

// ─────────────────────────── 시작 / 멈춤 ───────────────────────────

function updateInfo() {
  if (!audioCtx || !stream) return;
  const track = stream.getAudioTracks()[0];
  const settings = track.getSettings();
  const ms = el.info.dataset.classifyMs;
  el.info.textContent =
    `샘플레이트 ${audioCtx.sampleRate}Hz · 마이크: ${track.label || '기본 마이크'}` +
    ` · 잡음 억제 ${settings.noiseSuppression ? '켜짐' : '꺼짐'}` +
    (ms ? ` · 분류 ${ms}ms (창 ${WINDOW_SEC}초, 결과 ${el.info.dataset.windows}개)` : '');
  // 알림 기준 점수는 사용자에게는 필요 없는 내부 설정이라 개발 정보 칸에만 보여 준다 (11-19 의논 ③-2)
  el.thresholds.textContent =
    '알림 기준: ' + (targets.map((t) => `${t.name} ${Math.round(t.threshold * 100)}%`).join(' · ') || '없음');
}

async function start() {
  if (!window.isSecureContext) {
    setStatus('이 주소에서는 마이크를 쓸 수 없어요. https:// 주소나 localhost로 열어 주세요.', true);
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    setStatus('이 브라우저는 마이크 입력을 지원하지 않아요. 최신 Chrome으로 열어 주세요.', true);
    return;
  }

  el.start.disabled = true;
  setStatus('마이크 권한을 확인하는 중이에요…');

  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        // 사이렌·경적을 잡음으로 지우지 않도록 브라우저 보정을 끈다
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
        channelCount: { ideal: 2 }, // 방향 실험: 가능하면 2채널로 받는다
      },
      video: false,
    });
  } catch (err) {
    el.start.disabled = false;
    if (err.name === 'NotAllowedError') {
      setStatus('마이크 권한이 거부됐어요. 주소창 옆 자물쇠 아이콘에서 마이크를 허용한 뒤 다시 눌러 주세요.', true);
    } else if (err.name === 'NotFoundError') {
      setStatus('마이크를 찾지 못했어요. 마이크가 연결돼 있는지 확인해 주세요.', true);
    } else {
      setStatus(`마이크를 켜지 못했어요: ${err.name}`, true);
    }
    return;
  }

  audioCtx = new AudioContext();
  if (audioCtx.state === 'suspended') await audioCtx.resume();
  const source = audioCtx.createMediaStreamSource(stream);

  // 소리 크기용
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 2048;
  analyser.smoothingTimeConstant = 0;
  source.connect(analyser);             // 스피커로는 연결하지 않음 (하울링 방지)
  samples = new Float32Array(analyser.fftSize);

  // 방향 실험용: 채널을 나눠서 따로 측정
  channelCount = stream.getAudioTracks()[0].getSettings().channelCount ?? null;
  stereoProbe = createStereoProbe(audioCtx, source);
  lastStereoAt = 0;
  resetStereo();

  // 소리 분류용: AudioWorklet으로 오디오를 받아 최근 0.975초를 모은다
  // (내림: 44.1kHz 등에서 반올림으로 1샘플이 넘치면 빈 소리를 채운 결과가 하나 더 생길 수 있음)
  ring = new Float32Array(Math.floor(audioCtx.sampleRate * WINDOW_SEC));
  ringPos = 0;
  ringFilled = 0;
  sinceLastClassify = 0;
  try {
    await audioCtx.audioWorklet.addModule('capture-worklet.js');
    captureNode = new AudioWorkletNode(audioCtx, 'capture-processor');
    captureNode.port.onmessage = (e) => onAudioChunk(e.data);
    const mute = audioCtx.createGain();
    mute.gain.value = 0;                // 소리는 내보내지 않고, 처리만 계속되게 연결
    source.connect(captureNode).connect(mute).connect(audioCtx.destination);
  } catch (err) {
    console.error(err);
    setModelStatus('이 브라우저에서는 소리 분류를 할 수 없어요 (AudioWorklet 미지원). 소리 크기는 계속 볼 수 있어요.', true);
  }

  // 마이크가 중간에 멈추면 바로 알린다 (권한 해제, 다른 앱 전환 등)
  const track = stream.getAudioTracks()[0];
  track.addEventListener('ended', () => {
    stop();
    setStatus('감지가 멈췄어요. 마이크 연결이 끊겼어요. 다시 시작해 주세요.', true);
  });
  track.addEventListener('mute', () => setStatus('마이크 입력이 잠시 멈췄어요.', true));
  track.addEventListener('unmute', updateStatusLine);

  updateInfo();
  history = [];
  peakDb = MIN_DB;
  shownDb = MIN_DB;
  resetSound();
  el.stop.disabled = false;
  await keepScreenOn();
  updateStatusLine();
  rafId = requestAnimationFrame(loop);
}

function stop() {
  if (rafId) cancelAnimationFrame(rafId);
  rafId = null;
  if (captureNode) {
    captureNode.port.onmessage = null;
    captureNode.disconnect();
    captureNode = null;
  }
  stereoProbe?.disconnect();
  stereoProbe = null;
  releaseScreen();
  stream?.getTracks().forEach((t) => t.stop());
  stream = null;
  audioCtx?.close();
  audioCtx = null;
  el.start.disabled = false;
  el.stop.disabled = true;
  el.label.textContent = '멈춤';
  el.label.className = 'level-label';
  resetSound();
  setStatus('멈췄어요. 다시 보려면 \'감지 시작\'을 누르세요.');
}

el.start.addEventListener('click', start);
el.stop.addEventListener('click', stop);

// 페이지를 열자마자 모델을 미리 불러 둔다 (처음 한 번 약 25MB)
prepareClassifier();
