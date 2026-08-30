import httpx

TARGET_TOKENS = {"USDC", "USDT", "DAI", "ETH", "WETH"}

# Maps weird vault token symbols to our standard clean targets
TOKEN_MAPPINGS = {
    "USDC.E": "USDC",
    "USDT.E": "USDT",
    "WETH": "ETH",
}

AAVE_V3_SUBGRAPHS = {
    "ethereum": "https://api.thegraph.com/subgraphs/name/aave/protocol-v3-ethereum",
    "arbitrum": "https://api.thegraph.com/subgraphs/name/aave/protocol-v3-arbitrum",
    "optimism": "https://api.thegraph.com/subgraphs/name/aave/protocol-v3-optimism",
}

COMPOUND_V3_SUBGRAPHS = {
    "ethereum": "https://api.thegraph.com/subgraphs/name/messari/compound-v3-ethereum",
    "arbitrum": "https://api.thegraph.com/subgraphs/name/messari/compound-v3-arbitrum",
}

def parseRayRate(rate_str: str) -> float:
    # Ray is 1e27, converts to a standard percentage
    return (float(rate_str) / 1e27) * 100

def fetch_aave_v3(client: httpx.Client) -> list:
    """Query Aave V3 subgraphs to get current supply APYs."""
    results = []
    query = """
    {
      reserves {
        symbol
        decimals
        liquidityRate
      }
    }
    """
    for chain, url in AAVE_V3_SUBGRAPHS.items():
        try:
            r = client.post(url, json={"query": query})
            if r.status_code != 200:
                continue
            aave_responseData = r.json()
            reserves = aave_responseData.get("data", {}).get("reserves", [])
            for res in reserves:
                sym = res["symbol"].upper()
                sym = TOKEN_MAPPINGS.get(sym, sym)
                if sym in TARGET_TOKENS:
                    apy = parseRayRate(res["liquidityRate"])
                    results.append({
                        "protocol": "Aave V3",
                        "chain": chain,
                        "token": sym,
                        "apy": round(apy, 4),
                        "type": "Lend"
                    })
        except httpx.HTTPError:
            pass # FIXME: Aave v3 subgraph on optimism sometimes rate limits, need fallback RPC query?
    return results

def fetch_compound_v3(client: httpx.Client) -> list:
    results = []
    query = """
    {
      markets {
        inputToken {
          symbol
        }
        rates {
          rate
          side
        } 
      } 
    }
    """
    for chain, url in COMPOUND_V3_SUBGRAPHS.items():
        try:
            r = client.post(url, json={"query": query})
            if r.status_code != 200:
                continue
            data = r.json()
            markets = data.get("data", {}).get("markets", [])
            for market in markets:
                sym = market["inputToken"]["symbol"].upper()
                sym = TOKEN_MAPPINGS.get(sym, sym)
                if sym in TARGET_TOKENS:
                    for rate_obj in market.get("rates", []):
                        if rate_obj.get("side") == "LENDER":
                            # Messari compound v3 rate is already percentage (e.g. 4.25)
                            apy = float(rate_obj["rate"])
                            results.append({
                                "protocol": "Compound V3",
                                "chain": chain,
                                "token": sym,
                                "apy": round(apy, 4),
                                "type": "Lend"
                            })
        except httpx.HTTPError:
            pass
    return results

def fetch_beefy(client: httpx.Client) -> list:
    """Fetch all active Beefy vaults matching our target assets."""
    results = []
    try:
        vaults_r = client.get("https://api.beefy.finance/vaults")
        apys_r = client.get("https://api.beefy.finance/apy")
        
        if vaults_r.status_code != 200 or apys_r.status_code != 200:
            return results
            
        vaults = vaults_r.json()
        apys = apys_r.json()
        
        # print(f"DEBUG: Found {len(vaults)} beefy vaults, {len(apys)} apys")
        
        for vault in vaults:
            if vault.get("status") != "active":
                continue
            
            raw_token = vault.get("token", "").upper()
            token = TOKEN_MAPPINGS.get(raw_token, raw_token)
            if token not in TARGET_TOKENS:
                continue
                
            v_id = vault["id"]
            if v_id in apys:
                apy = apys[v_id] * 100 # Beefy yields are decimal (0.054 -> 5.4%)
                results.append({
                    "protocol": f"Beefy ({vault.get('platformId', 'Unknown')})",
                    "chain": vault.get("chain", "unknown"),
                    "token": token,
                    "apy": round(apy, 4),
                    "type": "Vault"
                })
    except httpx.HTTPError:
        pass
    return results

def fetch_all() -> list:
    # Use a single client with reasonable timeouts to speed up requests
    # and prevent connection resets on Windows.
    # TODO: Compound v3 USDC market on Arbitrum has a different subgraph endpoint we should add
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    with httpx.Client(timeout=8.0, limits=limits) as client:
        all_yields = []
        all_yields.extend(fetch_aave_v3(client))
        all_yields.extend(fetch_compound_v3(client))
        all_yields.extend(fetch_beefy(client))
        return all_yields
