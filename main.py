import os
import requests
import feedparser
from openai import OpenAI
from datetime import datetime, timedelta
import time
from email.utils import parsedate_to_datetime

# ==========================================
# 1. 核心环境配置 (API 密钥)
# ==========================================
# 📢 [用户自定义区]：请确保你的运行环境或 GitHub Actions 中配置了这两个环境变量
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# ==========================================
# 2. 终极信息源矩阵 (RSS 订阅源)
# ==========================================
# 📢 [用户自定义区]：在这里填入你感兴趣的国内源（比如你本地部署的 WeRSS 链接，或独立博客 RSS）
DOMESTIC_FEEDS = [
    "http://124.223.40.126:8001/feed/all.rss" # 示例：本地微信公众号聚合源
    "https://ai-digest.liziran.com/en/feed.xml"
    "https://www.jiqizhixin.com/rss"
]

# 📢 [用户自定义区]：在这里填入你感兴趣的国际源（如科技、财经、AI、设计等领域的 RSS）
INTL_FEEDS = [
    "https://www.theverge.com/rss/index.xml",           # 示例：科技资讯 The Verge
    "https://hnrss.org/frontpage",                      # 示例：极客论坛 Hacker News
    "https://www.economist.com/finance-and-economics/rss.xml" # 示例：经济学人
    "https://huggingface.co/blog/feed.xml"
    "https://ai.googleblog.com/feeds/posts/default"
    "https://openai.com/blog/rss.xml"
    "https://www.wired.com/feed/category/ai/latest/rss"
    "https://techcrunch.com/category/artificial-intelligence/feed/"
    "	https://www.technologyreview.com/topic/artificial-intelligence/feed/"
]

# 📢 [用户自定义区]：自定义你的周报名称和你的专属身份/格言
REPORT_TITLE = "🌍Yoyo 专属【AI 洞察周报】"
REPORT_SUBTITLE = "每周AI学习量。"

# ==========================================
# 3. 抓取近期更新的 RSS 文章
# ==========================================
def fetch_recent_rss(feed_urls, days_limit=7):
    # 📢 [用户自定义区]：默认抓取过去 7 天的内容，可修改 days_limit 参数
    print(f"📡 正在扫描订阅源，严格筛选过去 {days_limit} 天内的文章...")
    recent_items = []
    limit_date = datetime.now() - timedelta(days=days_limit)
    
    for url in feed_urls:
        try:
            feed = feedparser.parse(url)
            source_name = feed.feed.title if hasattr(feed.feed, 'title') else "精选智库"
            
            for entry in feed.entries:
                try:
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'published'):
                        pub_date = parsedate_to_datetime(entry.published).replace(tzinfo=None)
                    else:
                        continue
                        
                    if pub_date >= limit_date:
                        recent_items.append({
                            "title": entry.title,
                            "url": entry.link,
                            "summary": entry.get("summary", ""),
                            "source": source_name,
                            "pub_date": pub_date
                        })
                except Exception:
                    pass
        except Exception as e:
            print(f"解析 {url} 失败: {e}")
            
    recent_items.sort(key=lambda x: x['pub_date'], reverse=True)
    print(f"✅ 扫描完毕，共发现 {len(recent_items)} 篇新鲜文章。")
    return recent_items

# ==========================================
# 4. Jina 穿透抓取正文 (用于非微信的外部网页)
# ==========================================
def extract_full_text(url):
    jina_url = f"https://r.jina.ai/{url}"
    try:
        response = requests.get(jina_url, timeout=15)
        if response.status_code == 200:
            text = response.text
            if len(text) > 200 and "Access Denied" not in text:
                return text[:3800] 
    except Exception:
        pass
    return "抓取正文受限，请基于标题和摘要进行研判。"

