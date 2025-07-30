from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
import os
import time

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# Set up ChromeDriver path
chrome_driver_path = r"C:\WebDrivers\chromedriver.exe"
service = Service(executable_path=chrome_driver_path)

# Configure Chrome options for headless mode
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")

# Step 1: Scrape the homepage of JNMJournal for article titles and links
url = "https://www.jnmjournal.org/main.html"
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.get(url)
time.sleep(3)  # allow content to load

soup = BeautifulSoup(driver.page_source, 'html.parser')
with open("debug_jnm.html", "w", encoding="utf-8") as f:
    f.write(soup.prettify())
print("✅ Saved raw HTML to debug_jnm.html")

driver.quit()

# Find all article <a> tags with class 'j_text_size'
raw_articles = soup.find_all('a', class_='j_text_size')

# GERD-related keywords (lowercase for case-insensitive match)
keywords = ["gerd", "gastroesophageal reflux disease", "laryngopharyngeal reflux", "lpr"]

# Step 2: Filter for articles that match the keywords
article_links = []
print("\nAll articles found:")
for article in raw_articles:
    title = article.get_text(strip=True)
    href = article.get('href')

    print("-", title, "|", href)

    if not href or 'view.html' not in href:
        continue

    title_lower = title.lower()
    matched = False
    for keyword in keywords:
        if keyword in title_lower:
            matched = True
            print("✅ MATCH FOUND:", title)
            full_url = f"https://www.jnmjournal.org/{href}"
            article_links.append((title, full_url))
            break  # stop checking keywords
    if not matched:
        print("❌ No match:", title)


# Step 3: Read through the matching articles
article_contents = []
for title, link in article_links:
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(link)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        paragraphs = soup.find_all('p')
        content = "\n".join([para.get_text() for para in paragraphs])
        article_contents.append((title, link, content))
    except Exception as e:
        print(f"An error occurred while processing the article at {link}: {e}")
    finally:
        driver.quit()

# Step 4: Summarize each article
summaries = []
for title, link, content in article_contents:
    if not content.strip():
        print(f"Skipping empty article: {title}")
        continue

    truncated_content = content[:3000]

    messages = [
        {"role": "system", "content": "You are a helpful assistant that summarizes medical articles in 100 words or fewer."},
        {"role": "user", "content": f"Please summarize the following article content:\n{truncated_content}"}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        summary = response.choices[0].message.content
        summaries.append((title, link, summary))
    except Exception as e:
        print(f"An error occurred while summarizing the article: {e}")

# Step 5: Print summaries
for i, (title, link, summary) in enumerate(summaries, start=1):
    print(f"\n=== Summary of Article {i} ===")
    print(f"Title: {title}")
    print(f"Link: {link}")
    print(f"Summary: {summary}\n")
