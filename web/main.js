// 소리결 1주차: 마이크 입력을 받아 소리 크기(dBFS)를 화면에 보여 준다.
// 소리는 브라우저 안에서만 분석하고 저장·전송하지 않는다.

const MIN_DB = -80;          // 화면에 표시할 가장 작은 값
const QUIET_DB = -50;        // 이보다 작으면 '조용함'
const LOUD_DB = -20;         // 이보다 크면 '큼'
const HISTORY_SECONDS = 10;  // 그래프에 보여 줄 시간
const PEAK_HOLD_MS = 1500;   // 최대값 표시를 유지하는 시간

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
};

let stream = null;
let audioCtx = null;
let analyser = null;
let samples = null;
let rafId = null;
let history = [];            // [{t, db}]
let peakDb = MIN_DB;
let peakAt = 0;
let shownDb = MIN_DB;        // 숫자가 너무 빨리 바뀌지 않게 부드럽게 만든 값

function setStatus(text, isError = false) {
  el.status.textContent = text;
  el.status.classList.toggle('is-error', isError);
}

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

function render(rawDb, now) {
  // 완전한 무음(-Infinity)도 화면 최솟값으로 맞춘다
  const db = Number.isFinite(rawDb) ? Math.max(rawDb, MIN_DB) : MIN_DB;

  // 표시용 값: 올라갈 때는 바로, 내려갈 때는 천천히
  shownDb = db > shownDb ? db : shownDb * 0.9 + db * 0.1;

  if (db > peakDb || now - peakAt > PEAK_HOLD_MS) {
    peakDb = Math.max(db, MIN_DB);
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
  render(db, now);
  rafId = requestAnimationFrame(loop);
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
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 2048;              // 약 43ms 분량 (48kHz 기준)
  analyser.smoothingTimeConstant = 0;
  source.connect(analyser);             // 스피커로는 연결하지 않음 (하울링 방지)
  samples = new Float32Array(analyser.fftSize);

  // 마이크가 중간에 멈추면 바로 알린다 (권한 해제, 다른 앱 전환 등)
  const track = stream.getAudioTracks()[0];
  track.addEventListener('ended', () => {
    stop();
    setStatus('감지가 멈췄어요. 마이크 연결이 끊겼어요. 다시 시작해 주세요.', true);
  });
  track.addEventListener('mute', () => setStatus('마이크 입력이 잠시 멈췄어요.', true));
  track.addEventListener('unmute', () => setStatus('소리를 듣고 있어요.'));

  const settings = track.getSettings();
  el.info.textContent =
    `샘플레이트 ${audioCtx.sampleRate}Hz · 마이크: ${track.label || '기본 마이크'}` +
    ` · 잡음 억제 ${settings.noiseSuppression ? '켜짐' : '꺼짐'}`;

  history = [];
  peakDb = MIN_DB;
  shownDb = MIN_DB;
  el.stop.disabled = false;
  setStatus('소리를 듣고 있어요.');
  rafId = requestAnimationFrame(loop);
}

function stop() {
  if (rafId) cancelAnimationFrame(rafId);
  rafId = null;
  stream?.getTracks().forEach((t) => t.stop());
  stream = null;
  audioCtx?.close();
  audioCtx = null;
  el.start.disabled = false;
  el.stop.disabled = true;
  el.label.textContent = '멈춤';
  el.label.className = 'level-label';
  setStatus('멈췄어요. 다시 보려면 \'감지 시작\'을 누르세요.');
}

el.start.addEventListener('click', start);
el.stop.addEventListener('click', stop);