# Facebook Screenshot Bot

This application automatically takes screenshots of a Facebook page every 12 hours using Selenium and Chrome in a headless browser.

## Features

- Automatically captures screenshots of a configured Facebook page
- Removes login popups and banners
- Resizes screenshots to 420x1250 pixels
- Runs in a Docker container for easy deployment
- Continuous operation with configurable interval (default: 12 hours)

## Quick Start with Docker

### Build the Docker image

```bash
docker build -t facebook-screenshot-bot .
```

### Run the container

```bash
docker run -d --name facebook-screenshot-bot facebook-screenshot-bot
```

### Run with volume to access screenshots from host

```bash
docker run -d --name facebook-screenshot-bot -v $(pwd):/app facebook-screenshot-bot
```

## Configuration Options

You can configure the bot through environment variables:

```bash
docker run -d \
  -e FACEBOOK_URL="https://www.facebook.com/your_page" \
  -e USE_LOGIN="true" \
  -e FB_EMAIL="your_email@example.com" \
  -e FB_PASSWORD="your_password" \
  -v $(pwd):/app \
  --name facebook-screenshot-bot \
  facebook-screenshot-bot
```

### Available Environment Variables

- `FACEBOOK_URL`: The Facebook page URL to screenshot (default: https://www.facebook.com/EMHansele)
- `USE_LOGIN`: Whether to attempt login before taking the screenshot (default: false)
- `USE_POPUP_LOGIN`: Whether to use the popup login dialog (default: false)
- `FB_EMAIL`: Facebook login email
- `FB_PASSWORD`: Facebook login password

### Command Line Options

You can also pass command line options when running the container:

```bash
docker run -d facebook-screenshot-bot python facebook_screenshot.py --single-run --disable-headless
```

Available options:
- `--use-login`: Use Facebook login before taking screenshot
- `--use-popup-login`: Use the popup login dialog instead of removing it
- `--email`: Facebook login email
- `--password`: Facebook login password
- `--disable-headless`: Disable headless mode (shows browser UI)
- `--single-run`: Run once and exit instead of continuous mode

## Accessing Screenshots

The screenshot is saved as `screenshot.png` in the app directory. When using a volume mapping, you can access it directly from your host machine.

## Running Without Docker

### Prerequisites

- Python 3.9+
- Chrome or Chromium browser
- Required Python packages: selenium, pillow, webdriver-manager

### Installation

```bash
pip install -r requirements.txt
```

### Running

```bash
python facebook_screenshot.py
```

## License

MIT 