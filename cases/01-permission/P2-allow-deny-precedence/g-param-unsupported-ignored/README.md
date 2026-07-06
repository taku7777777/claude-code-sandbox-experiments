# P2-g: `deny: ["Bash(command:touch *)"]` は**無言で無効** → 「禁止したはず」の touch が通る

## 目的

- `Tool(param:value)` 構文の**対象外パラメータ**(`command` 等)を使った deny 規則が
  マッチせず無視されることを実測する(P3 の「マッチしない規則の無言無効化」と同型の地雷)
- あわせて docs 記載の**起動時警告**が実際に出ることを確認する

## 前提(設定)

```json
{
  "permissions": {
    "allow": ["Bash(*)"],
    "deny": ["Bash(command:touch *)"]
  }
}
```

- `command:` はコマンド内容を raw string として指すパラメータ名で、パラメータマッチの**対象外**

## 実行内容

1. Bash ツールで `touch ./PROOF.txt` を実行(deny が効いていれば止まるはずの操作)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `touch ./PROOF.txt` | allow | ✅ | **deny は無視され、allow `Bash(*)` で素通り** |

## なぜそうなるか

- パラメータマッチの対象は**トップレベル・スカラー**のツールパラメータのみ(→ P2-f)。
  `command` / `file_path` / `path` / `url` のような中身系パラメータは対象外で、規則ごと無視される。
- 起動時に stderr へ警告が出る(v2.1.201 実測・原文):
  > Permission deny rule "Bash(command:touch *)" targets command as a raw string and will not match — use Bash(…) for Bash's own matcher.
- ただし headless の `--output-format json` 運用では stderr を見ないことが多く、
  **警告は容易に見落とされる**。防いだつもりの deny が無効のまま運用に乗る。

## 運用時の留意事項

- コマンド内容で絞る正しい形は **`Bash(touch *)`**(Bash 専用のプレフィックスマッチャ → P4)。
  `Bash(command:...)` と書いた deny は**保護になっていない**。
- deny を書いたら必ず空撃ちで確認する(P3 の教訓と同じ)。起動時警告を CI で拾うなら stderr を監視する。

## 試し方(本リポジトリでの実測)

```bash
python3 harness/run.py P2-allow-deny-precedence/g-param-unsupported-ignored
python3 harness/run.py -m sdk P2-allow-deny-precedence/g-param-unsupported-ignored
# 起動時警告の確認(stderr):
cd cases/P2-allow-deny-precedence/g-param-unsupported-ignored && claude -p "ok" 2>&1 >/dev/null | head -1
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(一致・PROOF.txt 生成=deny 無効)/ sdk / 起動時警告を stderr で確認 |

## 対応する知識

- グループ [P2 README](../README.md)
- 関連: P2-f(効くパラメータマッチ)/ P3(マッチしない規則は無言で no-op)/ P4(コマンド内容の正しい絞り方)
