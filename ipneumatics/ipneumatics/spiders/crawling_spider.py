import time

from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy import Request
from scrapy_selenium import SeleniumRequest
from selenium_profiles.webdriver import Chrome
from selenium_profiles.profiles import profiles
from seleniumwire import webdriver
from scrapy import Selector

BASE_URL = "https://www.tme.eu"


class CrawlingSpider(CrawlSpider):
    item_count = 0

    count = 0
    name = "mycrawler"
    allowed_domains = ["tme.eu"]
    start_urls = ["https://www.tme.eu/am/en/linecard/p,omron_186"]

    rules = (
        Rule(LinkExtractor(allow='https://www.tme.eu/am/en/linecard/p,omron_186'), callback="parse_links"),
    )

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        profile = profiles.Windows()
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        self.driver = Chrome(profile, options=options,
                             uc_driver=False
                             )
        self.driver.implicitly_wait(3)

    def parse_links(self, response):
        parse_links = response.xpath(
            "//div[@class='o-body-container']/div/div/a[contains(@href,'omron')]/@href").getall()
        parse_text = response.xpath(
            "//div[@class='o-body-container']/div/div/a[contains(@href,'omron')]/text()").getall()
        parse_text = [t.replace('\n', '').replace(' ', '').replace('\r', '').replace('\t', '') for t in parse_text]
        while '' in parse_text:
            parse_text.remove('')
        parse_text = [t[:t.find('(')] for t in parse_text]
        for parse_link, category in zip(parse_links, parse_text):
            # if self.item_count > 50:
            #     return

            yield response.follow(BASE_URL + parse_link, callback=self.parse_page, dont_filter=True, meta={'category':category})

    def parse_page(self, response):
        category = response.meta.get('category')
        product_links = response.xpath("//div[contains(@class, 'gSOyD')]//h4/a/@href").getall()
        next_button = "//*[@class='o-pagination-bar__nav-button o-pagination-bar__nav-button--next']/@href"
        next_page = response.xpath(next_button).get()
        if next_page:
            url = response.url
            if "?page=" in response.url:
                url = response.url[:response.url.find("?page=")]
            yield response.follow(url + next_page, callback=self.parse_page, dont_filter=True,  meta={'category':category})

        for product_link in product_links:
            # if self.item_count > 50:
            #     return
            yield SeleniumRequest(url=BASE_URL + product_link, callback=self.parse_item, wait_time=10, meta={'category':category})

    def parse_item(self, response):
        self.item_count += 1
        # if self.item_count > 50:
        #     return
        item_name = response.xpath('//h1//text()').get()
        price = self.get_price(response.url)

        image_link = self.get_image_link(response, item_name)
        description = self.get_description(response)
        serial_number = response.xpath(
            "//h2//*[contains(text(), 'Manufacturer part number: ')]/../span[2]/text()").get()
        summary = response.xpath("//h2//*[contains(text(), 'Manufacturer part number: ')]/../../h2[1]//text()").get()
        category = response.meta.get('category')
        if image_link:
            yield Request(image_link, callback=self.download_image, cb_kwargs={"image_name": serial_number},
                          dont_filter=True)
        print("Parsed item count:", self.item_count)
        print("Parsed item:", response.url)

        yield {
            "item_name": item_name,
            "price": price,
            "serial_number": serial_number,
            "summary": summary,
            "category": category,
            "image_link": image_link,
            "item_link": response.request.url,
            **description
        }

    def get_price(self, url):
        self.driver.get(url)
        time.sleep(2)
        page_source = self.driver.page_source
        price = Selector(text=page_source).xpath("//*[contains(text(), '1+')]/..//span/text()").get()
        return price

    def download_image(self, response, image_name):
        if response.status == 200:
            file_path = rf'/home/ubuntu/Desktop/scrap_web/images/{image_name}.jpg'
            with open(file_path, 'wb') as file:
                file.write(response.body)

    def get_image_link(self, response, name):
        try:
            return response.xpath(f"//img[contains(@alt,'{name}')]/@src").get()
        except Exception as e:
            print(e)
            return None

    def get_description(self, response):
        try:
            description = response.xpath("//table/..")
            description_table = description[0]
            # parse description table
            data = {}
            description_table_data = description_table.xpath('//tbody/tr').getall()

            for item in description_table_data:
                tmp = Selector(text=item).xpath("//text()").getall()
                if len(tmp) == 2:
                    data.update({tmp[0]: tmp[1]})
                else:
                    data.update({tmp[0]: str(tmp[1:])})

            # parse desc rest part
            description_rest = description.xpath('//table/../div')[1:-2].getall()
            for item in description_rest:
                tmp = Selector(text=item).xpath("//text()").getall()
                if len(tmp) == 2:
                    data.update({tmp[0]: tmp[1]})
                else:
                    data.update({tmp[0]: str(tmp[1:])})
            return data

        except Exception as e:
            print(e)
            return None

    def __del__(self):
        print(self.item_count, ": items were parsed!!!")
