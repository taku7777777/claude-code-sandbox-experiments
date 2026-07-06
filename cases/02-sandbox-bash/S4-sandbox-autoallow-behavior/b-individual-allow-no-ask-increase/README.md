# S4-b: 個別 allow `Bash(echo:*)` を足しても ask は増えない(結果は c と同一)

## 目的

- sandbox auto-allow に個別 allow `Bash(echo:*)` を1つ足したとき、承認要求(ask)が増えるかを実測する。
- 結果が c(allow:[])と**同一**であることを示し、「ask を左右するのは allow 構成ではなくコマンド形状」を確定する(c との1変数対比)。

## 前提(設定)

```json
{ "sandbox": { "enabled": true }, "permissions": { "allow": ["Bash(echo:*)"] } }
```

- c(`allow:[]`)に個別 allow `Bash(echo:*)` を1つ足しただけ。プローブは c と同一の2本。

## 実行内容

1. Bash で単純コマンド(`echo hi > out.txt`)
2. Bash で glob→変数→ファイルアクセス(`for f in *.txt; do wc -l "$f"; done`)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo hi > out.txt`(単純) | allow | ✅ | c と同じ(auto-allow) |
| 2 | Bash `for f in *.txt; do wc -l "$f"; done` | ask | ✅ | c と同じ(形状で ask)。**個別 allow を足しても ask は増えない** |

- c 列と完全に同一。個別 allow の追加は ask 頻度を変えない。

## なぜそうなるか

- **ask を決めるのはコマンド形状であって allow 構成ではない。** 個別 allow `Bash(echo:*)` を足しても、単純 echo は元から auto-allow、glob→変数→ファイルは元から ask で、どちらも変化しない。
- これは `multi-repo-workspace.md` の主張(「個別 allow を入れると permission 層が allow マッチモードに切り替わり ask が増える。`allow:[]` + autoAllow が最善」)を **v2.1.201 で否定**する。当該記述(L84 / L286)は本グループの実測と食い違っており、統合 pass での同期対象。

## 運用時の留意事項

- 「個別 allow は逆効果だから `allow:[]` にせよ」という指針は本環境では再現しない。allow 構成は ask 頻度に効かない。
- ask を減らしたいならコマンド形状を単純化する(→ c)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。c と同じく 1 は無言実行、2 で承認プロンプトが出る。

```bash
cd cases/S4-sandbox-autoallow-behavior/b-individual-allow-no-ask-increase && claude
```

### ハーネスで実測する(結果の記録・プローブ独立)

プローブ2が ask 系:

```bash
python3 harness/run.py S4-sandbox-autoallow-behavior/b-individual-allow-no-ask-increase
python3 harness/run.py -m sdk S4-sandbox-autoallow-behavior/b-individual-allow-no-ask-increase
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless / sdk(2プローブとも一致・c と同一結果) |

## 対応する知識

- グループ [S4 README](../README.md)
- 関連: S4-c(baseline・同結果)/ multi-repo-workspace.md(逆主張=統合 pass で同期)
