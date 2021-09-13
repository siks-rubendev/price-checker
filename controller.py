import colorama
import json
import re
import requests
from bs4 import BeautifulSoup
from termcolor import colored
from time import sleep, time

colorama.init()

s = requests.session()            
#Development purposes (Uncomment if using Charles Proxy)
""" CHARLES_CERTIFICATE = './charles-cert/charles-cert.pem'
LOCAL = {'https': 'http://127.0.0.1:8888'}
s.verify = CHARLES_CERTIFICATE
s.proxies.update(LOCAL)
s.trust_env = False """

restocks_list, stockx_list, klekt_list, goat_list = [], [], [], []


def search_shoes(param):
    try:
        paint('Looking for matches...', 'yellow')
        r = s.get(f'https://restocks.net/es/shop/search?q={param}&page=1&filters[][range][price][gte]=1')
        return r
    except Exception as e:
        paint(f'Something went wrong. {e}', 'red')


def scrape_restocks(url):
    while 1:
        try:
            r = s.get(url)
            if r.status_code == 200:
                sizes, sizes_list = get_sizes_restocks(r.text)
                global restocks_list
                restocks_list = sizes_list
                return
            else:
                continue
        except Exception as e:
            paint(f'Something went wrong on Restocks. {e}', 'red')
            sleep(1.5)


def get_sizes_restocks(text):
    sizes = {}
    sizes_list = []

    soup = BeautifulSoup(text, 'html.parser')
    ul_sizes = soup.find('ul', {'class': 'select__size__list'})
    li_list = ul_sizes.findChildren('li')
                
    for li in li_list:
        size = li.findChildren('span')[0].string

        if size in sizes.keys():
            break

        price_parent = li.findChildren('span')[2]
        price = price_parent.findChildren('span')

        if not price:
            price = 'Not available'
        else:
            price = price[0].string
            price = price.replace('€ ', '') + '€'

        if '½' in size:
            size = size.replace(' ½', '.5')
        
        sizes[size] = price
        size_price = (size, price)

        for key, value in sizes_list:
            if key == size:
                return sizes, sizes_list

        sizes_list.append(size_price)  
                
    return sizes, sizes_list
    

