from bs4 import BeautifulSoup
import requests
import django
import os
import sys
import telebot
import time
from get_number import getnumber


url_source = 'https://avtoelon.uz'
# Fetch the HTML content of a web page
response = requests.get(url_source)
html_content = response.text

soup = BeautifulSoup(html_content, 'html.parser')

div_elements = soup.find_all('div', class_='hot-item')

k = 0
for div_element in div_elements[1:]:
    try:
        k += 1
        link = div_element.find('a')['href']
        # print("URL:", link)
        single_car_url = url_source+link
        time.sleep(2)
        response = requests.get(single_car_url)
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')

        number = getnumber(single_car_url)
        print(number)

        div_element = soup.find('div', class_='item product')

        span_brand = div_element.find('span', itemprop='brand')
        brand = span_brand.get_text(strip=True)

        span_name = div_element.find('span', itemprop='name')
        name = span_name.get_text(strip=True).replace(',', '')

        span_price = div_element.find('span', class_='a-price__text')
        price = span_price.get_text(strip=True).replace(
            'y.e.', '').replace('\xa0', '').replace('~', '')

        dt_element = div_element.find('dt', class_='value-title', string='Год')
        dd_element = dt_element.find_next_sibling('dd')
        year = dd_element.get_text(strip=True)

        # print(brand, name, year, price+'$')

        pairs = div_element.find_all(['dt', 'dd'])
        description = div_element.find(
            'div', class_='description-text').get_text(separator=' ').strip()
        formatted_text = ''
        for i in range(0, len(pairs), 2):
            if i != 2:
                dt_text = pairs[i].get_text(strip=True)
                dd_text = pairs[i + 1].get_text(strip=True)
                formatted_text += f"{dt_text} {dd_text},\n"

        photo_tags = div_element.find_all('a', class_='small-thumb')
        main_photo = div_element.find('div', class_='main-photo')

        url = "https://avtouzbot.pythonanywhere.com/api/cars/"

        images = []

        try:
            images.append({'image_link': main_photo.a.get(
                'href'), 'telegraph': main_photo.a.get('href')})
            for i, photo_tag in enumerate(photo_tags[1:]):
                if i >= 5:  # Maximum number of photos reached
                    break
                href = photo_tag.get('href')

                images.append({'image_link': href, 'telegraph': href})

        except Exception as e:
            print(e)

        # Define the car data to be posted
        car_data = {
            "owner_telegram_id": 872978271,  # The owner's Telegram ID
            "name": name,
            "model": brand,
            "year": year,
            "price": float(price),
            "description": formatted_text+description,
            "contact_number": number,
            "images": images,
            "complate":True
        }

        response = requests.post(url, json=car_data)

        if response.status_code == 201:
            print("Car data posted successfully!")
        else:
            print("Failed to post car data. Error:", response.text)

    except Exception as e:
        print(e)

print(k)
