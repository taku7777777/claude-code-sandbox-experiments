# S2-a: sandbox on の書込境界は cwd(+tmp)だけ。cwd 外は permission を通っても OS 層で止まる(`allow ❌`)

## 目的

- sandbox の Bash 書込境界(既定 = cwd + セッション `$TMPDIR`)を、共通3プローブ(cwd 内 / cwd 外2パス)で実測して固定する。
- cwd 外の失敗が「承認プロンプト(ask)」ではなく「permission は自動許可・OS 層が EPERM」(`allow ❌`)であることを示す。

## 前提(設定)

```json
{ "sandbox": { "enabled": true } }
```

- sandbox を on にしただけ。`allowWrite` なし、モードは default、permission 規則なし。
- `arrange`(プローブ固有): cwd 外プローブの書込先 `~/lab-fs-write` `~/lab-glob-XYZ` を sandbox の外で先に作る(「dir 無し」ではなく「境界外」で失敗させるため)。実行後 `cleanup` で撤去。

## 実行内容

1. Bash で cwd 直下に書込(`echo data > inside.txt`)
2. Bash で cwd 外 `~/lab-fs-write/probe.txt` に書込(allowWrite 未登録)
3. Bash で cwd 外 `~/lab-glob-XYZ/probe.txt` に書込(別パス)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo > inside.txt`(cwd 内) | allow | ✅ | sandbox が Bash を自動許可し、cwd は境界内 |
| 2 | Bash `echo > ~/lab-fs-write/probe.txt`(cwd 外) | allow | ❌ | 境界外を OS が EPERM。ask は出ない(SDK で askFired 空を実測) |
| 3 | Bash `echo > ~/lab-glob-XYZ/probe.txt`(cwd 外) | allow | ❌ | 同上 |

- **`allow ❌` = permission は sandbox 自動許可で通るが、境界外への実 write を OS サンドボックスが EPERM で止める。** 2層の食い違いが1行で読める。

## なぜそうなるか

- sandbox の Bash 書込は allowlist で、既定境界は **cwd + セッション temp**(`$TMPDIR` は sandbox 用に付け替えられる。docs: sandboxing)。境界内なら OS が「外に出られない」ことを保証するので承認を省いて自動許可する(`autoAllowBashIfSandboxed` 既定 true → S4)。
- **cwd 外は permission を通した後 OS 層で EPERM。フォールバックの承認要求(ask)は発生しない** — SDK で `canUseTool` が発火しない(askFired 空)ことを実測。ここが S5-c(`Bash(*)` + `allowUnsandboxedCommands` で脱出)との分岐点。

## 運用時の留意事項

- 「sandbox なら全部書ける」ではない。cwd 外へ書かせたいパスは `allowWrite` にフルパスで足す(→ S2-b)。
- cwd 外の書込失敗は OS 層の EPERM であって承認待ちではない。対話で承認しても通らない(→ S5-c のような allow 併用が無い限り)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。1 は無言で成功、2・3 は承認プロンプトも出ないまま `operation not permitted` で失敗するのが見える。

```bash
cd cases/S2-sandbox-fs-write/a-inside-cwd && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S2-sandbox-fs-write/a-inside-cwd
python3 harness/run.py -m sdk S2-sandbox-fs-write/a-inside-cwd
```

> sandbox(OS 層)の I/O を観測するケース(probe=`fs-write`、対象パスの存在で判定)。**canUseTool は permission 層しか見えず OS 境界そのものは測れない**が、SDK は「境界外書込で ask が発火しない(askFired 空)」ことを併せて記録でき、`allow ❌` が ask でないことの裏づけになる。

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(3プローブとも一致) |

## 対応する知識

- docs/FINDINGS.md: Q2(sandbox を使っているのに書けない/permission が要る)
- グループ [S2 README](../README.md)(3×5 マトリクス)
- 関連: S2-b(allowWrite で穴を開ける)/ S2-c(cwd 外拒否の明示)/ S4-a(sandbox auto-allow の出所)/ S5-c(allow 併用で脱出)
- 一次 docs: sandboxing(既定境界 = cwd + 付け替え `$TMPDIR`)
