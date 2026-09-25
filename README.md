# defi-yield-finder

A simple command-line tool to fetch, filter, and compare yields across Aave V3, Compound V3, and Beefy Finance vaults. It caches results locally to avoid hitting API rate limits during quick searches.

I got tired of opening bloated web interfaces just to check where to park some stablecoins or ETH. This script pulls directly from the public APIs and formats everything in a clean CLI table.

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/defi-yield-finder.git
   cd defi-yield-finder
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the finder with no arguments to get all rates above 1% APY:
```bash
python finder.py
```

Filter by asset (e.g., USDC, ETH):
```bash
python finder.py --asset USDC
```

Filter by minimum APY and sort by yield descending:
```bash
python finder.py --min-apy 4.5 --sort yield
```

Force refresh the cache instead of using the local file:
```bash
python finder.py --refresh
```

By default, cached data is stored in `yield_cache.json` in the current directory and is considered fresh for 10 minutes.

<!-- last-checked: 2026-09-25 -->
