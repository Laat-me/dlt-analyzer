"""Pure helpers for the public-search website list."""
from __future__ import annotations
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import ipaddress

TRACKING_KEYS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "gclid", "fbclid", "msclkid", "spm", "from"}
SEARCH_HOSTS = {"bing.com", "www.bing.com", "cn.bing.com", "google.com", "www.google.com", "baidu.com", "www.baidu.com", "sogou.com", "www.sogou.com", "so.com", "www.so.com", "duckduckgo.com", "www.duckduckgo.com"}
BLOCKED_DOMAINS = {"lottery.gov.cn", "sporttery.cn", "wiktionary.org", "wikipedia.org", "bing.com", "google.com", "baidu.com", "bigline.hk", "hanyuguoxue.com", "taikwun.hk"}
MULTI_LABEL_SUFFIXES = {"com.cn", "net.cn", "org.cn", "gov.cn", "com.hk", "co.uk", "org.uk", "ac.uk"}

def canonicalize_url(url: str) -> str | None:
    if not isinstance(url, str) or not url.strip(): return None
    try:
        p = urlsplit(url.strip())
        if p.scheme.lower() not in {"http", "https"} or not p.hostname: return None
        host = p.hostname.lower().rstrip(".")
        port = p.port
        if (p.scheme.lower() == "http" and port == 80) or (p.scheme.lower() == "https" and port == 443): port = None
        netloc = host if port is None else f"{host}:{port}"
        query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in TRACKING_KEYS]
        return urlunsplit((p.scheme.lower(), netloc, p.path or "/", urlencode(query), ""))
    except (ValueError, UnicodeError):
        return None

def extract_host(url: str) -> str | None:
    u = canonicalize_url(url)
    return urlsplit(u).hostname if u else None

def registrable_domain(host: str | None) -> str | None:
    if not host: return None
    host = host.lower().rstrip(".")
    try: ipaddress.ip_address(host); return host
    except ValueError: pass
    labels = host.split(".")
    if len(labels) <= 2: return host
    suffix = ".".join(labels[-2:])
    if suffix in MULTI_LABEL_SUFFIXES and len(labels) >= 3:
        return ".".join(labels[-3:])
    return suffix

def is_allowed_result_url(url: str) -> bool:
    host = extract_host(url); domain = registrable_domain(host)
    if not host or not domain: return False
    if domain in SEARCH_HOSTS or host in SEARCH_HOSTS: return False
    if domain in BLOCKED_DOMAINS: return False
    lowered = url.lower()
    if any(x in lowered for x in ("/search", "/login", "/signin", "/captcha", "javascript:", "mailto:")): return False
    return True

def site_from_url(url: str, query: str, target: str, discovered_at: str) -> dict | None:
    canonical = canonicalize_url(url)
    if not canonical or not is_allowed_result_url(canonical): return None
    domain = registrable_domain(extract_host(canonical))
    return {"domain": domain, "representativeUrl": canonical, "queries": [query], "targetDrawNum": str(target), "discoveredAt": discovered_at}

def merge_site(existing: dict, incoming: dict) -> dict:
    out = dict(existing)
    out["queries"] = sorted(set(existing.get("queries", [])) | set(incoming.get("queries", [])))
    return out

def dedupe_sites(items: list[dict], max_sites: int | None = None) -> list[dict]:
    merged = {}
    for item in items:
        domain = item.get("domain")
        if not domain: continue
        merged[domain] = merge_site(merged[domain], item) if domain in merged else item
    out = [merged[k] for k in sorted(merged)]
    return out[:max_sites] if max_sites else out
