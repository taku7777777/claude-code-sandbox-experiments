# S3-k: denyRead の `*` はリテラル — glob と思って書くと fail-open で秘密が漏れる

## 目的

- sandbox `filesystem.denyRead` のパスが **glob 展開されるか、リテラル文字列か**を確定する(S2-e が `allowWrite` で確定した挙動の read 側パリティ)。
- 危険度の非対称を可視化する: allowlist(write)で glob が効かないのは fail-closed(書けないだけ)。**blacklist(denyRead)で glob が黙って不一致になるのは fail-open**(塞いだつもりの秘密が読める)。

## 前提(設定)

```json
{
  "sandbox": {
    "enabled": true,
    "filesystem": {
      "denyRead": ["~/lab-rd-*", "~/lab-rd-lit"]
    }
  }
}
```

- `~/lab-rd-*` は glob に見えるエントリ。`~/lab-rd-lit` は plain literal の対照。
- 各プローブが自分の番兵ファイルを `arrange.setup` で用意し、実行後に自動削除。

## 実行内容

1. Bash で `cat ~/lab-rd-XYZ/f.txt`(`lab-rd-*` が glob なら `lab-rd-XYZ` に一致して塞がるはずの経路)
2. Bash で `cat ~/lab-rd-lit/f.txt`(plain literal エントリで確実に塞がる対照)

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | Bash `cat ~/lab-rd-XYZ/f.txt` | allow | ✅ | `*` はリテラルなので `lab-rd-*` は `lab-rd-XYZ` に不一致 → 番兵が漏れる(**fail-open**) |
| 2 | Bash `cat ~/lab-rd-lit/f.txt` | allow | ❌ | plain literal の denyRead が OS 層で遮断(実行痕跡 `MARK_S3K_LIT` は出るが番兵は出ない) |

- **1(漏洩)と 2(遮断)の対**が肝: 2 で「この設定下で denyRead は生きている」ことを示すので、1 の漏洩は「sandbox が切れている」ではなく「**glob エントリが不活性**」だと確定する。

## なぜそうなるか

- **sandbox のパスはリテラル。`*` はワイルドカードとして展開されず、ディレクトリ名の一部の文字として扱われる。** よって `denyRead:["~/lab-rd-*"]` は「`lab-rd-*` という名前のディレクトリ」しか指さず、`lab-rd-XYZ` のような実在名には一致しない。書いた本人は塞いだつもりでも秘密は読める。

## 運用時の留意事項

- ⚠️ **`denyRead` / `allowRead` は必ずフルのリテラルパスで書く。** `denyRead:["~/secrets-*"]` や `["~/.ssh/*"]` のような glob 風の記述は**黙って何も保護しない**(エラーも警告も出ない)。塞ぎたいディレクトリは実名で列挙する。
- write 側(`allowWrite`)の同じリテラル性は fail-closed(書けないだけ)だが、read 側の blacklist では同じ挙動が fail-open(漏れる)になる。危険度が段違いに高い。

## 試し方(本リポジトリでの実測)

### お手軽に試す(対話)

```bash
cd cases/S3-sandbox-fs-read/k-denyread-glob-literal && claude
# → prompt.ja.txt を貼り付け
```

### ハーネスで実測する(結果の記録・プローブ独立)

```bash
python3 harness/run.py S3-sandbox-fs-read/k-denyread-glob-literal
python3 harness/run.py -m sdk S3-sandbox-fs-read/k-denyread-glob-literal
```

## 検証記録

| 日付 | バージョン | 実測したモダリティ |
|---|---|---|
| 2026-07-05 | v2.1.201 | headless(2回反復で安定)/ sdk(2プローブ一致) |

補足: 「`lab-rd-*` という名前そのもののディレクトリ」を読むプローブも試したが、実行/自己抑制でランごとに結果が揺れた(モデルが未実行のまま拒否を装う failure mode)ため、採点対象からは外した。安定して観測できる主張(通常名の兄弟ディレクトリが漏れる=fail-open / plain literal は効く)のみをスコア化している。

## 対応する知識

- docs/FINDINGS.md: 「sandbox パスはリテラル(`*` 非展開)」(S2-e で write 側、本ケースで read 側)
- 関連: [S2-e](../../S2-sandbox-fs-write/e-glob-literal/README.md)(write 側パリティ)/ [a](../a-denyread-blocks/README.md)(denyRead:["~"] で全域遮断)/ [グループ README](../README.md)
