// 알림 판단: 0.5초마다 들어오는 클래스 점수를 보고 "확정"과 "알림 발생"을 정한다.
//
// - 최근 WINDOW_COUNT번 중 REQUIRED번 이상 기준 점수를 넘으면 확정
//   (YAMNet은 같은 사이렌도 구간마다 '오페라'로 착각하는 등 흔들리므로 한 번 튄 점수로는 알리지 않는다)
// - 확정되면 알림(진동·화면 깜빡임)을 보내되, 같은 소리는 COOLDOWN_MS 동안 다시 알리지 않는다
// - 화면에는 마지막 확정 후 HOLD_MS 동안 그 소리를 계속 보여 준다 (깜빡임 방지)
//
// 화면·브라우저와 무관한 순수 로직이라 단독으로 테스트할 수 있다.

export const WINDOW_COUNT = 3;   // 최근 3구간 (0.5초 간격 → 약 1.5초)
export const REQUIRED = 2;       // 그중 2구간 이상
export const COOLDOWN_MS = 5000; // 같은 소리 재알림 간격
export const HOLD_MS = 2000;     // 확정된 소리를 화면에 유지하는 시간

export function createAlertEngine({
  windowCount = WINDOW_COUNT,
  required = REQUIRED,
  cooldownMs = COOLDOWN_MS,
  holdMs = HOLD_MS,
} = {}) {
  const recent = new Map();     // id → [true/false, ...] 최근 windowCount개
  const lastFiredAt = new Map(); // id → 마지막 알림 시각
  let shown = null;             // { target, score, at }

  return {
    // scored: [{ id, name, level, priority, score, threshold }, ...]  (classifier.analyze의 targets)
    update(scored, now) {
      let confirmed = null;
      let pending = null;

      for (const t of scored) {
        const passed = t.score >= t.threshold;
        const list = recent.get(t.id) ?? [];
        list.push(passed);
        if (list.length > windowCount) list.shift();
        recent.set(t.id, list);

        const hits = list.filter(Boolean).length;
        if (hits >= required) {
          // 여러 소리가 동시에 확정되면 우선순위(숫자가 작을수록 긴급) → 점수 순
          if (!confirmed || t.priority < confirmed.priority ||
              (t.priority === confirmed.priority && t.score > confirmed.score)) {
            confirmed = t;
          }
        } else if (hits >= 1 && (!pending || t.score > pending.score)) {
          pending = t; // 최근 구간에서 한 번 넘었지만 아직 확정 전
        }
      }

      let fire = false;
      if (confirmed) {
        const last = lastFiredAt.get(confirmed.id) ?? -Infinity;
        if (now - last >= cooldownMs) {
          fire = true;
          lastFiredAt.set(confirmed.id, now);
        }
        shown = { target: confirmed, at: now };
      }

      const showing = shown && now - shown.at < holdMs ? shown.target : null;
      return { confirmed, fire, showing, pending: showing ? null : pending };
    },

    reset() {
      recent.clear();
      lastFiredAt.clear();
      shown = null;
    },
  };
}
