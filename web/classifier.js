// 소리 종류 분류: MediaPipe Audio Classifier + YAMNet (브라우저 안에서 실행)
// YAMNet은 AudioSet 521개 라벨 중 어떤 소리인지 점수를 낸다.
// 우리는 그중 알림 대상 클래스(configs/classes.yaml 기준)에 해당하는 라벨만 묶어서 판단한다.

import {
  AudioClassifier,
  FilesetResolver,
} from 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-audio@1.2.3/audio_bundle.mjs';

const WASM_BASE = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-audio@1.2.3/wasm';
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/audio_classifier/yamnet/float32/1/yamnet.tflite';

// 기본 기준 점수. 클래스별 값은 classes.yaml의 threshold(준형 평가 결과)가 있으면 그것을 쓴다.
export const THRESHOLD = 0.3;

// 우리 클래스 id(configs/classes.yaml) → YAMNet 라벨 (yamnet_class_map.csv의 display_name)
// 클래스의 이름·우선순위·사용 여부는 classes.yaml이 정하고(web/classes.json으로 내보냄),
// 여기에는 "YAMNet의 어떤 라벨을 그 클래스로 볼지"만 둔다.
export const YAMNET_LABELS = {
  siren: [
    'Siren',
    'Civil defense siren',
    'Police car (siren)',
    'Ambulance (siren)',
    'Fire engine, fire truck (siren)',
    'Emergency vehicle',
  ],
  // 자동차 + 이륜차 경적을 하나로 (classes.yaml과 같은 기준)
  horn: ['Vehicle horn, car horn, honking', 'Air horn, truck horn', 'Toot'],
  // 2차용 (classes.yaml에서 enabled: false인 동안은 쓰이지 않음)
  alarm: ['Smoke detector, smoke alarm', 'Fire alarm', 'Alarm'],
  knock_doorbell: ['Doorbell', 'Ding-dong', 'Knock'],
};

const LEVEL_BY_PRIORITY = { 1: 'urgent', 2: 'normal' };

// web/classes.json을 읽어 알림 대상만 고른다
// (enabled: true이고 priority가 1 이상이며, YAMNet 라벨이 정해진 클래스)
export async function loadTargets() {
  const res = await fetch('classes.json', { cache: 'no-cache' });
  if (!res.ok) throw new Error(`classes.json을 읽지 못했어요 (${res.status})`);
  const { classes } = await res.json();
  return classes
    .filter((c) => c.enabled && c.priority > 0 && YAMNET_LABELS[c.id])
    .map((c) => ({
      id: c.id,
      name: c.name_ko,
      priority: c.priority,
      level: LEVEL_BY_PRIORITY[c.priority] ?? 'normal',
      threshold: c.threshold ?? THRESHOLD, // classes.yaml에 threshold가 있으면 그 값, 없으면 기본값
      labels: YAMNET_LABELS[c.id],
    }));
}

// 상위 결과를 보여 줄 때 쓰는 한국어 이름 (없으면 영어 그대로)
const KO = {
  Speech: '말소리',
  'Child speech, kid speaking': '아이 말소리',
  Conversation: '대화',
  Music: '음악',
  Silence: '조용함',
  'Inside, small room': '실내 소리',
  'Inside, large room or hall': '넓은 실내 소리',
  Television: 'TV',
  Typing: '타자 소리',
  'Computer keyboard': '키보드',
  Clapping: '박수',
  'Hands': '손 소리',
  'Finger snapping': '손가락 튕기기',
  Laughter: '웃음소리',
  Dog: '개',
  Bark: '개 짖는 소리',
  Vehicle: '차량',
  Car: '자동차',
  Traffic: '교통 소음',
  'Traffic noise, roadway noise': '도로 소음',
  Engine: '엔진',
  Wind: '바람',
  Rain: '비',
  Water: '물소리',
  'Beep, bleep': '삐 소리',
  'Sine wave': '단일음',
  Tick: '똑딱 소리',
  'Alarm clock': '알람 시계',
  'Car alarm': '자동차 경보',
  Buzzer: '버저',
  Door: '문 소리',
  Siren: '사이렌',
  'Civil defense siren': '민방위 사이렌',
  'Police car (siren)': '경찰차 사이렌',
  'Ambulance (siren)': '구급차 사이렌',
  'Fire engine, fire truck (siren)': '소방차 사이렌',
  'Emergency vehicle': '긴급 차량',
  'Vehicle horn, car horn, honking': '자동차 경적',
  'Air horn, truck horn': '트럭 경적',
  Toot: '경적',
  'Smoke detector, smoke alarm': '화재감지기',
  'Fire alarm': '화재경보',
  Alarm: '경보음',
  Doorbell: '초인종',
  'Ding-dong': '딩동',
  Knock: '노크',
};

export function koName(label) {
  return KO[label] ?? label;
}

export async function loadClassifier() {
  const fileset = await FilesetResolver.forAudioTasks(WASM_BASE);
  return AudioClassifier.createFromOptions(fileset, {
    baseOptions: { modelAssetPath: MODEL_URL },
    maxResults: -1, // 521개 라벨 점수를 모두 받는다
  });
}

// samples: 약 1초 분량의 오디오, sampleRate: 그 샘플레이트, targets: loadTargets() 결과
export function analyze(classifier, samples, sampleRate, targets) {
  const results = classifier.classify(samples, sampleRate);

  // 입력이 여러 조각으로 나뉘어 분석되면, 라벨마다 가장 높은 점수를 쓴다
  const best = new Map();
  for (const result of results) {
    const categories = result.classifications?.[0]?.categories ?? [];
    for (const c of categories) {
      if ((best.get(c.categoryName) ?? 0) < c.score) best.set(c.categoryName, c.score);
    }
  }

  const top = [...best.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([label, score]) => ({ label, name: koName(label), score }));

  const scored = targets.map((t) => {
    let score = 0;
    let label = '';
    for (const l of t.labels) {
      const s = best.get(l) ?? 0;
      if (s > score) { score = s; label = l; }
    }
    return { ...t, score, label };
  });

  const hit =
    scored.filter((t) => t.score >= t.threshold).sort((a, b) => b.score - a.score)[0] ?? null;

  return { top, targets: scored, hit };
}
