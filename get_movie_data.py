import json
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib.parse
from rapidfuzz import fuzz
from rapidfuzz.fuzz import token_sort_ratio

BASE_URL = "https://www.the-numbers.com"

def parse_flexible_date(date_str):
    for fmt in ('%B %d, %Y', '%b %d, %Y'):
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    raise ValueError(f"Date format not recognized: {date_str}")

def find_best_match_link(soup, target_title, min_score=80):
    # Find the <h1> with "Movies" as its text
    movie_header = soup.find('h1', string='Movies')
    if not movie_header:
        print("❌ 'Movies' section header not found.")
        return None

    # The table we want is right after this header
    table = movie_header.find_next('table')
    if not table:
        print("❌ No table found after 'Movies' header.")
        return None

    best_score = 0
    best_link = None

    # Check each row in the table (skip header row)
    for row in table.find_all('td')[1:]:
        link_tag = row.find('a', href=True)
        if link_tag and '/movie/' in link_tag['href']:
            link_text = link_tag.get_text(strip=True)
            score = token_sort_ratio(link_text.lower(), target_title.lower())

            if score > best_score and score >= min_score:
                best_score = score
                best_link = f"https://www.the-numbers.com{link_tag['href'].split('#')[0]}"

    if best_link:
        print(f"✅ Best match: {best_link} ({best_score}%)")
        return best_link
    else:
        print("❌ No sufficiently close match found.")
        return None


# def find_best_match_link(soup):
    # Find the table with the expected headers
    movie_header = soup.find('h1', string='Movies')
    if not movie_header:
        print("❌ 'Movies' section header not found.")
        return None

    # The table we want is right after this header
    table = movie_header.find_next('table')
    if not table:
        print("❌ No table found after 'Movies' header.")
        return None

    # Find the first data row (not the header)
    data_rows = table.find_all('td')[1:]
    for row in data_rows:
        link_tag = row.find('a', href=True)
        if link_tag and '/movie/' in link_tag['href']:
            movie_url = f"https://www.the-numbers.com{link_tag['href'].split('#')[0]}"
            return movie_url

    print("❌ No movie link found in results table.")
    return None


def search_movie(title):
    query = urllib.parse.quote_plus(title)
    search_url = f"{BASE_URL}/custom-search?searchterm={query}"
    print(f"Searching for movie: {title} at {search_url}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    response = requests.get(search_url, headers=headers)
    if "summary" in response.url:
        return response.url 
    soup = BeautifulSoup(response.text, 'html.parser')
    # print("Parsing search results...")
    
    # Find the first movie search result link
    result_link = find_best_match_link(soup, title, 20)
    if not result_link:
        print(f"[!] No result found for: {title}")
        return None
    return result_link

def parse_duration(duration_str):
    import re
    hours = minutes = 0
    hr_match = re.search(r'(\d+)\s*hr', duration_str)
    min_match = re.search(r'(\d+)\s*min', duration_str)
    if hr_match:
        hours = int(hr_match.group(1))
    if min_match:
        minutes = int(min_match.group(1))
    return hours * 60 + minutes

def scrape_daily_gross(table):
    gross_data = []

    if table:
        for row in table.select("tr")[1:]:
            cols = row.find_all('td')
            if len(cols) >= 5:
                date = parse_flexible_date(cols[0].get_text(strip=True))
                gross = cols[2].get_text(strip=True).replace('$', '').replace(',', '')
                try:
                    gross = int(gross)
                except ValueError:
                    gross = None
                if int(date[0:4]) > 2024:
                    gross_data.append((date, gross))
    return gross_data

def get_worldwide_gross(table):
    if table:
        tr = table.select("tr")[-1]
        cols = tr.find_all('td')
        return cols[1].get_text(strip=True)
    return None


def has_financial_data(soup):
    finance_table = soup.find('table', id='movie_finances')
    if not finance_table:
        return False

    rows = finance_table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 2:
            label = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)
            if label == "Domestic Box Office":
                return value.lower() != "n/a"
    
    return False

def scrape_movie_data(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    time.sleep(0.5)  # Politeness delay
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    if not has_financial_data(soup):
        print(f"No financial data found for {url}")
        return None

    data = {
        'title': url.split('/')[-1].replace('-', ' ').title(),
        'release_date': None,
        'genre': None,
        'mpaa_rating': None,
        'runtime_minutes': None,
        'daily_total_gross': []
    }

    rows = soup.find_all("tr")
    for row in rows:
        header_cell = row.find("td")
        if not header_cell or not header_cell.find("b"):
            continue

        header = header_cell.find("b").get_text(strip=True)
        value_cell = row.find_all("td")[1] if len(row.find_all("td")) > 1 else None
        if not value_cell:
            continue

        value = value_cell.get_text(" ", strip=True)  # preserves inline spacing

        if "MPAA" in header:
            data["mpaa_rating"] = value.split(" ")[0]  # e.g., "R for ..." -> "R"
        elif header == "Running Time:":
            data["runtime_minutes"] = parse_duration(value)
        elif header == "Genre:":
            data["genre"] = value

    h2 = soup.find('h2', string='Daily Box Office Performance')
    if not h2:
        print("Daily Box Office section not found")
        return None
    # The table immediately follows the <h2>
    table = h2.find_next('table')
    first_data_row = table.find_all('tr')[1]
    date_cell = first_data_row.find('td')
    if date_cell and date_cell.a:
        data["release_date"] = parse_flexible_date(date_cell.a.get_text(strip=True))

    data["daily_total_gross"] = scrape_daily_gross(table)
    
    h2 = soup.find('h2', string='Box Office Summary Per Territory')
    if not h2:
        print("International Box Office not found")
        return None
    # The table immediately follows the <h2>
    table = h2.find_next('table')
    # Fallback to daily total gross if no worldwide gross found
    data["worldwide_gross"] = str( int(get_worldwide_gross(table).replace('$', '').replace(',', '')) + sum(value for _, value in data["daily_total_gross"]) )

    return data

def get_movie_data_from_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        movie_dict = json.load(f)

    all_results = []

    for owner, movies in movie_dict.items():
        for title in movies:
            print(f"Searching for {title} (Owner: {owner})")
            movie_url = search_movie(title)
            print(f"Found URL: {movie_url}")
            if movie_url:
                try:
                    movie_data = scrape_movie_data(movie_url)
                    movie_data['owner'] = owner
                    all_results.append(movie_data)
                except Exception as e:
                    print(f"Failed to scrape {title}: {e}")
            else:
                print(f"No match found for: {title}")
            print()

    return all_results

if __name__ == "__main__":
    data = get_movie_data_from_json("movie_draft_list.json")
    with open("movie_data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    for movie in data:
        print(f"{movie['owner']} - {movie['title']} ({movie['release_date']})")
        print(f"  Genre: {movie['genre']}")
        print(f"  Rating: {movie['mpaa_rating']}")
        print(f"  Runtime: {movie['runtime_minutes']} min")
        print(f"  International Box Office: {movie['worldwide_gross']}")
        if movie['daily_total_gross']:
            print(f"  Daily Gross: {movie['daily_total_gross'][:3]}")
        else:
            print("  Daily Gross: No data available")
