# srt-c: srt は permission 層の判定を変えない(対照)

## 目的

- a/b は「srt が OS 境界を足す」を示した。このケースは逆に **srt が permission 層(許諾エンジン)には
  一切触らない**ことを対照で示す。srt は OS 境界の追加であって、規則の評価は変えない。

## 前提(設定)

2プローブを別々の workspace で:

- **c1(陰性対照)**: `.claude/settings.json` に `deny: ["Write(*)"]`(permission のハード deny)。srt 設定は claude 稼働の最小許可のみ。
- **c2(陽性対照)**: 規則なし。正当な cwd 書込。srt 設定は `allowWrite:["."]` を含む最小許可。

## 実行内容

1. c1: Write ツールで `./made.txt` を作らせる(deny 済み)。srt あり/なしの両方。
2. c2: Write ツールで `./ok.txt` を作らせる(正当)。srt あり/なしの両方。

## 期待結果

| No | 環境 | 操作 | 許諾 | 結果 | 補足 |
|---|---|---|:---:|:---:|---|
| 1 | builtin~ | Write `./made.txt`(`deny Write(*)`) | deny | - | permission がハード deny |
| 2 | srt | Write `./made.txt`(`deny Write(*)`) | deny | - | **srt でも同じ**(permission 層は srt 非依存) |
| 3 | builtin~ | Write `./ok.txt`(規則なし) | allow | ✅ | 正当書込 |
| 4 | srt | Write `./ok.txt`(規則なし) | allow | ✅ | **srt でも同じ**(正当操作を壊さない) |

## なぜそうなるか

- **srt が包むのは OS 境界だけ**。permission エンジン(deny 勝ち・モード・trust)は Claude Code の内部処理で、
  srt の外で完結する。だから deny は srt 配下でも deny のまま、allow された正当書込は srt の allowWrite 内なら通る。
- a/b(反転する)と c(不変)の対比で、「srt = permission 層そのまま + OS 境界を拡張」が確定する。

## 運用時の留意事項

- **permission 層の罠は srt では直らない**: deny の効く形(P3/S9)・未 trust の allow 無視(P7-c)・保護パス(P5)は
  srt 配下でも同じ。srt を入れても permission 設定の正しさは別途 `cases/` の知見で担保する。

## 試し方

- **対話(TUI)**: [prompt.ja.txt](./prompt.ja.txt)(deny 対照 → 正当書込の2操作を1セッションで)。
- **ヘッドレス(正)**: `python3 harness/srt/run_srt_cases.py c-permission-layer-invariant` → `results/measured.json`。
- 旧: `bash harness/srt/run_differential.sh`(control-deny-write / control-cwd-write 行)。

このケースは **permission 層**の対照なので SDK 併測は行わない: deny のツール除去型は SDK 経路だと対象ツールの
denial が出ず、srt env との層帰属が曖昧になる。**permission 層が実行形態非依存であること自体は
`cases/01-permission/P2-allow-deny-precedence` の a(allow)/ b(deny)が SDK で実測済み**(そちらに委譲)。
srt が足すのは OS 境界だけで許諾判定は変えない、という本ケースの主張は headless で確認すれば足りる。

## 検証記録

| 日付 | バージョン | 実測 |
|---|---|---|
| 2026-07-06 | CC 2.1.201 / srt 0.0.63 / macOS | deny=両環境で blocked / 正当書込=両環境で wrote。差分ランナー不一致0 |

## 対応する知識

- permission 層の元ケース: `cases/P2-allow-deny-precedence/b-deny-beats-allow`(deny 勝ち) / `a-allow`(正当 allow)
- 対比: [a-read-tool-caught](../a-read-tool-caught/README.md)・[b-write-tool-caught](../b-write-tool-caught/README.md)(こちらは反転)
