# P1-i: settings の `permissions.defaultMode` → CLI フラグと同じ挙動(経路の等価性)

## 目的

- モード指定のもう一つの経路 **settings.json の `permissions.defaultMode`** が、
  CLI フラグ `--permission-mode` と同じ結果になることを実測する
- P1 グループの看板「設定の差分(mode を変える)」に対して b〜f の実体は CLI フラグ差分だった、
  というずれ(GAPS.md G8)を settings 経路の実測で埋める

## 前提(設定)

```json
{
  "permissions": {
    "defaultMode": "acceptEdits"
  }
}
```

- **CLI フラグは付けない**。モードを決めているのは settings.json だけ

## 実行内容

1. Write でケースディレクトリ直下にファイルを作成(cwd 内)
2. Write でホームディレクトリにファイルを作成(cwd 外)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Write `./PROOF.txt`(cwd 内) | allow | ✅ | P1-b の write-cwd と同結果 |
| 2 | Write `~/p1i-proof.txt`(cwd 外) | ask | ✅ | **cwd 境界も再現**(headless では ❌)。境界はモードに付随し、指定経路に依らない |

## なぜそうなるか

- `defaultMode` は「セッション開始時のモード既定値」。CLI フラグはそれを上書きする明示指定で、
  どちらの経路でも到達するモードが同じなら挙動も同じ(precedence: CLI > settings)。
- cwd 内 allow / cwd 外 ask の両側を測ることで、「settings 経由でも acceptEdits の
  自動承認と境界がそのまま付いてくる」ことを確認している。

## ⚠️ モダリティ差 — SDK では `defaultMode` が効かない(実測)

| 形態 | write-cwd | 解釈 |
|---|:---:|---|
| headless(CLI) | ALLOWED | CLI は settings の `defaultMode` を適用する |
| SDK(`settingSources: ["project"]`) | **ASK** | **settings の規則(allow/deny)は読まれるのに、`defaultMode` は発現しない** |

- SDK ではモードは `options.permissionMode`(既定値 `"default"`)で決まる。settings を
  `settingSources` で読み込んでも、モードだけは settings から持ち上がらない
  (P2 の SDK 実測で allow/deny 規則が settings から効くことは確認済み=規則とモードで扱いが違う)。
- **SDK でモードを変える唯一の経路は `options.permissionMode` を明示的に渡すこと。**
  `case.json` はこの差を `expected.byModality.sdk = "ASK"` として記録している。

## 運用時の留意事項

- チームで常用するモードは settings(project/user)の `defaultMode` に置き、
  一時的な切替だけ CLI フラグを使う、が使い分けの基本形。**ただし SDK 経由の自動化には
  settings の defaultMode は届かない**(上記)。SDK では options で明示する。
- settings の defaultMode と CLI フラグが衝突した場合の優先(CLI 勝ち)は docs 由来で未実測(→ GAPS.md G8 残項)。

## 試し方(本リポジトリでの実測)

```bash
python3 harness/run.py P1-permission-mode/i-defaultMode-in-settings
python3 harness/run.py -m sdk P1-permission-mode/i-defaultMode-in-settings
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless(2プローブとも一致)/ SDK(defaultMode 不発 → byModality で記録・一致) |

## 対応する知識

- グループ [P1 README](../README.md)
- 関連: P1-b(同モードの CLI フラグ経路)/ P7(settings スコープ間 precedence)
