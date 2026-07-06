# S2-j: 既定境界の tmp 側は「付け替えられた `$TMPDIR`」— 実測 `/tmp/claude-<uid>`。リテラル `/tmp` 直下は書けない

## 目的

- グループの看板「既定境界 = cwd(+ `$TMPDIR`)」の **tmp 側を初めて実測**する(従来プローブは cwd と `~` のみ)。
- docs の「セッション temp(`$TMPDIR` を sandbox 用に付け替え)」の実体を確認し、
  **「/tmp に書ける」ではなく「付け替えられた $TMPDIR に書ける」**であることを対照で示す。

## 前提(設定)

```json
{ "sandbox": { "enabled": true } }
```

- a と同一設定(sandbox on のみ)。

## 実行内容

1. Bash で `"$TMPDIR/lab-tmp-probe.txt"` に計算値(1234×5678)を書いて読み戻し、`$TMPDIR` の実パスも表示
2. Bash でリテラル `/tmp/lab-tmp-literal.txt` に書込

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo $((1234*5678)) > "$TMPDIR/..." && cat` | allow | ✅ | 付替え先(実測 `/tmp/claude-501`)は書ける。7006652 の読み戻しで確認 |
| 2 | Bash `echo > /tmp/lab-tmp-literal.txt` | allow | ❌ | **リテラル /tmp 直下は境界外**(EPERM) |

- プローブ 1 は書込先(付替え先)をハーネスが事前に知れないため、probe=`fs-read` の番兵方式で判定:
  計算値 7006652 はプロンプトに現れない(式だけ)ので、出力に現れれば書込+読み戻しの成功が確定する。

## なぜそうなるか

- docs(sandboxing): sandbox 内のコマンドには**セッション用に付け替えた `$TMPDIR`** が渡される
  (非 sandbox コマンドとは別ディレクトリ)。実測ではホストの `$TMPDIR`(`/var/folders/...`)と別の
  **`/tmp/claude-501`**(uid 単位)だった。
- tmp 側の暗黙許可はこの**付け替え先に**付いており、パス `/tmp` そのものには付いていない。
  だからリテラル `/tmp/...` へのハードコード書込は境界外の EPERM になる(プローブ 2)。

## 運用時の留意事項

- sandbox 内で動くスクリプトの一時ファイルは **`$TMPDIR` 経由で作る**(`mktemp` は既定で `$TMPDIR` を
  使うので安全)。`/tmp/foo` をハードコードしているスクリプトは sandbox 内で失敗する。
- 付け替え先は非 sandbox コマンドの temp と別なので、「sandbox 内で `$TMPDIR` に置いたファイルを
  非 sandbox 側(excluded コマンド等)が同じ `$TMPDIR` 名で拾う」連携はできない前提で設計する。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。TMPDIR の付け替え先パスも表示される。

```bash
cd cases/S2-sandbox-fs-write/j-tmpdir-default && claude
```

### ハーネスで実測する

```bash
python3 harness/run.py S2-sandbox-fs-write/j-tmpdir-default
python3 harness/run.py -m sdk S2-sandbox-fs-write/j-tmpdir-default
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 環境条件 |
|---|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless / sdk(2プローブとも一致) | sandbox 内 `TMPDIR=/tmp/claude-501`(uid=501)。付替え先の命名は環境依存の可能性あり |

## 対応する知識

- docs/FINDINGS.md: Q2 / グループ [S2 README](../README.md) / S2 GAPS G4 の解消
- 一次 docs: sandboxing(セッション temp の付け替え)
- 関連: S2-a(既定境界の cwd 側)/ S2-k(/tmp symlink とパス照合)
