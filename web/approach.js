// 가까워지는 중 / 멀어지는 중 판단 (11-19 의논 ④)
//
// 소리는 가까워지면 커지고 멀어지면 작아진다. 그래서 사이렌·경적이 확정돼 화면에 보이는 동안
// 최근 WINDOW_SEC초 소리 크기(dBFS)의 기울기(dB/초)를 직선 맞춤으로 구해 판단한다.
//
// 표시 시작 (엄격하게)
// - 기울기가 UP_SLOPE 이상인 판단이 UP_COUNT번 연속 → '가까워지는 중'
// - 기울기가 DOWN_SLOPE 이하인 판단이 DOWN_COUNT번 연속 → '멀어지는 중'
//   (다가오는 차를 '멀어짐'으로 잘못 알리는 게 더 위험해서 멀어짐을 더 엄격하게 본다)
// 표시 유지 (느슨하게, 11-20 실제 사이렌 시험에서 '너무 잠깐 뜬다' → 추가)
// - 한번 뜨면 기울기가 같은 방향(KEEP_UP 이상 / KEEP_DOWN 이하)인 동안 유지하고,
//   벗어난 판단이 RELEASE_COUNT번 연속일 때만 내린다. 반대 방향 시작 조건을 채우면 바로 바뀐다
// - 사이렌 점수가 잠깐 기준 아래로 내려가 확정이 끊겨도, GAP_MS 안에 같은 소리가 다시 확정되면 이어서 본다
// 이 판단은 표시만 더할 뿐, 알림을 줄이거나 끄지 않는다.
//
// 소리가 갑자기 시작되는 순간(배경 → 사이렌)의 크기 점프를 '가까워짐'으로 착각하지 않도록,
// 기울기는 그 소리가 확정된 뒤의 측정값만으로 계산한다. 그래서 표시는 확정 후 약 2초 뒤부터 나온다.
//
// 출발값 근거: 거리가 절반이 되면 약 6dB 커진다. 시속 50km 구급차가 50m 앞에서 다가오면 약 +2.4dB/초.
// 폰을 주머니에 넣거나 걸으면서 방향을 바꿔도 크기가 변하므로 실제 테스트로 조정한다.
//
// 화면·브라우저와 무관한 순수 로직이라 단독으로 테스트할 수 있다.

export const WINDOW_SEC = 3;      // 기울기를 볼 최근 시간 (사이렌 굴곡이 섞여도 흔들리지 않게)
export const MIN_SPAN_SEC = 1.5;  // 데이터가 이만큼은 쌓여야 판단
export const UP_SLOPE = 1.5;      // dB/초, 시작
export const UP_COUNT = 2;
export const DOWN_SLOPE = -3;     // dB/초, 시작
export const DOWN_COUNT = 3;
export const KEEP_UP = 0.5;       // dB/초, 유지
export const KEEP_DOWN = -1;      // dB/초, 유지
export const RELEASE_COUNT = 3;   // 유지 조건을 벗어난 판단이 이만큼 연속이면 내림 (0.5초 간격 → 1.5초)
export const GAP_MS = 3000;       // 확정이 이 시간 안에 다시 이어지면 같은 소리로 본다
export const FLOOR_DB = -80;      // 무음은 이 값으로 맞춘다

export const TREND_TEXT = { approach: '가까워지는 중', recede: '멀어지는 중' };

export function createApproachTracker({
  windowSec = WINDOW_SEC,
  minSpanSec = MIN_SPAN_SEC,
  upSlope = UP_SLOPE,
  upCount = UP_COUNT,
  downSlope = DOWN_SLOPE,
  downCount = DOWN_COUNT,
  keepUp = KEEP_UP,
  keepDown = KEEP_DOWN,
  releaseCount = RELEASE_COUNT,
  gapMs = GAP_MS,
  floorDb = FLOOR_DB,
} = {}) {
  let points = [];         // [{ t: ms, db }]
  let targetId = null;
  let startAt = -Infinity; // 지금 소리가 확정된 시각. 이 뒤의 측정값만 쓴다
  let lostAt = null;       // 확정이 끊긴 시각
  let up = 0;
  let down = 0;
  let off = 0;             // 유지 조건을 벗어난 연속 횟수
  let state = null;        // 'approach' | 'recede' | null

  const lastT = () => (points.length ? points[points.length - 1].t : 0);

  function clear() {
    targetId = null; startAt = -Infinity; lostAt = null;
    up = 0; down = 0; off = 0; state = null;
  }

  // 확정 뒤의 점들로 직선을 맞춰 기울기(dB/초)를 구한다
  function slope() {
    const use = points.filter((p) => p.t >= startAt);
    if (use.length < 3) return null;
    const t0 = use[0].t;
    const span = (use[use.length - 1].t - t0) / 1000;
    if (span < minSpanSec) return null;
    let sx = 0, sy = 0, sxx = 0, sxy = 0;
    for (const p of use) {
      const x = (p.t - t0) / 1000;
      sx += x; sy += p.db; sxx += x * x; sxy += x * p.db;
    }
    const n = use.length;
    const den = n * sxx - sx * sx;
    return den > 0 ? (n * sxy - sx * sy) / den : null;
  }

  const view = (s) => ({ state, slope: s, up, down, off });

  return {
    // 소리 크기 측정값을 매 프레임 넣는다
    push(db, t) {
      points.push({ t, db: Number.isFinite(db) ? Math.max(db, floorDb) : floorDb });
      const from = t - windowSec * 1000;
      while (points.length && points[0].t < from) points.shift();
    },

    // 분류할 때마다(0.5초) 부른다. id = 지금 화면에 보이는 확정 소리 (없으면 null)
    judge(id) {
      const now = lastT();
      if (!id) {
        // 잠깐 끊긴 건 기다려 주고, 오래 끊기면 처음부터
        if (targetId && lostAt === null) lostAt = now;
        if (targetId && now - lostAt > gapMs) clear();
        return { state: null, slope: null, up, down, off };
      }
      if (id !== targetId) {
        clear();
        targetId = id;
        startAt = now;
      }
      lostAt = null;

      const s = slope();
      if (s === null) return view(s);

      // 시작 조건 카운트
      if (s >= upSlope) { up += 1; down = 0; }
      else if (s <= downSlope) { down += 1; up = 0; }
      else { up = 0; down = 0; }

      if (up >= upCount) { state = 'approach'; off = 0; }
      else if (down >= downCount) { state = 'recede'; off = 0; }
      else if (state) {
        const keeping = state === 'approach' ? s >= keepUp : s <= keepDown;
        off = keeping ? 0 : off + 1;
        if (off >= releaseCount) { state = null; off = 0; }
      }
      return view(s);
    },

    reset() {
      points = [];
      clear();
    },
  };
}