# ==========================================
# 5. DeepSeek 深度剖析 (核心 AI 引擎)
# ==========================================
def analyze_with_deepseek(title, content, source_name):
    # 📢 [用户自定义区]：这是决定 AI 输出质量的灵魂 Prompt。你可以根据自己的需求调整语气和结构！
    prompt = f"""
    你是一位**专注AI产业化的资深投资分析师**，擅长从技术动态中提炼商业价值与战略信号。

    请审读这篇来自【{source_name}】的最新资讯：
    【标题】：{title}
    【正文/摘要】：{content}

    【判定准则】
    1. 如果该内容仅是无实质信息的广告、产品发布通告或旧闻重发，请仅回复“低信息量内容，建议跳过”。
    2. 若内容具备商业或战略分析价值，请按以下结构输出洞察简报。

    【高管视角洞察】
    📌 **一句话要闻**：用最精炼的商业语言概括核心事实（例如：某公司发布某产品，意在抢占某市场）。
    💡 **战略意义分析**：解析该事件对行业竞争格局、商业模式或投资风向的潜在影响。重点回答：**这对我的决策有何启发？**（例如：是否意味着某个技术路线已被验证？竞争对手可能如何应对？）
    🔭 **一个值得关注的信号**：指出该资讯中可能预示未来趋势的隐藏细节或长期影响，引发进一步思考。
    💡 **对生活应用和影视行业的影响**：指出该资讯中可能预示对影视行业相关和普通人生活的影响。
    """
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个能提供高信噪比信息摘要的顶级 AI 知识助理。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "无效资讯"

# ==========================================
# 6. 流水线核心逻辑
# ==========================================
def process_news_pipeline(news_list, section_title, limit=None):
    report_text = f"## {section_title}\n\n"
    valid_count = 0
    
    for item in news_list:
        # 📢 [用户自定义区]：控制每个版块最多输出多少篇文章，防止推送超载
        if limit is not None and valid_count >= limit:
            print(f"🛑 {section_title} 已达到 {limit} 篇上限，停止分析。")
            break
            
        print(f"🧐 评估文章: {item['title'][:30]}... (发布于 {item['pub_date'].strftime('%m-%d')})")
        full_text = extract_full_text(item['url'])
        time.sleep(1.5) # 防止请求过频被封
        
        analysis = analyze_with_deepseek(item['title'], full_text, item['source'])
        
        if "无效资讯" not in analysis:
            valid_count += 1
            report_text += f"### {valid_count}. {item['title']}\n"
            report_text += f"🔗 **原文直达**：[点击阅读全文]({item['url']})\n\n"
            report_text += f"{analysis}\n\n---\n\n"
            
    if valid_count == 0:
        report_text += "> 🛡️ *本周期内暂无符合价值研判标准的新鲜动态。*\n\n---\n\n"
    return report_text

# ==========================================
# 7. 执行与微信推送
# ==========================================
if __name__ == "__main__":
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    raw_domestic = fetch_recent_rss(DOMESTIC_FEEDS)
    raw_intl = fetch_recent_rss(INTL_FEEDS)
    
    # 构建报告头部
    final_report = f"# {REPORT_TITLE}\n\n"
    final_report += f"> 📅 **生成日期**：{today_str}\n"
    final_report += f"> 💡 **订阅说明**：{REPORT_SUBTITLE}\n\n---\n\n"
    
    # 📢 [用户自定义区]：组装报告。这里设置国内最多 15 篇，国际最多 8 篇，可自行修改 limit。
    final_report += process_news_pipeline(raw_domestic, "📌 第一部分：国内精选动态", limit=15)
    final_report += process_news_pipeline(raw_intl, "🌐 第二部分：海外视野观察", limit=20)
    
    # 推送至微信 (使用 HTTPS 防止被拦截)
    try:
        requests.post("https://www.pushplus.plus/send", json={
            "token": PUSHPLUS_TOKEN,
            "title": f"【本周推送】{REPORT_TITLE} - {today_str}",
            "content": final_report,
            "template": "markdown"
        }, timeout=15)
        print("✅ 任务完成，周报已成功发送至微信！")
    except Exception as e:
        print(f"❌ 推送失败，请检查网络或 Token 配置: {e}")
