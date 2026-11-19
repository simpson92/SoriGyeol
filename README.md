# 소리결 (SoriGyeol)

청각장애인·난청인을 위한 주변 소리 시각화·방향 알림 AI

> 🚧 진행 중인 프로젝트입니다.

## 데이터 출처 및 라이선스

이 레포에는 **소리 파일과 라벨 파일을 포함하지 않습니다.** 각 데이터셋의 이용 조건에 따라 직접 받아야 하며, 받는 방법은 [`docs/data-download.md`](docs/data-download.md)에 있습니다.

### AI Hub · 도시 소리 데이터 (한국)

- 링크: [aihub.or.kr · 도시 소리 데이터](https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=585) (재난안전환경 · 오디오 · 2021년 구축)
- 이 프로젝트에서의 사용: 교통소음(차량경적, 이륜차경적, 차량사이렌 등) 소리를 1차 학습·평가에 사용. AI Hub Validation 전체를 **한국 테스트셋**으로 사용

> 이 연구는 과학기술정보통신부의 재원으로 한국지능정보사회진흥원의 지원을 받아 구축된 "도시 소리 데이터"를 활용하여 수행된 연구입니다. 본 연구에 활용된 데이터는 AI 허브(aihub.or.kr)에서 다운로드 받으실 수 있습니다.

- AI 허브 이용정책에 따라 데이터를 다른 사람에게 복사·전달하지 않습니다. 필요한 경우 AI 허브에서 직접 신청해 주세요.
- 이 데이터로 학습한 모델과 결과물에도 위 출처를 밝힙니다.

### ESC-50 (해외)

- K. J. Piczak, "ESC: Dataset for Environmental Sound Classification," *Proceedings of the 23rd ACM International Conference on Multimedia*, 2015.
- 라이선스: [CC BY-NC 3.0](https://creativecommons.org/licenses/by-nc/3.0/) (비상업적 이용)
- 원본: [github.com/karolpiczak/ESC-50](https://github.com/karolpiczak/ESC-50)

### UrbanSound8K (해외)

- J. Salamon, C. Jacoby and J. P. Bello, "A Dataset and Taxonomy for Urban Sound Research," *22nd ACM International Conference on Multimedia (ACM-MM'14)*, Orlando, FL, USA, 2014.
- 라이선스: [CC BY-NC 3.0](https://creativecommons.org/licenses/by-nc/3.0/) (비상업적 이용)
- 원본: [Zenodo](https://zenodo.org/records/1203745)

### FSD50K (해외, 라벨 파일만 사용)

- E. Fonseca, X. Favory, J. Pons, F. Font and X. Serra, "FSD50K: An Open Dataset of Human-Labeled Sound Events," *IEEE/ACM Transactions on Audio, Speech, and Language Processing*, vol. 30, pp. 829–852, 2022.
- 이 프로젝트에서의 사용: 정답 라벨 파일(`FSD50K.ground_truth`)만 받아 클래스 구성을 검토. 소리 파일은 사용하지 않음
- 원본: [Zenodo](https://zenodo.org/records/4060432) (소리 파일은 클립마다 Creative Commons 라이선스가 다름)

### 이용 조건 요약

| 데이터 | 상업적 이용 | 출처 표시 | 재배포 |
|---|---|---|---|
| AI Hub 도시 소리 | 이용정책 범위 내 | **필수** (위 문구) | 불가 (각자 신청) |
| ESC-50 | 불가 | 필수 | 비상업 목적이면 가능 |
| UrbanSound8K | 불가 | 필수 | 비상업 목적이면 가능 |
| FSD50K | 클립별 라이선스 확인 | 필수 | 클립별 라이선스 확인 |

이 프로젝트는 **비상업적 포트폴리오 프로젝트**입니다. ESC-50·UrbanSound8K로 학습한 모델을 상업적으로 쓰려면 별도 검토가 필요합니다.

ESC-50, UrbanSound8K, FSD50K는 모두 [Freesound](https://freesound.org)에서 모은 녹음이라 같은 녹음이 여러 데이터셋에 들어 있을 수 있습니다. 학습·검증·테스트를 나눌 때 원본 녹음 ID로 묶어 같은 녹음이 나뉘지 않게 했습니다 (`src/make_split.py`).

## 사용한 모델 · 라이브러리

| 이름 | 용도 | 라이선스 |
|---|---|---|
| [YAMNet](https://github.com/tensorflow/models/tree/master/research/audioset/yamnet) (Google) | 브라우저에서 소리 종류 분류 (AudioSet 521개 라벨) | Apache 2.0 |
| [MediaPipe Audio Classifier](https://developers.google.com/edge/mediapipe/solutions/audio/audio_classifier/web_js) (`@mediapipe/tasks-audio`) | 웹에서 YAMNet 실행 | Apache 2.0 |