def scrape_stockx(sku):
    #Step check: Just for security purposes we make one plain request to the main page.
    fheaders = {
        'sec-ch-ua':	'"Google Chrome";v="93", " Not;A Brand";v="99", "Chromium";v="93"',
        'sec-ch-ua-mobile':	'?0',
        'sec-ch-ua-platform':	'"Windows"',
        'upgrade-insecure-requests':	'1',
        'user-agent':	'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
        'accept':	'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-fetch-site':	'none',
        'sec-fetch-mode':	'navigate',
        'sec-fetch-user':	'?1',
        'sec-fetch-dest':	'document',
        'accept-encoding':	'gzip, deflate, br',
        'accept-language':	'es-ES,es;q=0.9'
    }
    r = s.get('https://stockx.com', headers = fheaders)

    headers = {
        'sec-ch-ua':	'"Google Chrome";v="93", " Not;A Brand";v="99", "Chromium";v="93"',
        'appos': 'web',
        'sec-ch-ua-mobile':	'?0',
        'authorization':	'',
        'user-agent':	'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
        'x-requested-with':	'XMLHttpRequest',
        'sec-ch-ua-platform':	'"Windows"',
        'appversion':	'0.1',
        'accept':	'*/*',
        'sec-fetch-site':	'same-origin',
        'sec-fetch-mode':	'cors',
        'sec-fetch-dest':	'empty',
        'referer': 	f'https://stockx.com/search/sneakers?s={sku}',
        'accept-encoding':	'gzip, deflate, br',
        'accept-language':	'es-ES,es;q=0.9'
    }

    base_api_url = f'https://stockx.com/api/browse?productCategory=sneakers&currency=EUR&_search={sku}&dataType=product'
    while 1:
        try:
            api_response = s.get(base_api_url, headers = headers)
            if api_response.status_code == 200:
                product_api = api_response.json()
                if len(product_api['Products']) == 0:
                    return
                url_key = product_api['Products'][0]['urlKey']
                break
            else:
                paint(f'Request failed on StockX (Search API), Retrying... {api_response.status_code}', 'red')
                sleep(1.5)

        except Exception as e:
            paint(f'Something went wrong on Stockx. {e}', 'red')
            sleep(1.5)

    product_api_url = f'https://stockx.com/api/products/{url_key}?includes=market,360&currency=EUR&country=ES'

    sizes_total = []
    sizes = {}
    sizes_list = []

    while 1:
        try:
            product_api_response = s.get(product_api_url, headers = headers)

            if product_api_response.status_code == 200:
                json_info = product_api_response.json()

                for child in json_info['Product']['children']:
                    size = json_info['Product']['children'][child]['shoeSize']
                    lowest_ask = json_info['Product']['children'][child]['market']['lowestAsk']
                    highest_bid = json_info['Product']['children'][child]['market']['highestBid']
                    price = str(lowest_ask) + '€'

                    size_object = (size,  lowest_ask, highest_bid)
                    sizes_total.append(size_object)

                    sizes[size] = price

                    size_price = (size, price)
                    sizes_list.append(size_price) #This is the one I use for building the table.

                    
                break
            else:
                paint(f'Request failed on StockX (Result API - PROBS PX HITTING), Retrying... {product_api_response.status_code}', 'red')
                sleep(1.5)
                
        except Exception as e:
            paint('Something went wrong while scraping StockX... {e}', 'red')
            sleep(1.5)

    #Toda la info sobre cada una de las tallas la tengo en json_info['Product]['children'][child]['market']

    global stockx_list
    stockx_list = sizes_list
    return


