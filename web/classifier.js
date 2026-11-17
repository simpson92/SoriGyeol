// 소리 종류 분류: MediaPipe Audio Classifier + YAMNet (브라우저 안에서 실행)
// YAMNet은 AudioSet 521개 라벨 중 어떤 소리인지 점수를 낸다.
// 우리는 그중 감지할 4종에 해당하는 라벨만 묶어서 판단한다.

import {
  AudioClassifier,
  FilesetResolver,
} from 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-audio@1.2.3/audio_bundle.mjs';

const WASM_BASE = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-audio@1.2.3/wasm';
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/audio_classifier/yamnet/float32/1/yamnet.tflite';

// 이 점수 이상이면 '감지'로 본다. 2주차에 Python으로 평가한 뒤 조정한다.
export const THRESHOLD = 0.3;

// 감지할 소리 4종 (configs/targets.json과 같은 내용을 유지한다)
// labels: YAMNet 라벨 이름 (yamnet_class_map.csv 기준)
export const TARGETS = [
  {
    id: 'siren',
    name: '사이렌',
    level: 'urgent',
    labels: [
      'Siren',
      'Civil defense siren',
      'Police car (siren)',
      'Ambulance (siren)',
      'Fire engine, fire truck (siren)',
      'Emergency vehicle',
    ],
  },
  {
    id: 'car_horn',
    name: '자동차 경적',
    level: 'urgent',
    labels: ['Vehicle horn, car horn, honking', 'Air horn, truck horn', 'Toot'],
  },
  {
    id: 'fire_alarm',
    name: '화재경보',
    level: 'urgent',
    // 'Alarm'은 범위가 넓어 오알림이 생길 수 있지만, 놓치지 않는 쪽을 우선해 포함한다
    labels: ['Smoke detector, smoke alarm', 'Fire alarm', 'Alarm'],
  },
  {
    id: 'doorbell',
    name: '초인종·노크',
    level: 'normal',
    labels: ['Doorbell', 'Ding-dong', 'Knock'],
  },
];

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

// samples: 약 1초 분량의 오디오, sampleRate: 그 샘플레이트
export function analyze(classifier, samples, sampleRate) {
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

  const targets = TARGETS.map((t) => {
    let score = 0;
    let label = '';
    for (const l of t.labels) {
      const s = best.get(l) ?? 0;
      if (s > score) { score = s; label = l; }
    }
    return { ...t, score, label };
  });

  const hit =
    targets.filter((t) => t.score >= THRESHOLD).sort((a, b) => b.score - a.score)[0] ?? null;

  return { top, targets, hit };
}
