# P1-f: auto モード(research preview) → 本環境では自動承認は発現せず、default 相当(全書込 ask)

> 🔬 **auto は eligibility 制の research preview**。この README の期待結果は
> 「**eligibility の無い本環境で実際にどう動いたか**」の記録であり、文書上の仕様
> (working dir 内は自動承認)とは一致しない。環境条件は「検証記録」に明記。

## 目的

- 公式 6 モードのうち P1 に欠けていた `auto`(分類器=モデルが許可判定を下す唯一のモード)の実挙動を、
  本環境の条件下で記録する
- 文書上の仕様(working dir 内編集は自動承認)が発現するか否かを、他モードと同一の4プローブで確認する

## 前提(設定)

```json
{}
```

- 規則なし。モードは CLI フラグ `--permission-mode auto` で与える(P1 の他サブケースと同じ構図)
- auto の eligibility 要件(いずれも本環境では未充足):
  - research preview(v2.1.83+)/ Team / Enterprise での有効化
  - モデル制約: API は Opus 4.6+ / Sonnet 4.6+。Bedrock 等は Sonnet 5・Opus 4.7/4.8 + `CLAUDE_CODE_ENABLE_AUTO_MODE=1`

## 実行内容

1. Write でケースディレクトリ直下にファイルを作成
2. Write でホームディレクトリ(cwd 外)にファイルを作成
3. Write でケース内のサブディレクトリにファイルを作成
4. Edit で既存ファイル(cwd 内)の文字列を置換

## 期待結果(本環境での実測値)

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(cwd 内) | ask | ✅ | 仕様上は自動承認(②)のはずのセル。本環境では発現せず |
| 2 | Write `~/p1f-proof.txt`(cwd 外) | ask | ✅ | - |
| 3 | Write `./sub/proof.txt`(サブdir) | ask | ✅ | 同上(仕様上は②) |
| 4 | Edit `./note.txt`(既存ファイル) | ask | ✅ | 同上(仕様上は②) |

- 4プローブとも `ask`(SDK で canUseTool 発火を確認)= **P1-a(default)と完全に同一の挙動**。
- フラグ `--permission-mode auto` 自体は受理される(エラーにならない)。

## なぜそうなるか

- 文書上の仕様(spec §1.4)の判定順: ① allow/deny 規則で即決 → ② 読取・working dir 内編集は自動承認 →
  ③ 残りは分類器(モデル)が判断。仕様どおりなら 1・3・4 は ② で allow になるはず。
- **本環境は eligibility 未充足のため、auto の自動承認(②)も分類器(③)も発現せず、default モードに
  フォールバックしたのと同じ挙動になる**(フラグ受理と機能有効化が別、という実測)。

## 運用時の留意事項

- auto を指定しても**有効化されているとは限らない**。エラーにならずに default 相当で動くため、
  「自動承認されるはず」を前提にした CI/自動化は eligibility を確認してから組む。
- 有効な環境でも: headless(-p) では反復 block でセッションが abort する(spec §1.4)。
  判定 ③ は分類器(モデル)依存で、規則ベースのモードと違って決定的でない。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで auto モードの `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) の内容を貼り付けるだけ。
eligibility の無い環境では全操作で承認プロンプトが出る(=default 相当)。有効な環境なら
1・3・4(working dir 内)が自動承認されるはずで、その差自体が観察対象。

```bash
cd cases/P1-permission-mode/f-auto-mode && claude --permission-mode auto
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

ask 系(本環境)なので SDK で ask の発火を切り分けられる。

```bash
# ヘッドレス: ask の auto-deny で全プローブ DENIED
python3 harness/run.py P1-permission-mode/f-auto-mode

# SDK(canUseTool = ask の計測器): 全プローブ ASK = default と同一
python3 harness/run.py -m sdk P1-permission-mode/f-auto-mode
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ | 環境条件 |
|---|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(4プローブとも一致) | 個人アカウント(Team/Enterprise 有効化なし)<br>`CLAUDE_CODE_ENABLE_AUTO_MODE` 未設定<br>model=claude-haiku-4-5 |

- ⚠️ この結果は**環境依存**。eligibility を満たす環境で再実測したら、1・3・4 が `allow` に反転するか
  要確認(そのときは expected を更新し本注記を差し替える)。

## 対応する知識

- docs/EXECUTION-MODALITIES.md「canUseTool ≠ auto mode」(auto=モデル分類器 / canUseTool=自作コード)
- 関連: P1-a(本環境の auto と同一挙動)/ P1-b(自動承認が機能する場合の比較対象)
