<!--
README テンプレート雛形(統一版・主要ケース用 / probes[] + 2軸 expected 準拠)
仕様の正本: docs/CASE-FORMAT.md「README の構成」/ docs/EXECUTION-MODALITIES.md TL;DR

原則:
- 主題は「permission/sandbox がどう制御されるか」。実行方法は主要な関心ごとではない。
  → タイトルと 1〜6 節(目的〜運用時の留意事項)にモダリティ(headless/SDK/対話)を登場させない。
- 期待結果は「ask は approve した前提」で書く(規約)。「headless/CI では ask が auto-deny になる」は
  全ケース共通の前提なので、各行の補足には書かない(凡例として docs/GLOSSARY.md §7 に1回。ケース固有に
  効いてくる場合のみ「運用時の留意事項」「試し方」で触れる)。
- 節の並びはこの順で固定。[任意] は該当しなければ節ごと省略する。
- 1ケース1論点。probes[] は同じ論点を多角的に実証する行であって、雑多な検証の詰め込み場ではない。
  設定を動かすならサブケースを分け、対比はグループ README に置く(→ templates/template-group.md)。
- 確定済みのセキュリティ/リスク注意は簡潔化の対象外 = 必ず「運用時の留意事項」に残す。
- ✅=成功 / ❌=ブロック・失敗。凡例は docs/GLOSSARY.md に1回だけ置く(各 README には書かない)。
- 危険設定を試すケースはタイトル末尾に「(アンチパターン)」を付け、「目的」冒頭に ⚠️ 警告行を置く。
-->

# <ID>: <permission/sandbox 挙動の結論を1行で>

<!-- 例: 「P1-a: default モード + 規則なし → 書込系ツールは ask(自動許可されない)」。
     「headless で拒否される」のようなモダリティ前提の結論にしない。
     環境依存の挙動(eligibility 制の preview 等)は「本環境では〜」を明示した実測の結論にする(→ P1-f)。 -->

## 目的

- 何を確認するケースかを1〜2点で(特筆すべき留意点はグループ README 側で表現する)。

## 前提(設定)

```json
// .claude/settings.json(全文はケースのファイル)— 挙動を左右する値だけ抜粋
{
  "permissions": { "allow": ["Read(**)"] }
}
```

- 設定の重要ポイントを箇条書きで簡潔に。
- [任意] `arrange` で用意する前提(番兵ファイル・git repo 等)があれば1行で。

## 実行内容

<!-- 何をさせるかの抽象的表現だけ。スクリプト名・コマンドは書かない(→「試し方」)。
     probes[] の各要素と1:1、期待結果表の No と同順にする。
     書込制御系は標準4プローブセット(write-cwd / write-home / write-subdir / edit-cwd)を推奨
     — パス方向とツール方向の境界が1ケースで判別でき、グループ間でマトリクス比較できる(→ CASE-FORMAT.md)。 -->

1. Write でケースディレクトリ直下にファイルを作成
2. Write でホームディレクトリ(cwd 外)にファイルを作成

## 期待結果

<!-- 1行 = 1プローブ(case.json の probes[] と同順)。
     許諾 = expected.permission(allow/deny/ask/-) / 結果 = expected.result を ✅/❌/- で。
     結果は「ask は approve した前提」(全ケース共通の規約。auto-deny 等の一般論を補足に書かない)。
     allow × ❌ = permission は通ったが sandbox(OS 層)が止めた、の典型。
     補足には許諾/結果の2列から読み取れる当たり前のことは書かない。無ければ「-」。
     セル内が他と比べて長くなり過ぎる場合は改行タグ(</br>)で折り返す。 -->

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(cwd 内) | ask | ✅ | - |
| 2 | Write `~/x.txt`(cwd 外) | ask | ✅ | - |

## なぜそうなるか

- 挙動原理(機構)の説明。実運用の「対策」は次節へ。
- **このケースの核心となる因果は1行を太字で残す(簡潔化しても落とさない)。**

## 運用時の留意事項

- 実プロジェクトで取るべき「対策」だけを箇条書きで(機構説明は「なぜ」に置く)。
- 確定済みのセキュリティ/リスク注意はここに必ず残す。

## 試し方(本リポジトリでの実測)

<!-- ここで初めてモダリティに言及する。「お手軽に試す」は全ケース共通で先頭に置き、
     ハーネス実測のブロックはケース類型で変える(→ docs/CASE-FORMAT.md)。
     類型A(ask 系)のブロックか、類型B/C(注記のみ)のブロックか、該当する方だけ残す。 -->

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
<!-- そのケースで観察できることを1行で(例: 各操作で承認プロンプトが出る/出ずにブロックされる)。
     run.flags でモードを与えるケースは起動コマンドにフラグを付ける(claude --permission-mode X)。
     bypassPermissions 等の危険モードは冒頭に「⚠️ 隔離環境でのみ」を置く。 -->

```bash
cd cases/<GROUP>/<SUB> && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

<!-- ［類型A: ask 系(expected.permission=ask)］3形態を併記 -->
```bash
# ヘッドレス(claude -p): ask は承認者不在で auto-deny → DENIED
python3 harness/run.py <GROUP>/<SUB>

# SDK(canUseTool = ask の計測器): ask の発火を構造的に観測 → ASK
python3 harness/run.py -m sdk <GROUP>/<SUB>

# 対話(TUI): 承認プロンプトが出て、承認すれば成功 → ASK
python3 harness/run.py -m interactive --step prepare <GROUP>/<SUB>
python3 harness/run.py -m interactive --step judge <GROUP>/<SUB> --answer prompted=y --answer approved=y
```

<!-- ［類型B: permission 層・非 ask］headless のみ+注記 -->
```bash
python3 harness/run.py <GROUP>/<SUB>
```

> allow/deny 規則(orモード)で結論が決まるため**全形態で同結論**(→ docs/EXECUTION-MODALITIES.md)。
> (`permission: "blocked"` のケースは ask/deny 未分離。`-m sdk` で切り分けて昇格するのが TODO)

<!-- ［類型C: OS 層(sandbox)系(probe≠permission)］headless のみ+注記 -->
```bash
python3 harness/run.py <GROUP>/<SUB>
```

> sandbox(OS 層)の I/O を観測するケース。**SDK の canUseTool は permission 層しか見えず
> OS 境界は測れない**ため、headless で実測する。

## 検証記録

<!-- 「いつ・どのバージョンで、この README の記載どおりに再現できたか」だけを残す。
     結論はここに書かない(期待結果で表現済み)。
     モダリティ欄は「headless / sdk(Nプローブとも一致)」のように全プローブ一致を明記。
     環境依存ケースは「環境条件」列を足す(アカウント種別・関連環境変数・モデル等 → P1-f)。
     ハーネス外の手動プローブ(scratch 探索)があれば「補足」列に残す(→ P3-d)。 -->

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| YYYY-MM-DD | vX.X.XXX | headless / sdk / interactive(Nプローブとも一致) |

## 対応する知識

- docs/FINDINGS.md: QN「…」
- 関連: <GROUP>-x(対照・続きのケース)
