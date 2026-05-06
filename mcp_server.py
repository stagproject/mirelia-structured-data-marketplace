import os
import json
import time
import requests
import uvicorn
from typing import Optional
from pydantic import Field
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from supabase import create_client, Client
from dotenv import load_dotenv

from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, PlainTextResponse

from web3 import Web3
try:
    # web3.py v6+ (Polygon等で必須)
    from web3.middleware import ExtraDataToPOAMiddleware as poa_middleware
except ImportError:
    # 旧バージョン互換用
    from web3.middleware import geth_poa_middleware as poa_middleware


load_dotenv()

security_settings = TransportSecuritySettings(enable_dns_rebinding_protection=False)
mcp = FastMCP("Mirelia-Structured-Data-Marketplace", transport_security=security_settings)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
if url and key:
    supabase: Client = create_client(url, key)
else:
    supabase = None

# 各ネットワークのRPC初期化
rpc_base = os.environ.get("BASE_MAINNET")
rpc_polygon = os.environ.get("POLYGON_MAINNET")
rpc_oasis = os.environ.get("OASIS_MAINNET")

usdc_base_raw = os.environ.get("BASE_USDC")
usdc_polygon_raw = os.environ.get("POLYGON_USDC")
abi_string = os.environ.get("ERC20_ABI")
WALLET_ADDRESS_RAW = os.environ.get("SELLER_WALLET_ADDRESS")

chains = {}
if Web3 and abi_string and WALLET_ADDRESS_RAW:
    WALLET_ADDRESS = Web3.to_checksum_address(WALLET_ADDRESS_RAW)
    ERC20_ABI = json.loads(abi_string)
    
    if rpc_base and usdc_base_raw:
        w3_base = Web3(Web3.HTTPProvider(rpc_base))
        chains["base"] = {
            "w3": w3_base,
            "usdc": w3_base.eth.contract(address=Web3.to_checksum_address(usdc_base_raw), abi=ERC20_ABI),
            "type": "erc20"
        }
    
    if rpc_polygon and usdc_polygon_raw:
        w3_polygon = Web3(Web3.HTTPProvider(rpc_polygon))
        w3_polygon.middleware_onion.inject(poa_middleware, layer=0)
        chains["polygon"] = {
            "w3": w3_polygon,
            "usdc": w3_polygon.eth.contract(address=Web3.to_checksum_address(usdc_polygon_raw), abi=ERC20_ABI),
            "type": "erc20"
        }
        
    if rpc_oasis:
        w3_oasis = Web3(Web3.HTTPProvider(rpc_oasis))
        chains["oasis"] = {
            "w3": w3_oasis,
            "usdc": None,
            "type": "native"
        }
else:
    WALLET_ADDRESS = None

# -----------------------------------------------------------------------------
# ユーティリティ: Supabaseのエスケープ配列文字列をネイティブなJSON配列にパース
# -----------------------------------------------------------------------------
def clean_supabase_data(rows):
    array_fields = ['assignee', 'inventor', 'secondary_cpcs', 'attr_tech_stack', 'tech_stacks', 'biz_target_ind', 'attr_performance', 'package_tags', 'cited_patents']
    for row in rows:
        for field in array_fields:
            if field in row and isinstance(row[field], str):
                try:
                    row[field] = json.loads(row[field])
                except Exception:
                    pass
    return rows

