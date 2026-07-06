# srt-d: srt の network 境界 — 既定全ブロック + allowlist(Bash 経路)

## 目的

- srt の network 制御(既定全 deny・`allowedDomains` で開ける)が効くことを確認する。組み込み sandbox の
  network(`cases/S6`)と同型だが、srt は**プロセス全体**が対象(組み込みは Bash 限定)。
- このケースは Bash curl を直接 srt で包んで単離する(claude 非経由。permission 層・WebFetch の交絡を避ける)。

## 前提(設定)

```jsonc
{
  "filesystem": { "allowWrite": [".", "/tmp"] },
  "network": { "allowedDomains": ["api.anthropic.com", "*.anthropic.com"], "deniedDomains": [] }
}
```

## 実行内容

1. `srt --settings <上記> -c 'curl … https://api.anthropic.com'`(**許可**ドメイン)。
2. 同じく `curl … https://example.com`(**非許可**ドメイン)。

## 期待結果

| No | 操作 | 許諾 | 結果 | 補足 |
|---|---|:---:|:---:|---|
| 1 | curl api.anthropic.com(allowlist 内) | - | ✅ | 到達(HTTP 応答が返る) |
| 2 | curl example.com(allowlist 外) | - | ❌ | **接続不可**(HTTP=000)。既定全ブロック |

- 許諾列が `-` なのは permission 層を経ない純 OS 層の観測だから(srt が proxy で egress を仲介)。

## なぜそうなるか

- srt は macOS で Seatbelt + localhost proxy 構成。全 egress を proxy に強制し、proxy が `allowedDomains` で
  ホワイトリスト判定する。**プロセス非依存**(組み込み S6 と同じく `sh -c`・python でも遮断)。
- 組み込みとの差は「Bash 限定 vs プロセス全体」。srt なら claude の子プロセス全体の egress が1本に絞られる。

## 運用時の留意事項

- ネットワークを本当に止めたいなら permission の文字列 deny(`deny Bash(curl:*)`)ではなく OS 層で(P4-c ⇔ S6)。
  srt は claude プロセス全体にこの OS 層 network 境界をかけられる。
- **WebFetch も srt の network 境界に掛かる**(実測 srt-h): 当初「サーバ側実行で掛からない」疑いがあったが、
  WebFetch はローカルプロセス発の HTTP で、非許可ドメインは `Socket is closed` で遮断された(→ [h-webfetch-vs-network](../h-webfetch-vs-network/README.md))。
  それでも egress を多層で締めたいなら WebFetch は permission(P10 `WebFetch(domain:…)`)側でも塞ぐ。

## 試し方

```bash
cat > /tmp/net.json <<'JSON'
{"filesystem":{"allowWrite":[".","/tmp"]},"network":{"allowedDomains":["api.anthropic.com","*.anthropic.com"]}}
JSON
srt --settings /tmp/net.json -c 'curl -s -o /dev/null -w "%{http_code}\n" --max-time 8 https://api.anthropic.com'  # 応答
srt --settings /tmp/net.json -c 'curl -s -o /dev/null -w "%{http_code}\n" --max-time 8 https://example.com'        # 000=遮断
```

## 検証記録

| 日付 | バージョン | 実測 |
|---|---|---|
| 2026-07-06 | srt 0.0.63 / macOS | api.anthropic.com=HTTP 404(到達) / example.com=HTTP 000(遮断) |

## 対応する知識

- 組み込み側: `cases/S6-sandbox-network`(egress 既定全ブロック・allowedDomains・WebFetch 迂回=S6-h)
- WebFetch × srt: [h-webfetch-vs-network](../h-webfetch-vs-network/README.md)(srt-h で実測・掛かる)