def scrape_klekt(sku):

    base_api_url = 'https://apiv2.klekt.com/shop-api?vendure-token=iqrhumfu2u9mumwq369'
    
    headers = {
        'sec-ch-ua':	'"Google Chrome";v="93", " Not;A Brand";v="99", "Chromium";v="93"',
        'accept':	'application/json, text/plain, */*',
        'content-type':	'application/json;charset=UTF-8',
        'sec-ch-ua-mobile':	'?0',
        'user-agent':	'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
        'sec-ch-ua-platform': '"Windows"',
        'origin':	'https://www.klekt.com',
        'sec-fetch-site':	'same-site',
        'sec-fetch-mode':	'cors',
        'sec-fetch-dest':	'empty',
        'referer':	'https://www.klekt.com/',
        'accept-encoding':	'gzip, deflate, br',
        'accept-language'	:'es-ES,es;q=0.9'
    }

    payload = {
        "operationName": "SearchProducts",
        "variables": {
            "input": {
                "term": str(sku),
                "sizeType": 0,
                "facetValueIds": [],
                "groupByProduct": True,
                "brandSlugs": [],
                "brandLineSlugs": [],
                "categorySlugs": [],
                "availability": "available",
                "take": 48,
                "skip": 0,
                "sort": {
                    "featured": "DESC"
                },
                "showWithoutSizeSet": False,
                "conditions": ["new"],
                "boxConditionSlugs": [],
                "itemConditionSlugs": []
            }
        },
        "query": "query SearchProducts($input: SearchInput!) {\n  search(input: $input) {\n    items {\n      productId\n      slug\n      styleCode\n      categoryNames\n      brandNames\n      brandLineNames\n      productName\n      description\n      variantsCount\n      sameDayShipping\n      sdsPriceWithTaxMin\n      styleCode\n      sizeType\n      conditions {\n        condition\n      }\n      customMappings {\n        ... on CustomProductMappings {\n          featured\n          new\n        }\n      }\n      priceWithTax {\n        ... on PriceRange {\n          min\n          max\n        }\n      }\n      productAsset {\n        id\n        preview\n      }\n    }\n    totalItems\n  }\n}\n"
    }

    sizes = {}
    sizes_list = []
    while 1:
        try:
            api_post_response = s.post(base_api_url, headers=headers, json = payload)
            if api_post_response.status_code == 200:
                product_data = api_post_response.json()
                if product_data['data']['search']['totalItems'] == 0:
                    return [], []

                product_id = product_data['data']['search']['items'][0]['productId']
                url_identifier = product_data['data']['search']['items'][0]['slug']

                payload = {
                    "query": "query ProductDetails($productId: ID!) {\n  productDetails(id: $productId) {\n    name\n    id\n    slug\n    description\n    conditions {\n      condition\n      minPrice\n    }\n    featuredAsset {\n      preview\n    }\n    assets {\n      asset {\n        id\n        preview\n        name\n      }\n      position\n    }\n    customFields {\n      new\n      featured\n      styleCode\n    }\n    facetValues {\n      code\n    }\n    variants {\n      id\n      customFields {\n        sameDayShipping\n      }\n      availableCount\n      priceWithTax\n      facetValues {\n        code\n        name\n        id\n        facet {\n          code\n        }\n      }\n    }\n    variantsNDD {\n      id\n      customFields {\n        sameDayShipping\n      }\n      availableCount\n      priceWithTax\n      facetValues {\n        code\n        name\n        id\n        facet {\n          code\n        }\n      }\n    }\n  }\n}\n",
                    "variables": {
                        "productId": product_id
                    }
                }

                api_product_response = s.post(base_api_url, headers = headers, json = payload)
                if api_product_response.status_code == 200:
                    product_data = api_product_response.json()
                    for variant in product_data['data']['productDetails']['variants']:
                        price = variant['priceWithTax']
                        size = variant['facetValues'][0]['code']
                        
                        price = str(price)[:-2]
                        price = price + '€'
                        size = size.replace('us', '')
                        size = size.replace('y', '')

                        size_price = (size, price)
                        sizes_list.append(size_price)

                        sizes[size] = price

                    global klekt_list
                    klekt_list = sizes_list
                    return
                    
        except Exception as e:
            paint(f'Something went wrong on Klekt. Retrying... {e}', 'red')
            sleep(1.5)
      

def paint(text, color):
    print(colored(text,color))


def return_restocks():
    return restocks_list


def return_stockx():
    return stockx_list


def return_klekt():
    return klekt_list


def return_goat():
    return goat_list


#Goat renders its page dynamically, using a bunch of js files, where script tags are also loaded dynamically. 
#In the first place, I need the product 'slug' to be able to perform the right request to the GOAT API.
#I can find the slug under an 'a' tag (href value), once the search page is fully loaded.
#Once I have the slug of the product, its just performing the correct requests to the API.
def scrape_goat(sku):

    base_search_url = f'https://www.goat.com/search?query={sku}' 

    headers = {
        'sec-ch-ua':	'"Google Chrome";v="93", " Not;A Brand";v="99", "Chromium";v="93"',
        'sec-ch-ua-mobile':	'?0',
        'sec-ch-ua-platform':	'"Windows"',
        'upgrade-insecure-requests':	'1',
        'user-agent':	'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
        'accept':	'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-fetch-site':	'none',
        'sec-fetch-mode':	'navigate',
        'sec-fetch-user':	'?1',
        'sec-fetch-dest':	'document',
        'accept-encoding':	'gzip, deflate, br',
        'accept-language':	'es-ES,es;q=0.9'
    }

    search_page_response = s.get(base_search_url, headers = headers)
    soup = BeautifulSoup(search_page_response.text, 'html.parser')

    start = time()
    for element in soup.find_all('a'):
        print(element)
        sleep(0.2)
        if re.search(f'{sku}$', element['href']):
            print(element['href'])
    end = time()
    print('Elapsed time, ', end-start)
