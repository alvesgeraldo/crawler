import requests
import logging
from datetime import datetime
from bs4 import BeautifulSoup

from apify import Actor

class CrawlerXornal:
    def __init__(self, config):
        self.config = config

        self.base_url = self.config['base_url']
        self.months_string_int = {
          'xan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'mai': 5, 'xun': 6, 'xul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dec': 12
        }

    def fetch_page(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            print(f'Error fetching {url}: {e}')
            return None

    def parse_html(self, content):
        return BeautifulSoup(content, 'html.parser')

    def format_date(self, day, month, year):
        month = self.months_string_int.get(month.lower(), 0)
        date_obj = datetime(int(year), month, int(day))
        date = date_obj.strftime('%Y-%m-%d %H:%M:%S')

        return date

    def extract_title_and_description(self):
        content = self.fetch_page(self.base_url)

        if content:
            soup = self.parse_html(content)

            title = soup.find('title').text if soup.find('title').text else 'Not found title'
            meta_description_elem = soup.find('meta', {'name': 'description'})
            description = meta_description_elem['content'] if meta_description_elem['content'] else 'Not found description'

        return title, description

    def get_link_articles(self):
        link_articles = []

        content = self.fetch_page(self.config['startUrls'][0]['url'])

        if content:
            soup = self.parse_html(content)
            articles_elements = soup.select('h2 a')

            for a in articles_elements:
                link_articles.append(a['href'])

        return link_articles

    def extract_data_articles(self, link_articles):
        content_articles = []

        for article in link_articles:
            content = self.fetch_page(article)

            if not content:
                continue

            soup = self.parse_html(content)
            # get article
            article_content = soup.find('article', class_='post')

            #get title
            title = article_content.find('h1', class_='title').text.strip()

            #get publication date
            date = article_content.find('div', class_='dateText')
            if date:
                day = date.find('span', class_='dayMonth').text.strip()
                month = date.find('span', class_='month').text.strip()
                year = date.find('span', class_='year').text.strip()

                date = self.format_date(day, month, year)

            # get description
            description = ''
            content_div = article_content.find('div', class_='content')
            if content_div:
                paragraphs = content_div.find_all('p')
                description = ' '.join(paragraph.text.strip() for paragraph in paragraphs)

            #get images
            media = []
            images = article_content.find_all('figure')
            for image in images:
                img = image.find('img')
                media.append(img['src'])

            # get categories
            categories = []
            categories_ul = article_content.find('ul', class_='categories')
            if categories_ul:
                categories_a = categories_ul.find_all('a')
                categories = [category.text.strip() for category in categories_a]

            content_article = {
                'link': article,
                'title': title,
                'publication_date': date,
                'author': 'Xornal Vigo',
                'description': description,
                'categories': categories,
                'media': media
            }

            content_articles.append(content_article)

        return content_articles

    def get_or_create_website(self, website_data):
        result = self.db.check_website(website_data['name'])

        if result:
            website_id = result[0]
            logging.info("Website already exists, using existing ID.")
        else:
            website_id = self.db.insert_website(website_data)
            logging.info("New website inserted.")

        return website_id

    def run_crawler(self):
        logging.info("Starting crawler...")
        logging.info("Extracting title and description data")
        title, description = self.extract_title_and_description()
        inserted_at = datetime.now()

        website_data = {
            'name': 'xornalvigo',
            'link': self.config['startUrls'][0]['url'],
            'title': title,
            'description': description,
            'inserted_at': inserted_at
        }

        print(website_data)

        # website_id = self.get_or_create_website(website_data)
        link_articles = self.get_link_articles()
        print(link_articles)
        articles = self.extract_data_articles(link_articles)

        if not articles:
            logging.warning("No articles were found.")
        else:
            processed_results = [{
                'article': {**article, 'website_id': 0}
            } for article in articles]

            print(f'Processed {len(processed_results)} results.')
            print(processed_results)
            # self.insert_results_db(processed_results)
            # logging.info('Data inserted into DB.')

async def main() -> None:

    async with Actor:
        Actor.log.info('CrawlerXornalVigo started.')

        config = await Actor.get_input()

        crawler = CrawlerXornal(config)
        crawler.run_crawler()

        Actor.log.info('CrawlerXornalVigo finished.')
