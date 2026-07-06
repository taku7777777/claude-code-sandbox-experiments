# P1-d: dontAsk モード + allow なし → ask せず即 deny(完全非対話)

## 目的

- dontAsk が「allow に登録されていないツールを ask せず即 deny する」ことを確認する(完全非対話 CI 向け)
- その deny がパス・ツールによらず一様であることを対比で示す

## 前提(設定)

```json
{}
```

- settings.json は空(allow 規則なし)。挙動を変えているのは CLI フラグ `--permission-mode dontAsk` のみ
- P1-a と同一プローブ・同一設定で、差分はモードだけ

## 実行内容

1. Write でケースディレクトリ直下にファイルを作成
2. Write でホームディレクトリ(cwd 外)にファイルを作成
3. Write でケース内のサブディレクトリにファイルを作成
4. Edit で既存ファイル(cwd 内)の文字列を置換

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(cwd 内) | deny | - | - |
| 2 | Write `~/p1d-proof.txt`(cwd 外) | deny | - | - |
| 3 | Write `./sub/proof.txt`(サブdir) | deny | - | - |
| 4 | Edit `./note.txt`(既存ファイル) | deny | - | - |

- 結果 `-` = deny なので実行に至らない(承認して通す余地がそもそもない)。
- P1-a(default)と最終結果は同じ「書けない」だが、**許諾列が違う**(ask vs deny)。

## なぜそうなるか

- **dontAsk は `permissions.allow` で事前承認されていないツールを、プロンプトを出さず即 deny する。**
- default(ask=承認待ち)と違い、承認という概念自体が発生しない。「確実に非対話」にしたい CI 向けのモード。
- **機構は SDK 実測で確定**(2026-07-05): 全書込プローブで canUseTool が**発火せず** denials に記録
  = engine 判定は ask ではなく hard deny(headless の ❌ が「ask の auto-deny」でないことの構造的証明。
  P1-a はまったく同じプローブで canUseTool が発火する=ask、との対照)。

## 運用時の留意事項

- CI では「allow に必要なツールを列挙 + dontAsk」にすると、想定外の操作が確実に止まる
  (default の「ask 経由の auto-deny」より機構として明示的)。
  **allow 済みが実際に通ることは P1-g で実測済み**(本ケースの肯定対照)。読取専用ツール(Read)は
  allow 不要で dontAsk でも通る(同 g)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで dontAsk モードの `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
承認プロンプトが一度も出ずに拒否されることがその場で確認できる(対話なのに聞かれないのが P1-a との違い)。

```bash
cd cases/P1-permission-mode/d-dontAsk && claude --permission-mode dontAsk
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py P1-permission-mode/d-dontAsk
python3 harness/run.py -m sdk P1-permission-mode/d-dontAsk
```

> `dontAsk` は ask を出さず即 deny するため**全形態で同結論**(対話でも承認プロンプトは出ない)。
> SDK では canUseTool 非発火 + denials 記録 = DENIED_HARD として観測される。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(4プローブとも一致) |
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | sdk(4プローブとも DENIED_HARD で一致。canUseTool 非発火=deny-not-ask の実証) |

## 対応する知識

- グループ [P1 README](../README.md)
- 関連: P1-a(default は ask→未承認で書けない。機構の対照)/ P1-e(bypass は逆に全許可)
