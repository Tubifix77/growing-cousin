#!/usr/bin/env python3
# tool: fetcher
# call: fetcher <url>
# does: fetches the raw text content from a given URL.
import sys
import urllib.request

def main():
    if len(sys.argv) < 2:
        print("Usage: fetcher <url>")
        sys.exit(1)
    
    url = sys.argv[1]
    try:
        # Use a User-Agent to avoid being blocked by basic filters
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
            print(content)
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
