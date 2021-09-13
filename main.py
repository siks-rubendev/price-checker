import threading
import colorama
import json
from controller import search_shoes, scrape_goat, scrape_klekt, scrape_restocks, scrape_stockx, return_klekt, return_restocks, return_stockx
from tabulate import tabulate
from termcolor import colored
import time
import datetime
import multiprocessing

colorama.init()


def main():
    sku = ''
    user_option = input('Enter a shoe name or sku to continue: ')
    shoe_list = request_options(user_option)
    
    #User input. Check for valid input.
    while 1:
        selected_shoe = input('Please select a shoe from the list to compare its price: ')
        try:
            selected_shoe = int(selected_shoe)
            if selected_shoe < 0 or selected_shoe > len(shoe_list) + 1:
                raise(ValueError)
            break
        except ValueError:
            paint('Invalid Value!', 'red')

    #Enter another name
    if selected_shoe == len(shoe_list):
        main()

    else:
        sku = shoe_list[selected_shoe]['sku']
        shoe_name = shoe_list[selected_shoe]['name']
        product_url_restocks = shoe_list[selected_shoe]['slug']
        threads = []

        paint(f'Selected shoe: {shoe_name} - {sku}', 'green')
        time.sleep(0.3)
        paint('Scraping sites...', 'yellow')
        start = time.time()

        t1 = threading.Thread(target = scrape_restocks, args = (product_url_restocks,))
        t2 = threading.Thread(target = scrape_stockx, args = (sku,))
        t3 = threading.Thread(target = scrape_klekt, args = (sku,))
        threads.append(t1)
        threads.append(t2)
        threads.append(t3)

        for t in threads:
            t.start()

        for t in threads:
            t.join()
        
        sizes_list_restocks = return_restocks()
        sizes_list_stockx = return_stockx()
        sizes_list_klekt = return_klekt()

        end = time.time()
        paint(f'Time elapsed: {end-start}s', 'blue')

        try:
            sizes_list_klekt.sort(key = lambda x :float(x[0]))
        except ValueError as e:
            print(f'{e}. Passing.')
            pass

        #Join all information to be used
        fill_empty_spaces([sizes_list_restocks, sizes_list_stockx, sizes_list_klekt])
        information_list = join_data_tuples(sizes_list_restocks, sizes_list_stockx, sizes_list_klekt)

        #Table management
        manage_table(information_list)

        if input("Do you want to check another shoe? [y/n]: ") == 'y':
            main()


def paint(text, color):
    print(colored(text, color))        


def request_options(user_option):

    response = search_shoes(user_option)
    json_response = response.json()
    for i, shoe in enumerate(json_response['data']):
        paint(f'{i} - {shoe["name"]} - {shoe["sku"]}', 'green')
    paint(f'{len(json_response["data"])} - Enter name again', 'yellow')

    return json_response['data']


def join_data_tuples(sizes_list_restocks, sizes_list_stockx, sizes_list_klekt):
    information_list = []

    for i in range(len(sizes_list_restocks)):
        new_list = [sizes_list_restocks[i][0], sizes_list_restocks[i][1], sizes_list_stockx[i][0], sizes_list_stockx[i][1]]
        new_list.append(sizes_list_klekt[i][0])
        new_list.append(sizes_list_klekt[i][1])
        information_list.append(new_list)

    return information_list


def manage_table(information_list):
    table = []
    paint('PRICE TABLE', 'blue')

    for line in information_list:
        t = [line[0], line[1], line[2], line[3], line[4], line[5]]
        table.append(t)
        
    paint(tabulate(table, headers = ['Size', 'Restocks', 'Size', 'Stockx', 'Size', 'Klekt']), 'green')


def fill_empty_spaces(list):
    max_list = max((x) for x in list)
    max_length = max(len(x) for x in list)
    for l in list:
        for t in range(len(l), max_length):
            l.append(('-', '-'))


if __name__ == '__main__':
    try:
        paint('Easily compare resell prices on the main platforms.', 'blue')
        main()
    except KeyboardInterrupt:
        print('Interruption detected.')