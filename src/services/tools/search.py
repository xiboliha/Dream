"""Web search tool for querying information from the internet."""

import asyncio
import aiohttp
import re
import html as html_lib
from typing import Optional, Dict, Any, List
from urllib.parse import quote_plus, quote, unquote
from loguru import logger


class WebSearchTool:
    """Tool for web search using Bing China (works in China without captcha)."""

    def __init__(self):
        """Initialize web search tool."""
        self.bing_url = "https://cn.bing.com/search"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    async def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the web for information.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            Search results dict
        """
        try:
            timeout = aiohttp.ClientTimeout(total=15)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                params = {"q": query}
                async with session.get(
                    self.bing_url,
                    params=params,
                    headers=self.headers,
                    allow_redirects=True,
                ) as response:
                    if response.status == 200:
                        html = await response.text(encoding='utf-8', errors='replace')
                        results = self._parse_bing_results(html, max_results)
                        if results:
                            return {
                                "success": True,
                                "query": query,
                                "results": results,
                                "count": len(results),
                            }
                        else:
                            logger.warning("No results parsed from Bing")
                            return {"success": False, "error": "未找到搜索结果", "query": query}
                    else:
                        logger.warning(f"Bing returned {response.status}")
                        return {"success": False, "error": "搜索服务暂时不可用", "query": query}

        except asyncio.TimeoutError:
            logger.error("Web search timeout")
            return {"success": False, "error": "搜索超时", "query": query}
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {"success": False, "error": "搜索失败", "query": query}

    def _parse_bing_results(self, html: str, max_results: int) -> List[Dict[str, str]]:
        """Parse Bing HTML results.

        Args:
            html: HTML response
            max_results: Maximum results to extract

        Returns:
            List of result dicts with title, snippet, url
        """
        results = []

        # Bing uses <li class="b_algo"> for search results
        algo_pattern = r'<li class="b_algo"[^>]*>(.*?)</li>'
        algos = re.findall(algo_pattern, html, re.DOTALL)

        for algo in algos:
            if len(results) >= max_results:
                break

            # Extract title and URL from h2 tag (more reliable)
            h2_match = re.search(r'<h2[^>]*>(.*?)</h2>', algo, re.DOTALL)
            if not h2_match:
                continue

            h2_content = h2_match.group(1)
            link_match = re.search(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', h2_content, re.DOTALL)
            if not link_match:
                continue

            url = link_match.group(1)
            title_html = link_match.group(2)

            # Clean title - remove nested divs that contain site info (tpic/tptxt)
            title_html = re.sub(r'<div class="tpic".*?</div></div></div>', '', title_html, flags=re.DOTALL)
            title_html = re.sub(r'<div class="tptxt".*?</div></div>', '', title_html, flags=re.DOTALL)
            title = html_lib.unescape(re.sub(r'<[^>]+>', '', title_html).strip())

            # Skip empty or very short titles
            if not title or len(title) < 3:
                continue

            # Extract snippet
            snippet = ""
            snippet_patterns = [
                r'<p[^>]*class="[^"]*b_lineclamp[^"]*"[^>]*>(.*?)</p>',
                r'<div[^>]*class="[^"]*b_caption[^"]*"[^>]*>.*?<p>(.*?)</p>',
                r'<p>(.*?)</p>',
            ]
            for sp in snippet_patterns:
                sm = re.search(sp, algo, re.DOTALL)
                if sm:
                    snippet = html_lib.unescape(re.sub(r'<[^>]+>', '', sm.group(1)).strip())
                    if len(snippet) > 20:
                        break

            results.append({
                "title": title,
                "snippet": snippet[:200] if snippet else "",
                "url": url,
            })

        return results

    def format_search_results(self, search_data: Dict[str, Any]) -> str:
        """Format search results for AI context.

        Args:
            search_data: Search results dict

        Returns:
            Formatted string for conversation context
        """
        if not search_data.get("success"):
            return f"搜索失败: {search_data.get('error', '未知错误')}"

        results = search_data.get("results", [])
        if not results:
            return f"没有找到关于「{search_data.get('query', '')}」的相关信息"

        formatted = f"搜索「{search_data.get('query', '')}」的结果:\n"
        for i, r in enumerate(results[:3], 1):  # Only show top 3
            formatted += f"\n{i}. {r['title']}\n"
            if r['snippet']:
                formatted += f"   {r['snippet'][:150]}...\n"

        return formatted

    def should_search(self, message: str) -> Optional[str]:
        """Determine if message needs web search and extract query.

        Args:
            message: User message

        Returns:
            Search query if search is needed, None otherwise
        """
        # Keywords that indicate search intent
        search_triggers = [
            # Direct search requests - "你搜一下", "帮我查查"
            (r'(?:你)?(?:搜一下|搜索一下|搜下|搜搜|查一下|查查|帮我查|帮我搜|百度一下|谷歌一下)(.+)', 1),
            # News/current events - "最新的新闻", "帮我查查最新的新闻"
            (r'(?:帮我)?(?:查查|搜搜)?(?:最新|最近)(?:的)?(.*)(?:新闻|消息|情况|动态)', 1),
            (r'(?:最新|最近)(?:的)?(?:新闻|消息)', 0),  # "最新的新闻" -> full match
            # Knowledge questions
            (r'(.+)(?:是什么|是谁|怎么回事|什么意思)', 1),
            (r'(?:你知道|知道吗|了解)(.+?)(?:吗|么|不)', 1),
            # How-to questions
            (r'(.+)(?:怎么做|怎么弄|如何|怎样)', 1),
            # Time/schedule questions - "几点钟开始营业"
            (r'(.+?)(?:几点|什么时候|多久)(.+)', 0),  # group 0 = full match
        ]

        for pattern, group in search_triggers:
            match = re.search(pattern, message)
            if match:
                if group == 0:
                    query = match.group(0).strip()
                else:
                    query = match.group(group).strip()

                # Handle empty query for news
                if not query or query in ['的']:
                    if '新闻' in message:
                        query = '今日新闻'
                    else:
                        continue

                # Filter out too short or common phrases
                if len(query) >= 2 and query not in ['你', '我', '这', '那', '什么']:
                    # For news queries, add context if needed
                    if '新闻' in message and '新闻' not in query:
                        query = query + ' 新闻'
                    return query

        return None
