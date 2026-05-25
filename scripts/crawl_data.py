import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger

BASE_URL = "https://openaccess.thecvf.com"
CVPR_URL = f"{BASE_URL}/CVPR2025?day=all"
BASE_DIR = Path("cvpr_papers_by_topic")
DOWNLOAD_LIMIT = 30
REQUEST_TIMEOUT = 15

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

KEYWORDS: Dict[str, List[str]] = {
    "GenAI": ["diffusion", "generative", "gan", "generation", "text-to-image", "text-to-video", "llm", "synthesis"],
    "NLP_in_CV": ["language", "text", "caption", "vlm", "prompt", "chat", "multimodal", "dialogue", "translation"],
    "Pure_CV": ["segmentation", "object detection", "tracking", "3d gaussian", "nerf", "depth estimation", "stereo"]
}


class CVPRCrawler:

    def __init__(self, base_dir: Path, limit: int = DOWNLOAD_LIMIT):
        self.base_dir = base_dir
        self.limit = limit
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
    def setup_directories(self) -> None:
        for topic in KEYWORDS.keys():
            topic_dir = self.base_dir / topic
            topic_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Đã đảm bảo thư mục tồn tại: {topic_dir}")

    def fetch_paper_list(self) -> tuple[List[str], List[str]]:
        logger.info(f"Đang kết nối đến cơ sở dữ liệu CVPR tại {CVPR_URL}...")
        try:
            res = self.session.get(CVPR_URL, timeout=REQUEST_TIMEOUT)
            res.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Lỗi kết nối tới trang CVPR: {e}")
            raise SystemExit(1)

        soup = BeautifulSoup(res.text, 'html.parser')
        
        title_tags = soup.find_all('dt', class_='ptitle')
        
        titles = []
        pdf_links = []
        
        for dt in title_tags:
            titles.append(dt.text.strip())
            
            dds = dt.find_next_siblings('dd', limit=2)
            pdf_link = None
            for dd in dds:
                a_tag = next((a['href'] for a in dd.find_all('a') if a.text.lower() == 'pdf'), None)
                if a_tag:
                    pdf_link = f"{BASE_URL}{a_tag}"
                    break
            
            pdf_links.append(pdf_link or "")

        logger.info(f"Tìm thấy tổng cộng {len(titles)} bài báo. Bắt đầu quá trình lọc...")
        return titles, pdf_links

    def _categorize_paper(self, title: str) -> Optional[str]:
        title_lower = title.lower()
        for topic, words in KEYWORDS.items():
            if any(word in title_lower for word in words):
                return topic
        return None

    def _sanitize_filename(self, filename: str) -> str:
        safe_name = re.sub(r'[^\w\s-]', '', filename).strip()
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        return safe_name[:150]

    def download_papers(self, titles: List[str], pdf_links: List[str]) -> None:
        downloaded_count = 0
        
        for idx, title in enumerate(titles):
            if downloaded_count >= self.limit:
                logger.success(f"Đã chạm ngưỡng giới hạn tải {self.limit} bài báo.")
                break
                
            pdf_url = pdf_links[idx]
            if not pdf_url:
                continue
                
            topic = self._categorize_paper(title)
            if not topic:
                continue
                
            logger.info(f"[{downloaded_count + 1}/{self.limit}] Chủ đề [{topic}]: {title}")
            
            safe_title = self._sanitize_filename(title)
            file_path = self.base_dir / topic / f"{safe_title}.pdf"
            
            if file_path.exists():
                logger.debug(f"Bài báo đã tồn tại (Skip): {file_path.name}")
                continue

            try:
                pdf_res = self.session.get(pdf_url, timeout=REQUEST_TIMEOUT)
                pdf_res.raise_for_status()
                
                with open(file_path, 'wb') as f:
                    f.write(pdf_res.content)
                
                logger.success(f"-> Tải thành công vào: {topic}/")
                downloaded_count += 1
            except requests.RequestException as e:
                logger.error(f"-> Gặp lỗi khi tải bài này: {e}")
                
        logger.info(f"Quá trình hoàn tất! Đã gom đủ {downloaded_count} tài liệu chuẩn chỉ.")

def main():
    crawler = CVPRCrawler(base_dir=BASE_DIR, limit=DOWNLOAD_LIMIT)
    crawler.setup_directories()
    
    titles, pdf_links = crawler.fetch_paper_list()
    
    if len(titles) == len(pdf_links):
        crawler.download_papers(titles, pdf_links)
    else:
        logger.error(f"Lệch dữ liệu: Số lượng titles ({len(titles)}) khác links ({len(pdf_links)}).")

if __name__ == "__main__":
    main()