# -----------------------------------------------------------------------------
# 1. 探索・詳細確認・重複確認 統合ツール (Hybrid Discovery)
# -----------------------------------------------------------------------------
@mcp.tool()
def search_packages(search_query: str = Field(default="", description="Search query. Use keywords like 'USPTO', 'G01', 'Physics', or 'Electricity'. Leave blank for all packages.")) -> str:
    """
    [COST: FREE]
    The primary marketplace exploration tool for USPTO structured patent data.
    Currently focuses on IPC Sections G (Physics, e.g., G01) and H (Electricity, e.g., H04).
    - If search_query is empty: Returns the full inventory (tags, titles, tech_stacks, prices) sorted by tag.
    - If search_query is provided: Returns detailed JSON info including 'description' and 'patent_ids' for deduplication.
    """
    if not supabase:
        return json.dumps({"error": "Database connection failed"})

    try:
        if search_query in ["null", "None", ""]:
            search_query = ""
            
        search_query = search_query.strip()

        if not search_query:
            res = supabase.table("v_package_marketplace") \
                .select("package_tag, category, title, record_count, price_usd, avg_importance_p, tech_stacks") \
                .order("package_tag") \
                .execute()
            return json.dumps(clean_supabase_data(res.data), ensure_ascii=False)
        else:
            safe_query = search_query.replace(",", " ")
            
            # 1. タグ完全一致の高速検索 (詳細データを含む v_catalogs を使用)
            if "_" in safe_query:
                exact_res = supabase.table("v_catalogs").select("*").eq("package_tag", safe_query).execute()
                if exact_res.data:
                    return json.dumps(clean_supabase_data(exact_res.data), ensure_ascii=False)

            # 2. 通常のあいまい検索 (LIMITを設けてタイムアウト防止)
            res = supabase.table("v_catalogs") \
                .select("*") \
                .or_(f"category.ilike.%{safe_query}%,title.ilike.%{safe_query}%,description.ilike.%{safe_query}%,package_tag.ilike.%{safe_query}%") \
                .order("package_tag") \
                .limit(20) \
                .execute()
            return json.dumps(clean_supabase_data(res.data), ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})
