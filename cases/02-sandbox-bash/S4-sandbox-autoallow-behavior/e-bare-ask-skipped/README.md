# S4-e: bare `Bash` ask は **sandbox 実行分にはスキップ・非 sandbox(excluded)実行分には適用** — ask を分けるのは規則でなく実行経路

## 目的

- docs の「bare `Bash` ask 規則は sandbox 実行にはスキップされ、fallback(非 sandbox)実行には適用される」
  の**両半分を同一設定内で直接実証**する(従来の a は「ask 規則を跨いだ」ことを分離できていなかった)。

## 前提(設定)

```json
{
  "sandbox": { "enabled": true, "excludedCommands": ["touch *"] },
  "permissions": { "ask": ["Bash"] }
}
```

- ask は **bare 形**(`Bash`)。`excludedCommands` により `touch *` だけ sandbox の**外**で実行される
  (= 実行経路をプローブで切り替えるための仕掛け。設定は 1 枚のまま)。

## 実行内容

1. Bash で `echo data > inside.txt`(sandbox 内で実行される)
2. Bash で `touch s4e-fallback.txt`(excluded → sandbox 外で実行される)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `echo data > inside.txt`(sandbox 実行) | allow | ✅ | **bare `Bash` ask はスキップ**され auto-allow が勝つ(無プロンプト) |
| 2 | Bash `touch s4e-fallback.txt`(非 sandbox 実行) | ask | ✅ | **同じ ask 規則が非 sandbox 分には適用**される |

- touch は read-only 集合外(P4-i)なので「元々無条件承認だった」交絡はない。

## なぜそうなるか

- **bare `Bash` ask の適用可否は実行経路で決まる**: sandbox 化された実行は OS 境界に守られている前提で
  ask がスキップされ(auto-allow)、sandbox の外で走る分(excluded / fallback)は通常の permission
  フローに乗るので bare ask がそのまま効く。
- 同一設定で probe 1 と 2 の結果が割れることが、この分岐の直接証拠(設定差ではなく経路差)。
- 対になる分岐: **content-scoped ask(`Bash(touch *)` 等)は sandbox 実行でもスキップされない**(→ S4-f)。

## 運用時の留意事項

- 「全 Bash を確認制にしたい」つもりで `ask: ["Bash"]` を書いても、**sandbox が有効なら sandbox 内実行分は
  素通りする**。sandbox 下で確認を強制したいなら content-scoped ask(S4-f)か `autoAllowBashIfSandboxed:false`(S4-d)。
- 逆に excludedCommands で sandbox 外に出したコマンドは bare ask のゲートを受ける — excluded は
  「無条件で楽になる」わけではない(S5-a の脱出とは別の面)。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

このディレクトリで `claude` を起動し、[prompt.ja.txt](./prompt.ja.txt) を貼り付けるだけ。同じ ask 規則の下で 1 は無プロンプト・2 だけ承認プロンプトが出る。

```bash
cd cases/S4-sandbox-autoallow-behavior/e-bare-ask-skipped && claude
```

### ハーネスで実測する(ask 系: SDK の canUseTool が決定的シグナル)

```bash
python3 harness/run.py S4-sandbox-autoallow-behavior/e-bare-ask-skipped
python3 harness/run.py -m sdk S4-sandbox-autoallow-behavior/e-bare-ask-skipped
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 / SDK 0.3.200 | headless(P1: ALLOWED / P2: DENIED=auto-deny)/ sdk(P1: askFired 空で ALLOWED / **P2: askFired=[Bash] で ASK**) |

## 対応する知識

- グループ [S4 README](../README.md) / S4 GAPS G4 の解消(spec §4.2 ④の両半分)
- 関連: S4-f(content-scoped ask は貫通=対の分岐)/ S4-a(auto-allow ベースライン)/ S5-a(excludedCommands の脱出面)/ P4-i(touch は read-only 集合外)
