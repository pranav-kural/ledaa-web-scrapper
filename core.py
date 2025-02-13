import requests
from bs4 import BeautifulSoup
import markdownify
import hashlib
import boto3

# Constants
BASE_URL = "https://fragment.dev/docs"
S3_DATA_BUCKET = "fragment-docs-data"
S3_OUTPUT_FOLDER = "scraped_docs"
HASHES_TABLE = "fragment-docs-hashes"

# Extracts HTML from the section that contains the primary documentation content specific to the topic of URL
def get_primary_section_html(url):
    """
    This method fetches and extracts HTML from the section that contains the primary documentation content specific to the topic of URL.

    :param str url: The URL of the page to scrape

    :return BeautifulSoup: The primary section content as a BeautifulSoup object
    """
    # Fetch the page content
    response = requests.get(url)
    if response.status_code != 200:
        #  throw an exception if the request was unsuccessful
        raise Exception(f"Failed to fetch URL: {url}")
    # Parse the HTML content
    soup = BeautifulSoup(response.text, "html.parser")

    # Locate the primary content
    main_content_div = soup.find("div", class_="basis-full")
    if not main_content_div:
        raise Exception(f"No main content found for {url}")
    # Extract section
    primary_section = main_content_div.find("section")
    if not primary_section:
        raise Exception(f"No section found in main content for {url}")

    return primary_section

# Processes the primary section content HTML and converts it to markdown
def process_primary_section_content(primary_section):
    """
    This method processes the primary section content HTML and converts it to markdown with proper formatting.

    Inline and block code snippets are converted to markdown code blocks.
    Images are converted to markdown image links.

    :param BeautifulSoup primary_section: The primary section content as a BeautifulSoup object

    :return str: The markdown content
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

# Saves the markdown data to a file on AWS S3 with unique name based on the URL
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

    # Upload the data to S3
    s3 = boto3.client('s3')
    try:
        # Save data to file on S3
        # If file already exists, its simply overwritten
        s3.put_object(Bucket=S3_DATA_BUCKET, Key=f"{S3_OUTPUT_FOLDER}/{filename}", Body=markdown_data)
        print(f"File uploaded to S3: {filename}")
    except Exception as e:
        raise Exception(f"An error occurred while saving markdown data to S3: {e}")

# Generates a hash of the content for a given URL and updates it in DynamoDB
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
        # Write/update the hash in the table
        table.put_item(Item={
            'id': url,
            'url': url,
            'hash': hash_content
        })
        print(f"Hash saved successfully for {url}")
    except Exception as e:
        print(f"An error occurred while saving the hash: {e}")

# Main method to scrape the URL and generate hash
def scrape_url_and_generate_hash(url):
    """
    This method scrapes the content of a given URL and converts it to markdown.

    :param str url: The URL of the page to scrape
    """
    print(f"Scraping URL: {url}")
    # Get the primary section content
    try:
        primary_section = get_primary_section_html(url)
        print("Primary section content extracted")
        try:
            # Process the primary section content
            markdown_content = process_primary_section_content(primary_section)
            print("Primary section content processed")
            try: 
                # Save the markdown content to a file
                save_markdown_data(url, markdown_content)
                try:
                    # Generate and store hash of primary content
                    generate_and_save_hash(url, markdown_content)
                except Exception as e:
                    print(f"An error occurred while generating and saving hash: {e}")
                    return {
                        'statusCode': 500,
                        'body': 'An error occurred while generating and saving hash'
                    }
            except Exception as e:
                print(f"An error occurred while saving markdown data: {e}")
                return {
                    'statusCode': 500,
                    'body': 'An error occurred while saving markdown data'
                }
        except Exception as e:
            print(f"An error occurred while processing primary section content: {e}")
            return {
                'statusCode': 500,
                'body': 'An error occurred while processing primary section content'
            }
    except Exception as e:
        print(f"An error occurred while fetching primary section content: {e}")
        return {
            'statusCode': 500,
            'body': 'An error occurred while fetching primary section content'
        }
    print(f"Scraping completed for URL: {url}")
    return {
        'statusCode': 200,
        'body': 'Scraping completed'
    }
    
    

# Lambda handler method (will be invoked by AWS Lambda)
def lambda_handler(event, context):
    print("LEDAA Web Scrapper Lambda invoked")
    # Validate URL 
    if "url" not in event:
        return {
            'statusCode': 400,
            'body': 'URL is required'
        }
    # Scrape the URL and generate hash
    return scrape_url_and_generate_hash(event["url"])
