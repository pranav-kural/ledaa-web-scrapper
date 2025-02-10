#!/bin/bash

# Create a directory for the python layer
mkdir -p layers/python

# cd into python directory
cd layers/python

# Install the required packages in the python directory for arm64
pip3 install --platform=macosx_11_0_arm64 --only-binary=:all: -r ../../requirements.txt -t .

# cd back to the parent directory
cd ..

# remove older zip file
rm -f ../terraform/packages/ledaa_web_scrapper_lambda_layer.zip

# Zip the contents of the python directory
zip -r ../terraform/packages/ledaa_web_scrapper_lambda_layer.zip .

# Remove the layers/python directory
cd ..
rm -rf layers
