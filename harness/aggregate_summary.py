#!/usr/bin/env python3
"""
results/summary-<modality>.json を「ディスク上の per-case 実測結果から」再集計する。

なぜ要るか:
  run.py は「その 1 回の実行に含めたケースだけ」で summary を丸ごと上書きする。
  そのため部分実行のたびに summary が数件の断片に縮み、リポジトリ全体の現況を表さない。
  このスクリプトはモデルを一切呼ばず、各ケースの results/<modality>.json を読み集めて
  全ケース分の summary を作る（＝保存済み実測の忠実な集約）。

使い方:
  python3 harness/aggregate_summary.py            # headless と sdk 両方
  python3 harness/aggregate_summary.py headless   # 片方だけ

出力: results/summary-headless.json / results/summary-sdk.json
      末尾に集計統計を stdout へ表示。
"""
import json
import re
import sys
from pathlib import Path

_BUCKET_RE = re.compile(r"^\d\d-")


def _short_id(case_dir, base):
    """cases/<NN-bucket>/<GROUP>/<SUB> → '<GROUP>/<SUB>'(番号バケツ接頭辞を落とす)。"""
    parts = list(case_dir.relative_to(base).parts)
    if parts and _BUCKET_RE.match(parts[0]):
        parts = parts[1:]
    return "/".join(parts)

REPO = Path(__file__).resolve().parent.parent
CASES = REPO / "cases"
OUT = REPO / "results"


def collect(modality):
    entries = []
    for cj in sorted(CASES.glob("**/case.json")):
        rp = cj.parent / "results" / f"{modality}.json"
        if not rp.exists():
            continue
        try:
            entries.append(json.loads(rp.read_text()))
        except Exception as e:  # noqa: BLE001
            entries.append({"id": _short_id(cj.parent, CASES),
                            "modality": modality, "verdict": "PARSE_ERROR",
                            "error": str(e)})
    return entries


def stats(entries):
    p = f = n = 0
    fails = []
    for e in entries:
        m = e.get("match")
        if m is True:
            p += 1
        elif m is False:
            f += 1
            fails.append((e.get("id"), e.get("verdict")))
        else:
            n += 1
    return p, f, n, fails


def main():
    modalities = sys.argv[1:] or ["headless", "sdk"]
    OUT.mkdir(exist_ok=True)
    total_boxes = sum(1 for cj in CASES.glob("**/case.json")
                      if not (cj.parent / "results" / "headless.json").exists())
    total_cases = sum(1 for _ in CASES.glob("**/case.json"))
    total_groups = len({p.parent.parent.name for p in CASES.glob("**/case.json")})
    for mod in modalities:
        entries = collect(mod)
        (OUT / f"summary-{mod}.json").write_text(
            json.dumps(entries, indent=2, ensure_ascii=False) + "\n")
        p, f, n, fails = stats(entries)
        print(f"[{mod}] measured={len(entries)}  match=True:{p}  match=False:{f}  match=None:{n}")
        for cid, v in fails:
            print(f"    !! {str(v):<13} {cid}")
    print(f"\nrepo: groups={total_groups}  subcases={total_cases}  "
          f"headless未実測(箱)={total_boxes}")


if __name__ == "__main__":
    main()
