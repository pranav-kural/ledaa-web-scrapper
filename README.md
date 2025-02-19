# LEDAA Web Scrapper

This is a web scrapper meant to scrap HTML data from the [FRAGMENT (documentation)](https://fragment.dev/docs) webpages, and prepare and store correctly formatted markdown data to AWS S3.

The extracted markdown data then can be used as source data for knowledge base in a Retrieval Augmented Generation (RAG)-based conversational AI system or application. Large Language Models (LLMs) can easily comprehend markdown formatted data, and use of LLMs for specialized semantic chunking also becomes a possibility with markdown data, further enhancing context retrieval in RAG.

To learn more check: [Building AI Assistant for FRAGMENT documentation](https://www.pkural.ca/blog/posts/fragment/)

![ledaa-web-scrapper](https://github.com/user-attachments/assets/835a681a-5737-408a-b945-16e3e40c5ab3)

## Handling Data Updates

To address the challenge of dealing with obsolete or outdated information, this program also creates and stores **unique hashes** of the primary data in **AWS DynamoDB** for each webpage URL (i.e., webpage **URL** acts as `key` and the SHA-256 **hash** generated for the HTML of the primary section on that URL is stored as the `value`). A separate AWS Lambda job runs periodically to scrap HTML data for each URL and compare the hash with the stored hash in DynamoDB. If the hash is different, the Lambda job initiates the process to scrap data again for that URL and the data loading process (embedding generation + vector store update) is triggered. Each chunk in the vector store is associated through **metadata** with the URL from which it was extracted. Therefore, when data needs to be updated for a certain URL, only specific chunks are replaced.

## Data Extraction

The data extraction process involves the following steps:

1. **Web Scraping**: The program receives `URL` of the webpage as an argument and uses `BeautifulSoup` to scrap HTML data from the given URL.
2. **Primary Section HTML Extraction**: First, we extract the HTML of only the section of the documentation page we are concerned with, i.e., we exclude the header, footer, and other irrelevant sections.
3. **Content Formatting**: Certain elements are formatted optimally for markdown conversion and format standards. Our focus here is mainly on `code` elements. Both inline and block code elements are formatted correctly. Images are also replaced with links to the images, and hyperlinks are formatted correctly.
4. **Markdown Conversion**: The formatted HTML content is converted to markdown using `markdownify` library.
5. **Data Storage**: The markdown data is stored in AWS S3. If file for the given URL already exists, its overwritten.

Code for the above steps can be found in the `core.py` file.

## AWS Lambda Deployment

We deploy the web scrapper function to AWS Lambda using [Terraform](https://www.terraform.io/). The Terraform configuration files can be found in the `terraform` directory. The configuration file creates:

-   Appropriate AWS role and policy for the Lambda function.
-   AWS Lambda Layer for the Lambda function using pre-built compressed lambda layer zip file (present in `terraform/packages`, created using `create_lambda_layer.sh`).
-   Data archive file for the core code (`core.py`).
-   AWS Lambda function using the data archive file, the Lambda Layer, and the appropriate role.
-   Lambda function is configured appropriately to access **AWS S3** and **AWS DynamoDB**.

There are certain scripts in `terraform` directory, like `apply.sh` and `plan.sh`, which can be used to apply and plan the Terraform configuration respectively. These scripts extract necessary environment variables from the `.env` file and pass them to Terraform.

Ideally, this Lambda function will be triggered by another Lambda function which is responsible for monitoring documentation updates.

Sample output from a single invocation:

```bash
LEDAA Web Scrapper Lambda invoked
Scraping URL: https://fragment.dev/docs/install-the-sdk
Primary section content extracted
Primary section content processed
Saving markdown data for https://fragment.dev/docs/install-the-sdk
File uploaded to S3: install-the-sdk.md
Hash saved successfully for https://fragment.dev/docs/install-the-sdk
Scraping completed for URL: https://fragment.dev/docs/install-the-sdk
```

## LICENSE

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
