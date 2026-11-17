// 마이크 소리를 2048 샘플씩 모아 메인 화면 쪽으로 보낸다.
// (AudioWorklet은 오디오 전용 스레드에서 돌아서 화면이 바빠도 소리가 끊기지 않는다)

const CHUNK = 2048;

class CaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buffer = new Float32Array(CHUNK);
    this.filled = 0;
  }

  process(inputs) {
    const channel = inputs[0]?.[0];
    if (channel) {
      let offset = 0;
      while (offset < channel.length) {
        const n = Math.min(CHUNK - this.filled, channel.length - offset);
        this.buffer.set(channel.subarray(offset, offset + n), this.filled);
        this.filled += n;
        offset += n;
        if (this.filled === CHUNK) {
          this.port.postMessage(this.buffer.slice(0));
          this.filled = 0;
        }
      }
    }
    return true; // 계속 동작
  }
}

registerProcessor('capture-processor', CaptureProcessor);
