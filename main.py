import json
from datetime import datetime
from typing import Dict, Any
from bs4 import BeautifulSoup
import logging
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ZalandoMonitor:
    def __init__(self, product_url: str):

        self.product_url = product_url
        self.product_data: Dict[str, Any] = {}
        self.session = self._create_session()

    def _create_session(self):
        session = requests.Session()

        # Default 
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'da-DK,da;q=0.9',
        })

        retry_strategy = Retry(
            total=2,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def fetch_product_page(self) -> str:
        logger.info(f"Fetching: {self.product_url}")

        # User-Agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'da-DK,da;q=0.9,en-US;q=0.8,en;q=0.7',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }

        try:
            response = self.session.get(self.product_url, headers=headers, timeout=10, allow_redirects=True)
            logger.info(f"Status: {response.status_code}")

            if response.status_code == 200:
                logger.info(f"Successfully fetched {len(response.text)} bytes")
                return response.text
            else:
                logger.warning(f"Got status {response.status_code}")
                return ""
        except Exception as e:
            logger.error(f"Error fetching page: {e}")
            return ""
    
    def parse_product_data(self, html_content: str) -> Dict[str, Any]:
        # Returns a dictionary: if there is loot, returns it; otherwise, returns an empty dictionary.
        product_data = {
            "url": self.product_url,
            "fetched_at": datetime.now().isoformat(),
            "product_name": None,
            "brand": None,
            "price": None,
            "available_sizes": [],
            "all_sizes": [],
            "images": [],
            "product_id": None,
            "color": None,
            "in_stock": False,
            "stock_status": "Out of Stock",
        }

        if not html_content:
            logger.warning("No HTML content to parse")
            return product_data

        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Product ID
            url_slug = self.product_url.split('/')[-1].replace('.html', '')
            product_id_match = re.search(r'([a-z0-9]{8,})-[a-z0-9]+$', url_slug)
            if product_id_match:
                product_data["product_id"] = product_id_match.group(1)

            name_parts = url_slug.split('-')
            if name_parts:
                product_data["brand"] = name_parts[0].title()
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content', '')
                if ' - ' in title:
                    product_data["product_name"] = title.split(' - ')[0].strip()
                else:
                    product_data["product_name"] = title.split('|')[0].strip()

            color_pattern = r'"color":\s*"([^"]+)"'
            colors = re.findall(color_pattern, html_content)
            if colors:
                # First unique color, changeable
                product_data["color"] = colors[0]
                logger.info(f"Found color: {product_data['color']}")

            # Price regex
            price_match = re.search(r'(\d+[.,]\d{2})\s*kr', html_content)
            if price_match:
                product_data["price"] = price_match.group(1)
                logger.info(f"Found price: {product_data['price']}")

            images = soup.find_all('img', {'src': re.compile(r'img\d+\.ztat\.net|mosaic.*\.jpg')})
            for img in images[:20]:
                src = img.get('src', '')
                if src and src not in product_data["images"]:
                    product_data["images"].append(src)
            logger.info(f"Found {len(product_data['images'])} images")

            # Sizes regex
            size_pattern = r'"size":\s*"(\d+(?:\.\d+)?)"'
            sizes = re.findall(size_pattern, html_content)
            if sizes:
                product_data["all_sizes"] = sorted(list(set(sizes)), key=lambda x: float(x))
                product_data["available_sizes"] = product_data["all_sizes"]
                logger.info(f"Found {len(product_data['all_sizes'])} sizes: {product_data['all_sizes']}")
            else:
                # Fallback
                all_buttons = soup.find_all('button')
                for btn in all_buttons:
                    size_text = btn.get_text(strip=True)
                    #EU sizes
                    if size_text and (size_text.isdigit() or (len(size_text) <= 3 and size_text.replace('.', '').isdigit())):
                        if size_text not in product_data["all_sizes"]:
                            product_data["all_sizes"].append(size_text)
                            # Available?
                            is_disabled = btn.get("disabled") or "disabled" in btn.get("class", [])
                            if not is_disabled:
                                product_data["available_sizes"].append(size_text)

            product_data["in_stock"] = len(product_data["available_sizes"]) > 0
            product_data["stock_status"] = "In Stock" if product_data["in_stock"] else "Out of Stock"

            logger.info(f"Successfully parsed product: {product_data['product_name']}")
            logger.info(f"Available sizes: {product_data['available_sizes']}")

        except Exception as e:
            logger.error(f"Error parsing product data: {e}")

        return product_data
    
    def monitor(self) -> Dict[str, Any]:
       # Returns Dictionary containing all information of the product
        try:
            html_content = self.fetch_product_page()
            self.product_data = self.parse_product_data(html_content)
            return self.product_data

        except Exception as e:
            logger.error(f"Error during monitoring: {e}")
            raise
    
    def save_to_json(self, filename: str = "zalando_product.json") -> None:
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.product_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Product data saved to {filename}")
        
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
            raise
def main():
    product_url = "https://www.zalando.dk/adidas-originals-samba-og-unisex-sneakers-brownputty-greygold-metallic-ad115o1rq-o11.html"
    output_file = "zalando_product.json"
    monitor = ZalandoMonitor(product_url)
    logger.info("Starting product monitoring...")
    product_data = monitor.monitor()
    monitor.save_to_json(output_file)


    print(f"File: {output_file}")
if __name__ == "__main__":
    main()

