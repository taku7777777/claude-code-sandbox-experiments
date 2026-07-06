# S2-k: `allowWrite` の絶対パスは **symlink 解決して照合される** — `/tmp` 表記でも `/private/tmp` 表記でも効く

## 目的

- sandbox FS write のパス照合が **symlink 解決済みの実パス**で行われるかを実測する
  (S6-f では unix **socket** のパスが非解決で `/tmp` 表記が不一致だった — FS 側への外挿は未実測だった)。
- S2 で未使用だった **`/` 絶対プレフィックス**の動作確認も兼ねる(従来ケースは `~/` のみ)。

## 前提(設定)

```json
{
  "sandbox": {
    "enabled": true,
    "filesystem": {
      "allowWrite": ["/private/tmp/lab-abs-resolved", "/tmp/lab-abs-literal"]
    }
  }
}
```

- macOS の `/tmp` は `/private/tmp` への symlink。**解決済み表記と symlink 表記のエントリを 1 つずつ**入れ、
  書込はどちらも `/tmp/...` 表記で行う。

## 実行内容

1. Bash で `/tmp/lab-abs-resolved/f.txt` に書込(設定エントリは `/private/tmp/...` 表記)
2. Bash で `/tmp/lab-abs-literal/g.txt` に書込(設定エントリは `/tmp/...` 表記)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo > /tmp/lab-abs-resolved/f.txt` | allow | ✅ | 書込先が解決され(`/private/tmp/...`)、解決済み表記のエントリにマッチ |
| 2 | Bash `echo > /tmp/lab-abs-literal/g.txt` | allow | ✅ | **symlink 表記のエントリも解決されて効く** |

## なぜそうなるか

- 両プローブが通る = **設定側・書込先側の両方が解決済み実パスに正規化されてから照合される**。
  表記揺れ(`/tmp` vs `/private/tmp`)で穴が開いたり閉じたりしない。
- **socket とは非対称**: S6-f では `allowUnixSockets` の `/tmp/...` 表記が不一致で `/private/tmp/...`
  表記が必要だった。「sandbox のパスは symlink 非解決」という一般化は FS write には当てはまらない
  (COVERAGE の外挿記述を本ケースで訂正)。

## 運用時の留意事項

- FS の `allowWrite`/`denyWrite` は `/tmp` 表記のままで書いてよい(macOS)。
  一方 **unix socket のパスは解決済み表記(`/private/tmp/...`)が必要**(S6-f)— 機能ごとに確かめる。
- 逆向きの含意: `denyWrite` も解決後の実パスで効くはずなので、「symlink 経由の別表記で deny を迂回」は
  この層では期待できない(deny 側の直接実測は未実施)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。

```bash
cd cases/S2-sandbox-fs-write/k-abs-path-resolution && claude
```

### ハーネスで実測する

```bash
python3 harness/run.py S2-sandbox-fs-write/k-abs-path-resolution
python3 harness/run.py -m sdk S2-sandbox-fs-write/k-abs-path-resolution
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless / sdk(2プローブとも一致) |

## 対応する知識

- docs/FINDINGS.md: Q2 / グループ [S2 README](../README.md) / S2 GAPS G5 の解消(socket 実測からの外挿を FS で訂正)
- 関連: S6-f(unix socket は**非解決** = 非対称の相手)/ S2-j(/tmp 直下自体は既定境界外)
