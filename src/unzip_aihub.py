"""AI Hub zip 파일 일괄 압축 해제 (한글 파일 이름 깨짐 방지).

AI Hub zip은 파일 이름이 CP949(윈도우 한글)로 저장된 경우가 많아서
그냥 unzip으로 풀면 이름이 깨진다. 이 스크립트는 이름을 올바르게 복원해서 푼다.

사용법:
    python src/unzip_aihub.py data/raw/aihub_urban_sound            # 풀기만
    python src/unzip_aihub.py data/raw/aihub_urban_sound --delete   # 풀고 zip 삭제

- 각 zip은 같은 위치에 zip 이름과 같은 폴더로 풀린다.
    예) 라벨링데이터/TL_1.교통소음.zip → 라벨링데이터/TL_1.교통소음/
- 다 풀린 zip은 폴더 안에 .unzipped 표시 파일을 남겨서, 중간에 끊겨도 다시 실행하면 이어서 진행한다.
"""
import argparse
import shutil
import zipfile
from pathlib import Path

from tqdm import tqdm

DONE_MARK = ".unzipped"


def fix_name(info: zipfile.ZipInfo) -> str:
    """CP949로 저장된 한글 이름을 올바르게 복원한다."""
    name = info.filename
    if info.flag_bits & 0x800:  # 이미 UTF-8로 저장된 이름
        return name
    try:
        return name.encode("cp437").decode("cp949")
    except UnicodeError:
        return name


def extract(zip_path: Path) -> int:
    out_dir = zip_path.with_suffix("")
    if (out_dir / DONE_MARK).exists():
        print(f"[건너뜀] 이미 풀림: {zip_path.name}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    root = out_dir.resolve()
    count = 0
    with zipfile.ZipFile(zip_path) as zf:
        members = zf.infolist()
        for info in tqdm(members, desc=zip_path.name, unit="file"):
            target = (out_dir / fix_name(info)).resolve()
            if not target.is_relative_to(root):  # 폴더 밖으로 나가는 경로 차단
                raise ValueError(f"잘못된 경로: {info.filename}")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)
            count += 1

    (out_dir / DONE_MARK).touch()
    return count


def main():
    parser = argparse.ArgumentParser(description="AI Hub zip 일괄 압축 해제")
    parser.add_argument("root", type=Path, help="zip 파일들이 들어 있는 최상위 폴더")
    parser.add_argument("--delete", action="store_true", help="다 풀린 zip 파일 삭제")
    args = parser.parse_args()

    zips = sorted(args.root.rglob("*.zip"))
    if not zips:
        print("zip 파일이 없습니다.")
        return

    print(f"zip {len(zips)}개 발견")
    for z in zips:
        n = extract(z)
        if n:
            print(f"[완료] {z.name}: 파일 {n}개")
        if args.delete:
            z.unlink()
            print(f"[삭제] {z.name}")

    print("모두 완료")


if __name__ == "__main__":
    main()