# -----------------------------------------------------------------------------
# 2. 決済・配信: 最終実行
# -----------------------------------------------------------------------------
@mcp.tool()
def verify_crypto_payment_and_deliver(
    tx_hash: str = Field(description="The transaction hash of the completed payment."),
    package_tag: str = Field(description="The tag of the package to purchase."),
    network: str = Field(description="The blockchain network used. Must be 'base', 'polygon', or 'oasis'.")
) -> str:
    """
    [COST: PAID / FINAL EXECUTION]
    Verifies an on-chain cryptocurrency transaction and delivers the full JSON dataset CDN URL. 
    Supported networks and currencies:
    - 'base': USDC
    - 'polygon': USDC
    - 'oasis': ROSE
    WARNING: Do NOT call this tool until you have successfully executed the blockchain transaction and obtained a valid 'tx_hash'. 
    """
    if not supabase:
        return json.dumps({"error": "Supabase connection failed"}, ensure_ascii=False)
        
    network = network.lower()
    if network not in chains:
        return json.dumps({"error": f"Unsupported or unconfigured network: {network}"}, ensure_ascii=False)
        
    tx_check = supabase.table("processed_transactions").select("tx_hash").eq("tx_hash", tx_hash).execute()
    if tx_check.data:
        return json.dumps({"error": "Transaction has already been processed."}, ensure_ascii=False)

    chain_info = chains[network]
    w3 = chain_info["w3"]

    try:
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
        except Exception:
            return json.dumps({"error": "Invalid transaction hash or receipt not found"}, ensure_ascii=False)

        if receipt['status'] != 1:
            return json.dumps({"error": "Transaction failed on-chain"}, ensure_ascii=False)

        block = None
        for _ in range(5):
            try:
                block = w3.eth.get_block(receipt['blockNumber'])
                break
            except Exception:
                time.sleep(2)
                
        if not block:
            return json.dumps({"error": "Block not found due to RPC sync delay. Please retry verification."}, ensure_ascii=False)

        current_time = int(time.time())
        if current_time - block['timestamp'] > 3600:
            return json.dumps({"error": "Transaction is expired. Must be executed within the last 1 hour."}, ensure_ascii=False)

        catalog_res = supabase.table("patent_packages").select("price_usd, sales_count").eq("package_tag", package_tag).execute()
        if not catalog_res.data:
            return json.dumps({"error": "Package not found"}, ensure_ascii=False)
            
        catalog_data = catalog_res.data[0]
        real_price_usd = float(catalog_data['price_usd'])
        
        payment_found = False
        
        if chain_info["type"] == "erc20":
            required_usdc = int(real_price_usd * (10**6))
            events = chain_info["usdc"].events.Transfer().process_receipt(receipt)
            for event in events:
                if event['args']['to'].lower() == WALLET_ADDRESS.lower() and event['args']['value'] >= required_usdc:
                    payment_found = True
                    break
        elif chain_info["type"] == "native":
            tx = w3.eth.get_transaction(tx_hash)
            if tx['to'] and tx['to'].lower() == WALLET_ADDRESS.lower():
                try:
                    res_cg = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=oasis-network&vs_currencies=usd", timeout=5)
                    rose_price = float(res_cg.json()['oasis-network']['usd'])
                    if rose_price > 0:
                        required_wei = int((real_price_usd / rose_price) * 0.95 * (10**18))
                        if tx['value'] >= required_wei:
                            payment_found = True
                except Exception as e:
                    return json.dumps({"error": str(e)}, ensure_ascii=False)

        if not payment_found:
             return json.dumps({"error": "Valid payment not found or insufficient amount."}, ensure_ascii=False)
             
        try:
            supabase.table("processed_transactions").insert({
                "tx_hash": tx_hash,
                "network": network,
                "package_tag": package_tag,
                "verified_at": current_time
            }).execute()
        except Exception:
            return json.dumps({"error": "Race condition: Transaction already processed."}, ensure_ascii=False)
             
        supabase.table("patent_packages").update({"sales_count": (catalog_data['sales_count'] or 0) + 1}).eq("package_tag", package_tag).execute()

        res_data = supabase.table("v_patent_marketplace_lite").select("*").contains("package_tags", [package_tag]).execute()
        
        return json.dumps({
            "system_log": f"Payment verified on {network.upper()}.",
            "package_data": clean_supabase_data(res_data.data)
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

if __name__ == "__main__":
    import sys
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import FileResponse
    from starlette.middleware.cors import CORSMiddleware

    # Cloud Run環境かどうかを判定（Cloud Runは自動的にK_SERVICE環境変数を付与する）
    is_cloud_run = "K_SERVICE" in os.environ

    if is_cloud_run or "--sse" in sys.argv:
        # ---------------------------------------------------------
        # Cloud Run用 (SSEモード / Uvicorn起動)
        # ---------------------------------------------------------
        async def agent_card(request):
            return FileResponse("agent-card.json")

        port = int(os.environ.get("PORT", 8080))
        mcp_asgi_app = mcp.sse_app()
        
        app = Starlette(routes=[
            Route("/.well-known/agent-card.json", endpoint=agent_card),
            Mount("/", app=mcp_asgi_app)
        ])
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"], 
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")
    else:
        # ---------------------------------------------------------
        # Glamaのテスト環境・ローカル用 (Stdioモード)
        # ---------------------------------------------------------
        mcp.run(transport="stdio")
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import FileResponse
    from starlette.middleware.cors import CORSMiddleware # 追加

    # 1. ファイルを返す「関数」を定義する
    async def agent_card(request):
        return FileResponse("agent-card.json")

    port = int(os.environ.get("PORT", 8080))
    
    # 2. 【ここが修正点】FastMCPからSSE用のASGIアプリを取り出す正しいメソッド
    mcp_asgi_app = mcp.sse_app()
    
    # 3. endpointには関数を指定し、mcpはルートにMountする
    app = Starlette(routes=[
        Route("/.well-known/agent-card.json", endpoint=agent_card),
        Mount("/", app=mcp_asgi_app)
    ])
    
    # 4. Inspector 等から接続するための CORS 設定
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")