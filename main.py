import os
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://bbs.wenxuecity.com/cfzh/"
}

def get_posts_by_blogger(blogger_name, max_years=1):
    print(f"🚀 开始云端抓取博主 【{blogger_name}】 近 {max_years} 年的历史帖子...")
    cutoff_date = datetime.now() - timedelta(days=365 * max_years)
    all_extracted_posts = []
    page = 1
    should_continue = True
    
    while should_continue:
        print(f"🔎 正在扫描 【{blogger_name}】 的第 {page} 页...")
        search_url = f"https://bbs.wenxuecity.com/cfzh/?author={blogger_name}&page={page}"
        
        try:
            response = requests.get(search_url, headers=HEADERS, timeout=15)
            response.encoding = 'utf-8'
            if response.status_code != 200:
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            post_links = soup.find_all('a', class_='post')
            if not post_links:
                break
                
            for link in post_links:
                title = link.text.strip()
                href = link.get('href', '')
                if not href or "ad" in href:
                    continue
                    
                full_url = "https://bbs.wenxuecity.com" + href
                parent = link.find_parent()
                parent_text = parent.text if parent else ""
                time_span = parent.find('span', class_='time') if parent else None
                date_str = ""
                
                if time_span:
                    date_str = time_span.text.strip()
                else:
                    import re
                    date_match = re.search(r'\d{4}-\d{2}-\d{2}', parent_text)
                    if date_match:
                        date_str = date_match.group(0)
                
                try:
                    if len(date_str) > 10:
                        post_date = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    else:
                        post_date = datetime.strptime(date_str, "%Y-%m-%d")
                except:
                    post_date = datetime.now() 
                
                if post_date < cutoff_date:
                    print(f"⏱️ 发现历史帖子时间为 {date_str}，已超出1年范围。停止翻页。")
                    should_continue = False
                    break
                
                content = fetch_post_content(full_url)
                all_extracted_posts.append({
                    "博主": blogger_name,
                    "发布时间": date_str,
                    "帖子标题": title,
                    "帖子链接": full_url,
                    "帖子正文": content
                })
                time.sleep(1) # 频率控制
                
            page += 1
            if page > 50:
                break
        except Exception as e:
            print(f"❌ 错误: {e}")
            break
            
    return all_extracted_posts

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
    """把生成的 Excel 文件通过 TG 机器人直接发送给用户"""
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    print("📤 正在通过 Telegram 机器人发送 Excel 文件...")
    try:
        with open(file_path, 'rb') as f:
            files = {'document': f}
            payload = {'chat_id': chat_id, 'caption': '📊 文学城博主一年历史帖子整理已完成，请查收！'}
            response = requests.post(url, data=payload, files=files)
            return response.json()
    except Exception as e:
        print(f"❌ 发送文件失败: {e}")

if __name__ == "__main__":
    tg_token = os.environ.get("TG_BOT_TOKEN")
    tg_chat_id = os.environ.get("TG_CHAT_ID")
    
    # 📝 在这里修改你想抓取的博主名字
    BLOGGER_NAMES = ["三心三意", "lionhill"]
    
    all_data = []
    for blogger in BLOGGER_NAMES:
        all_data.extend(get_posts_by_blogger(blogger, max_years=1))
        
    if all_data:
        df = pd.DataFrame(all_data)
        output_file = "文学城博主一年历史帖子整理.xlsx"
        df.to_excel(output_file, index=False)
        
        # 调用机器人发货
        send_excel_to_telegram(tg_token, tg_chat_id, output_file)
        print("🎉 任务完全结束！")
    else:
        print("❌ 未抓取到任何数据")
