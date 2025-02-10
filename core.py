import requests
from bs4 import BeautifulSoup
import markdownify
import os
import hashlib
import boto3

BASE_URL = "https://fragment.dev/docs"
OUTPUT_FOLDER = "scraped_docs"

S3_DATA_BUCKET = "fragment-docs-data"
HASHES_TABLE = "fragment-docs-hashes"
    
def get_primary_section_html(url):
    """
    This method fetches the primary section content of a given URL.

    url (str): The URL of the page to scrape
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Locate the primary content
    main_content_div = soup.find("div", class_="basis-full")
    if not main_content_div:
        print(f"Warning: No main content found for {url}")
        return ""

    primary_section = main_content_div.find("section")
    if not primary_section:
        print(f"Warning: No section found in main content for {url}")
        return ""

    return primary_section

def process_primary_section_content(primary_section):
    """
    This method processes the primary section content and converts it to markdown.

    primary_section (bs4.element.Tag): The primary section content
    """
    # Convert <pre><code> blocks to markdown fenced code blocks
    for pre in primary_section.find_all("pre"):
        code_block = pre.find("code")
        if code_block:
            language = "bash"  # Default language
            if "class" in code_block.attrs:
                classes = code_block["class"]
                for c in classes:
                    if c.startswith("language-"):
                        language = c.split("language-")[1]
                        break

            code_text = code_block.get_text()
            markdown_code = f"\n```{language}\n{code_text}\n```\n"
            pre.replace_with(markdown_code)

    # Handle <code> blocks that are NOT inside <pre>
    for code in primary_section.find_all("code"):
        code_text = code.get_text()
        if "data-testid" in code.attrs and code["data-testid"] == "inline-code":
            markdown_inline = f"`{code_text}`"
            code.replace_with(markdown_inline)
        else:
            language = "bash"
            if "class" in code.attrs:
                classes = code["class"]
                for c in classes:
                    if c.startswith("language-"):
                        language = c.split("language-")[1]
                        break
            markdown_code = f"\n```{language}\n{code_text}\n```\n"
            code.replace_with(markdown_code)

    # Convert images to markdown
    for img in primary_section.find_all("img"):
        img_url = img["src"]
        img.replace_with(f"![Image]({img_url})")

    # Convert filtered HTML to Markdown
    markdown_content = markdownify.markdownify(str(primary_section), heading_style="ATX")

    return markdown_content

def save_markdown_data(url, markdown_data):
    """
    This method saves the markdown data to a file on AWS S3 with unique name based on the URL.

    :param str url: The URL of the page
    :param str markdown_data: The markdown content to save

    :return: None
    """
    print(f"Saving markdown data for {url}")
    # Generate a unique filename based on the URL
    filename = url.replace(f"{BASE_URL}/", "").replace("/", "-") + ".md"
    file_path = os.path.join(OUTPUT_FOLDER, filename)

    # Save the markdown data to a file
    try:
      os.makedirs(OUTPUT_FOLDER, exist_ok=True)
      with open(file_path, "w") as f:
          f.write(markdown_data)
      print(f"Markdown data saved to {file_path}")
    except FileNotFoundError:
        print(f"Error: The directory does not exist: {os.path.dirname(filename)}")
    except PermissionError:
        print(f"Error: Permission denied for writing to the file: {filename}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    # Upload the file to S3
    s3 = boto3.client('s3')
    try:
        # Attempt to delete the file if it already exists
        # If file does not exist, we will ignore the exception
        s3.delete_object(Bucket=S3_DATA_BUCKET, Key=filename)
            
        s3.Object(S3_DATA_BUCKET, filename).put(Body=markdown_data)
        print(f"File uploaded to S3: {filename}")

        # Remove the local file after uploading to S3
        os.remove(file_path)
        print(f"Local file removed: {file_path}")
    except Exception as e:
        print(f"An error occurred while uploading the file to S3: {e}")

def generate_and_save_hash(url, content):
    """
    This method generates a hash of the content for a given URL and updates it in DynamoDB. If the given URL already exists in the table, it will update the existing record.

    :param str url: The URL of the page
    :param str content: The content of the page

    :return: None
    """
    # Generate a hash of the content
    hash_content = hashlib.sha256(content.encode('utf-8')).hexdigest()

    # Save the hash in DynamoDB
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(HASHES_TABLE)
        table.put_item(Item={
            'id': url,
            'url': url,
            'hash': hash_content
        })
        print(f"Hash saved successfully for {url}")
    except Exception as e:
        print(f"An error occurred while saving the hash: {e}")

def scrape_url_and_generate_hash(url):
    """
    This method scrapes the content of a given URL and converts it to markdown.

    :param str url: The URL of the page to scrape
    """
    print(f"Scraping URL: {url}")
    # Get the primary section content
    primary_section = get_primary_section_html(url)
    print("Primary section content extracted")
    # Process the primary section content
    markdown_content = process_primary_section_content(primary_section)
    print("Primary section content processed")
    # Save the markdown content to a file
    save_markdown_data(url, markdown_content)
    # Generate and store hash of primary content
    generate_and_save_hash(url, primary_section)
    print(f"Scraping completed for URL: {url}")

# def get_all_doc_links():
#     response = requests.get(BASE_URL)
#     soup = BeautifulSoup(response.text, "html.parser")
#     links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith('/docs')]
#     return list(set(["https://fragment.dev" + link for link in links]))

def lambda_handler(event, context):
    print("LEDAA Web Scrapper Lambda invoked")
    scrape_url_and_generate_hash("https://fragment.dev/docs/install-the-sdk")
    return {
        'statusCode': 200,
        'body': 'Scraping completed'
    }
