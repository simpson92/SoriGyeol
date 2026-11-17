// 방향 실험 1단계: 이 기기·브라우저가 마이크를 2채널로 주는지 확인한다.
// - 채널별 소리 크기와 차이 (크기 차이 → 어느 쪽 마이크에 가까운지)
// - 두 채널의 상관 (1.00에 가까우면 사실상 같은 소리 = 모노를 복사한 것)
// - 도착 시간 차이 (교차상관이 가장 큰 지연. 방향 추정의 핵심 값)

// 폰 마이크 간격은 보통 15cm 안팎 → 소리가 두 마이크에 닿는 시간 차이는 최대 약 0.5ms
const MAX_DELAY_SEC = 0.0006;

function rmsDb(buf) {
  let sum = 0;
  for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
  const rms = Math.sqrt(sum / buf.length);
  return rms > 0 ? 20 * Math.log10(rms) : -Infinity;
}

// lag만큼 b를 밀었을 때 a와 얼마나 닮았는지 (정규화된 상관, -1 ~ 1)
function correlation(a, b, lag) {
  let sab = 0, saa = 0, sbb = 0;
  const n = a.length;
  const start = Math.max(0, -lag);
  const end = Math.min(n, n - lag);
  for (let i = start; i < end; i++) {
    const x = a[i];
    const y = b[i + lag];
    sab += x * y;
    saa += x * x;
    sbb += y * y;
  }
  const denom = Math.sqrt(saa * sbb);
  return denom > 0 ? sab / denom : 0;
}

export function createStereoProbe(audioCtx, source) {
  const splitter = audioCtx.createChannelSplitter(2);
  const left = audioCtx.createAnalyser();
  const right = audioCtx.createAnalyser();
  for (const a of [left, right]) {
    a.fftSize = 2048;
    a.smoothingTimeConstant = 0;
  }
  source.connect(splitter);
  splitter.connect(left, 0);
  splitter.connect(right, 1); // 모노 입력이면 이 채널은 무음이 된다

  const bufL = new Float32Array(left.fftSize);
  const bufR = new Float32Array(right.fftSize);
  const maxLag = Math.ceil(audioCtx.sampleRate * MAX_DELAY_SEC);

  return {
    read() {
      left.getFloatTimeDomainData(bufL);
      right.getFloatTimeDomainData(bufR);

      const dbL = rmsDb(bufL);
      const dbR = rmsDb(bufR);

      // 도착 시간 차이: 지연을 -maxLag ~ +maxLag로 바꿔 가며 가장 닮은 지점을 찾는다
      let bestLag = 0;
      let bestCorr = -Infinity;
      for (let lag = -maxLag; lag <= maxLag; lag++) {
        const c = correlation(bufL, bufR, lag);
        if (c > bestCorr) { bestCorr = c; bestLag = lag; }
      }

      return {
        dbL,
        dbR,
        diffDb: Number.isFinite(dbL) && Number.isFinite(dbR) ? dbL - dbR : null,
        corr0: correlation(bufL, bufR, 0),
        bestLag,                                      // 양수: 오른쪽 채널이 늦게 도착
        bestLagUs: (bestLag / audioCtx.sampleRate) * 1e6,
        bestCorr,
      };
    },
    disconnect() {
      splitter.disconnect();
    },
  };
}

// 측정값을 사람이 읽을 판정으로 바꾼다
export function judgeStereo(channelCount, r) {
  if (!Number.isFinite(r.dbR)) {
    return { key: 'mono', text: '1채널(모노)로 들어와요. 이 기기·브라우저에서는 마이크만으로 방향을 추정하기 어려워요.' };
  }
  if (r.corr0 > 0.999 && Math.abs(r.diffDb ?? 0) < 0.1) {
    return { key: 'copy', text: '2채널이지만 두 채널이 똑같아요(모노를 복사한 것). 방향 정보가 없어요.' };
  }
  return { key: 'stereo', text: '2채널이 서로 다른 소리를 담고 있어요. 방향 실험을 해 볼 수 있는 기기예요.' };
}