import re
import urllib.request
import urllib.parse
import time
from typing import List, Dict, Any

def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search the web using DuckDuckGo's HTML interface.
    Returns a list of dicts: [{'title': ..., 'url': ..., 'snippet': ...}].
    """
    url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
    )
    
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    raise Exception(f"HTTP Status {response.status}")
                html = response.read().decode("utf-8")
                
            # Regex to match DuckDuckGo HTML results
            pattern = re.compile(
                r'<h2 class="result__title">[\s\S]*?<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>[\s\S]*?<a[^>]*class="result__snippet"[^>]*>([\s\S]*?)</a>'
            )
            matches = pattern.findall(html)
            
            results = []
            for m in matches[:max_results]:
                raw_url, raw_title, raw_snippet = m
                
                # Strip HTML tags
                title = re.sub(r'<[^>]+>', '', raw_title).strip()
                snippet = re.sub(r'<[^>]+>', '', raw_snippet).strip()
                
                # Decode url
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_url).query)
                actual_url = parsed.get("uddg", [raw_url])[0]
                
                results.append({
                    "title": title,
                    "url": actual_url,
                    "snippet": snippet
                })
                
            return results
            
        except Exception as e:
            print(f"DuckDuckGo search attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(1)
            else:
                return [{"error": f"Search failed: {str(e)}"}]
                
    return []
