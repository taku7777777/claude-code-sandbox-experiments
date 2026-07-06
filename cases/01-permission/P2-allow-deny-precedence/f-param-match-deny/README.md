# P2-f: パラメータマッチ deny `Bash(run_in_background:true)` → その引数を付けた呼び出しだけ block

## 目的

- deny/ask 限定の **`Tool(param:value)` 構文**(パラメータマッチ)が実際に効くことを確認する
- 「**省略されたパラメータは不マッチ**」(docs)の対照を同一コマンドで取る:
  同じ `touch` が run_in_background の有無だけで deny / allow に分かれる

## 前提(設定)

```json
{
  "permissions": {
    "allow": ["Bash(*)"],
    "deny": ["Bash(run_in_background:true)"]
  }
}
```

- 広い allow に、パラメータ条件付きの deny を重ねる(P4-a の「広 allow + 狭 deny」のパラメータ版)

## 実行内容

1. Bash ツールを **`run_in_background: true` 付き**で呼び、`touch ./bg_proof.txt` を実行
2. 同じコマンドを**フォアグラウンド**(パラメータなし)で実行

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `touch`(run_in_background:true) | deny | - | **パラメータマッチで block**。`denials: ["Bash"]` 記録=ツールは見えたまま呼び出し時拒否 |
| 2 | Bash `touch`(パラメータなし) | allow | ✅ | **省略パラメータは不マッチ** → allow `Bash(*)` に落ちて通る |

## なぜそうなるか

- deny/ask は `Tool(param:value)` 構文を受け付ける(トップレベル・スカラーのパラメータのみ、`*` 可)。
  呼び出しの引数が条件に一致した場合だけマッチする。
- パラメータを**省略した**呼び出しはマッチしない(docs 明記)。「バックグラウンド実行だけ禁止」のような
  引数条件の禁止が 1 規則で書ける。
- bare/`Tool(*)` deny(P2-b)と違い**コンテキスト除去は起きない**。ツールは見えたままで、
  マッチする呼び出しだけが `permission_denials` に記録されて止まる(P4-a のスコープ付き deny と同じ現れ方)。

## 運用時の留意事項

- 対象にできるのは**ツール定義のトップレベル・スカラーのパラメータ**だけ。
  `command` / `file_path` / `path` / `url` などの中身は対象外で、書いても**無言で無効**(→ P2-g)。
- コマンド内容で絞りたいときはこの構文ではなく `Bash(touch *)` 形式(→ P4)を使う。

## 試し方(本リポジトリでの実測)

```bash
python3 harness/run.py P2-allow-deny-precedence/f-param-match-deny
python3 harness/run.py -m sdk P2-allow-deny-precedence/f-param-match-deny
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(2プローブとも一致)/ sdk |

## 対応する知識

- グループ [P2 README](../README.md)
- 関連: P2-g(対象外パラメータは無言無視)/ P4-a(コマンドプレフィックスによる「広 allow + 狭 deny」)/ P2-b(bare deny は除去型)
