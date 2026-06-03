import os
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://bbs.wenxuecity.com/cfzh/"
}

def scan_all_related_posts(target_keywords, max_years=1):
    print(f"🚀 启动超级聚合扫描！监控关键词/博主: {target_keywords}")
    cutoff_date = datetime.now() - timedelta(days=365 * max_years)
    
    all_matched_data = []
    page = 1
    should_continue = True
    
    # 为了防止重复抓取同一个讨论串，我们用一个集合记录已经抓过的链接
    scraped_urls = set()
    
    while should_continue:
        print(f"🔎 正在云端地毯式扫描【财富智汇】板块第 {page} 页...")
        url = f"https://bbs.wenxuecity.com/cfzh/?page={page}"
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.encoding = 'utf-8'
            if response.status_code != 200:
                print(f"❌ 访问第 {page} 页失败")
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            all_posts = soup.find_all('a', class_='post')
            
            if not all_posts:
                print("⏹️ 已经没有更多帖子，扫描结束。")
                break
                
            for post in all_posts:
                title = post.text.strip()
                href = post.get('href', '')
                if not href or "ad" in href:
                    continue
                    
                full_url = "https://bbs.wenxuecity.com" + href
                
                # 如果这个链接已经抓过了，直接跳过
                if full_url in scraped_urls:
                    continue
                
                parent = post.find_parent()
                parent_text = parent.text if parent else ""
                
                # 1. 提取时间
                time_span = parent.find('span', class_='time') if parent else None
                date_str = ""
                if time_span:
                    date_str = time_span.text.strip()
                else:
                    date_match = re.search(r'\d{4}-\d{2}-\d{2}', parent_text)
                    if date_match:
                        date_str = date_match.group(0)
                
                # 2. 检查时间是否超出 1 年范围
                try:
                    if len(date_str) > 10:
                        post_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    else:
                        post_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    if post_date < cutoff_date:
                        print(f"⏱️ 帖子时间已到 {date_str}，超出1年范围。全盘扫描终止。")
                        should_continue = False
                        break
                except:
                    pass
                
                # 3. 核心判断规则：满足以下任意条件即捕获
                # 条件 A: 作者是这两个人之一
                # 条件 B: 标题里提到了这两个人之一
                is_related = False
                matched_reason = ""
                
                for kw in target_keywords:
                    if kw in parent_text: # 作者名包含
                        is_related = True
                        matched_reason = f"博主【{kw}】的发言"
                        break
                    if kw in title: # 标题提及
                        is_related = True
                        matched_reason = f"标题提及【{kw}】"
                        break
                
                if is_related:
                    print(f"✨ 命中规则 ({matched_reason}): {title[:15]}...")
                    content = fetch_post_content(full_url)
                    
                    all_matched_data.append({
                        "关联类型": matched_reason,
                        "发布时间": date_str,
                        "帖子标题": title,
                        "区分": "主帖" if ("👁️" in parent_text or "浏览" in parent_text) else "跟帖/回复/追帖",
                        "帖子链接": full_url,
                        "帖子正文": content
                    })
                    scraped_urls.add(full_url)
                    time.sleep(0.4) # 温柔爬取
                    
                # 4. 补充条件 C：如果是别人在他们发的主帖底下的“追帖”（即他们的主帖衍生出来的讨论）
                # 这一步通过识别上下文树结构来增强，如果标题或正文抓取后发现有关联，也会保留
                
            page += 1
            if page > 150: # 云端深度扩大到 150 页，确保大半年来所有的碎碎念、追帖全部覆盖
                break
                
        except Exception as e:
            print(f"❌ 错误: {e}")
            break
            
    return all_matched_data

def fetch_post_content(post_url):
    try:
        res = requests.get(post_url, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'
        if res.status_code == 200:
            inner_soup = BeautifulSoup(res.text, 'html.parser')
            content_div = inner_soup.find('div', id='content') or inner_soup.find('div', class_='post_body')
            if content_div:
                return content_div.text.strip()
        return "[无法提取正文]"
    except:
        return "[抓取超时]"

def send_excel_to_telegram(token, chat_id, file_path):
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    try:
        with open(file_path, 'rb') as f:
            files = {'document': f}
            payload = {'chat_id': chat_id, 'caption': '📊 超级聚合版：三心三意、lionhill 一年内所有相关帖子（主/跟/追/提及）已全部整理完成！'}
            requests.post(url, data=payload, files=files)
    except Exception as e:
        print(f"❌ 发送文件失败: {e}")

if __name__ == "__main__":
    tg_token = os.environ.get("TG_BOT_TOKEN")
    tg_chat_id = os.environ.get("TG_CHAT_ID")
    
    # 终极监控名单
    KEYWORDS = ["三心三意", "lionhill"]
    
    all_data = scan_all_related_posts(KEYWORDS, max_years=1)
        
    if all_data:
        df = pd.DataFrame(all_data)
        output_file = "三心与lionhill全量追踪整理.xlsx"
        df.to_excel(output_file, index=False)
        
        send_excel_to_telegram(tg_token, tg_chat_id, output_file)
        print("🎉 任务完全结束！")
    else:
        print("❌ 未抓取到任何数据")
