# Webhook Splitter/Split Hook

## Description

Webhook Splitter/Split hook allows you to split a webhook into multiple webhooks. This is useful when you have a single webhook that you want to send to multiple services. 

Some use cases include:
- Sending a single webhook which is a callback from an external provider to multiple services
- Sending a single webhook to multiple analytics services
- Tracking webhook/callbacks from different sources.

Don't want to host it yourself? Use it for free at https://splithook.com 

## Installation

Provide step by step series of examples and explanations about how to get a development environment running.

```bash
git clone git@github.com:shivam276/hook-splitter.git
cd webhook-splitter
pip install -r requirements.txt
```
## Usage

```bash
python app.py
```
You will have a dev server running on http://localhost:5000, you can use this URL to create a webhook in your external provider.