terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.76"
    }
  }

  required_version = ">= 1.5.6"
}

provider "aws" {
  region     = "ca-central-1"
  access_key = var.AWS_ACCESS_KEY
  secret_key = var.AWS_SECRET_KEY
}

resource "aws_iam_role" "lambda_role" {
  name = "lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "s3:GetObject",
          "sns:Publish",
          "dynamodb:*",
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_layer_version" "lambda_layer" {
  filename   = "packages/ledaa_web_scrapper_lambda_layer.zip"
  layer_name = "LEDAA-Web-Scrapper-Layer"

  compatible_runtimes = ["python3.13"]
}

data "archive_file" "lambda_code" {
  type        = "zip"
  source_file = "../core.py"
  output_path = "packages/ledaa_web_scrapper_package.zip"
}

resource "aws_lambda_function" "ledaa_web_scrapper" {
  function_name = "ledaa_web_scrapper_lambda"
  role          = aws_iam_role.lambda_role.arn
  handler       = "core.lambda_handler"
  runtime       = "python3.13"
  architectures = ["arm64"]

  filename         = "packages/ledaa_web_scrapper_package.zip"
  source_code_hash = data.archive_file.lambda_code.output_base64sha256

  layers = [aws_lambda_layer_version.lambda_layer.arn]

  timeout = 10
}