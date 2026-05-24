# Mirelia Structured Data Marketplace

USPTO patent data MCP server for AI agents doing competitive intelligence, prior art search, and technology scouting.

## When to use

- User asks about patents, USPTO, prior art, IP landscape, or competitor technology
- R&D agent needs structured patent JSON with business value fields (not raw XML)
- Quant or VC workflow needs CPC-filtered semiconductor / AI / telecom patents

## Connect

```json
{
  "mcpServers": {
    "mirelia-patents": {
      "url": "https://mirelia-structured-data-marketplace.mcp.xpay.sh/mcp?key=YOUR_XPAY_KEY"
    }
  }
}
```

API key: https://xpay.tools

## Typical flow

1. `search_single_patents` with `primary_cpc` (e.g. G06) and optional `keyword`
2. `purchase_single_patent` with empty `tx_hash` → execute on-chain payload → retry with `tx_hash`
3. Or `search_packages` then `verify_crypto_payment_and_deliver` for bulk

## Networks

`polygon` (USDC, default), `base` (USDC), `oasis` (ROSE / WROSE for AA wallets)
