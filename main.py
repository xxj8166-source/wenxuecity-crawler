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

def get_blogger_all_posts(blogger_name, max_years=1):
    """
    通过文学城官方作者专属URL，定点轰炸该博主的所有发言（包含主帖和回帖、追帖）
    """
    print(f"==========================================")
    print(f"🚀 正在云端深度归档博主 【{blogger_name}】 近 {max_years} 年的所有帖子...")
    print(f"==========================================")
    
    cutoff_date = datetime.now() - timedelta(days=365 * max_years)
    all_extracted_posts = []
    page = 1
    should_continue = True
    
    while should_continue:
        print(f"🔎 正在扫描 【{blogger_name}】 的发言列表第 {page} 页...")
        # 文学城官方作者旧帖追踪核心URL
        search_url = f"https://bbs.wenxuecity.com/cfzh/?author={blogger_name}&page={page}"
        
        try:
            response = requests.get(search_url, headers=HEADERS, timeout=15)
            response.encoding = 'utf-8'
            if response.status_code != 200:
                print(f"❌ 无法访问第 {page} 页，状态码: {response.status_code}")
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            post_links = soup.find_all('a', class_='post')
            
            if not post_links:
                print(f"⏹️ 【{blogger_name}】 第 {page} 页没有更多帖子了，该博主归档完毕。")
                break
                
            for link in post_links:
                title = link.text.strip()
                href = link.get('href', '')
                if not href or "ad" in href:
                    continue
                    
                # 修复文学城URL拼接格式，防止出现双斜杠或点号导致访问失败
                if href.startswith('.'):
                    href = href.lstrip('.')
                if href.startswith('/'):
                    full_url = "https://bbs.wenxuecity.com" + href
                else:
                    full_url = "https://bbs.wenxuecity.com/" + href
                
                # 提取时间
                parent = link.find_parent()
                parent_text = parent.text if parent else ""
                time_span = parent.find('span', class_='time') if parent else None
                date_str = ""
                
                if time_span:
                    date_str = time_span.text.strip()
                else:
                    date_match = re.search(r'\d{4}-\d{2}-\d{2}', parent_text)
                    if date_match:
                        date_str = date_match.group(0)
                
                # 判断时间是否超过1年
                try:
                    if len(date_str) > 10:
                        post_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    else:
                        post_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    if post_date < cutoff_date:
                        print(f"⏱️ 发现历史帖子时间为 {date_str}，已超出1年范围。停止向下翻页。")
                        should_continue = False
                        break
                except:
                    # 如果偶尔拿不到时间，默认保留，防止漏掉重要讨论
                    pass
                
                # 进入帖子内部，连带正文和讨论话题一起下载下来
                print(f"📖 深度提取内文: {title[:15]}...")
                content = fetch_post_content(full_url)
                
                all_extracted_posts.append({
                    "博主": blogger_name,
                    "发布时间": date_str if date_str else "见链接",
                    "帖子标题": title,
                    "帖子链接": full_url,
                    "讨论讨论话题正文": content
                })
                time.sleep(0.6) # 安全延迟，稳定至上
                
            page += 1
            if page > 60: # 每个人最多向下翻60页，确保深度
                break
                
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            break
            
    return all_extracted_posts

def fetch_post_content(post_url):
    """
    点进帖子内部，把大段讨论内容抓出来
    """
    try:
        res = requests.get(post_url, headers=HEADERS, timeout=12)
        res.encoding = 'utf-8'
        if res.status_code == 200:
            inner_soup = BeautifulSoup(res.text, 'html.parser')
            # 精准匹配文学城正文和回帖框包裹层
            content_div = inner_soup.find('div', id='content') or inner_soup.find('div', class_='post_body') or inner_soup.find('div', class_='article')
            if content_div:
                text = content_div.text.strip()
                # 过滤掉多余的系统按钮字符
                text = re.sub(r'\s+', ' ', text)
                return text if text else "[纯标题贴，无内文]"
        return "[无内文或无法提取]"
    except:
        return "[抓取超时，可手动点击链接查看]"

def send_excel_to_telegram(token, chat_id, file_path):
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    print("📤 正在通过 Telegram 机器人发送完整的 Excel 归档文件...")
    try:
        with open(file_path, 'rb') as f:
            files = {'document': f}
            payload = {'chat_id': chat_id, 'caption': '📊 精准归档完成！三心三意、lionhill 近一年所有核心发言及正文长文已全部打包，请查收！'}
            response = requests.post(url, data=payload, files=files)
            return response.json()
    except Exception as e:
        print(f"❌ 发送文件失败: {e}")

if __name__ == "__main__":
    tg_token = os.environ.get("TG_BOT_TOKEN")
    tg_chat_id = os.environ.get("TG_CHAT_ID")
    
    # 🎯 直接锁定这两位核心博主
    BLOGGER_NAMES = ["三心三意", "lionhill"]
    
    all_data = []
    for blogger in BLOGGER_NAMES:
        all_data.extend(get_blogger_all_posts(blogger, max_years=1))
        
    if all_data:
        df = pd.DataFrame(all_data)
        output_file = "财富智汇核心博主年度全量档案.xlsx"
        df.to_excel(output_file, index=False)
        
        send_excel_to_telegram(tg_token, tg_chat_id, output_file)
        print("🎉 任务全部成功结束！")
    else:
        print("❌ 糟糕，未捞到任何数据，请检查配置。")
