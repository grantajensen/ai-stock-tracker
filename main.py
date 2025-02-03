import os
import requests
import yfinance as yf
from PIL import Image, ImageDraw, ImageFont
import datetime
import hashlib
import time
from dotenv import load_dotenv

load_dotenv()

cloud_name = os.getenv("CLOUD_NAME")
api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")

TICKERS = ["AAPL", "NVDA", "MSFT", "AMD", "TSM", "AMZN", "GOOG", "META", "TSLA", "QQQ"]

# Fetch stock data from Yahoo Finance
def fetch_stock_data(tickers):
    stock_data = {}
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="2d")  # Get last two days to calculate change
        if len(hist) >= 2:
            last_close = hist.iloc[-2]["Close"]
            current_close = hist.iloc[-1]["Close"]
            change = ((current_close - last_close) / last_close) * 100
            stock_data[ticker] = {"price": round(current_close, 2), "change": round(change, 2)}
    return stock_data


# Generate image
def generate_stock_image(stock_data):
    width, height = 1080, 650
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    positions = [
        (0, height*0.1, width*0.3, height*0.5),
        (width*0.3, height*0.1, width*0.6, height*0.5),
        (0, height*0.5, width*0.3, height*0.9),
        (width*0.3, height*0.5, width*0.6, height*0.9),
        (width*0.6, height*0.1, width*0.8, height*0.41),
        (width*0.8, height*0.1, width, height*0.41),
        (width*0.6, height*0.41, width*0.8, height*0.72),
        (width*0.8, height*0.41, width, height*0.72),
        (width*0.6, height*0.72, width*0.8, height*0.9), 
        (width*0.8, height*0.72, width, height*0.9)
    ]

    positions = [tuple(map(int, pos)) for pos in positions]

    for i, (ticker, data) in enumerate(stock_data.items()):
        x1, y1, x2, y2 = positions[i]
        if data["change"] >= 0.5:
            color = (101, 249, 93)
        elif data["change"] <= -0.5:
            color = (250, 103, 103)
        elif data["change"] > 0 and data["change"] < 0.5:
            color = (157, 247, 149)
        elif data["change"] < 0 and data["change"] > -0.5:
            color = (252, 130, 130)
        else:
            color = (220, 220, 220)

        draw.rectangle([x1, y1, x2, y2], fill=color, outline=(0,0,0,0), width=3)
        
        logo_path = f"logos/{ticker}.png"
        if os.path.exists(logo_path):
            logo_size = round((y2 - y1) * 0.35)
            logo = Image.open(logo_path).convert("RGBA")
            logo = logo.resize((logo_size, logo_size))  # Resize for consistency
            logo_x = x1 + (x2 - x1 - logo.width) // 2
            logo_y = y1 + ((y2 - y1) // 13)
            img.paste(logo, (logo_x, logo_y), logo)

        big_font_size = round((y2 - y1) * 0.17)
        little_font_size = round((y2 - y1) * 0.11)
        big_font = ImageFont.truetype("fonts/arial-bold.ttf", big_font_size)
        little_font = ImageFont.truetype("fonts/arial-bold.ttf", little_font_size)

        ticker_text = f"{ticker}"
        price_text = f"${data['price']:.2f}"
        if data['change'] >= 0:
            change_text = f"+{data['change']:.2f}%"
        else:
            change_text = f"{data['change']:.2f}%"
        ticker_size = round(draw.textlength(ticker_text,font=big_font))
        price_size = round(draw.textlength(price_text,font=little_font))
        change_size = round(draw.textlength(change_text,font=little_font))
 
        draw.text((x1 + ((x2 - x1 - ticker_size) // 2), logo_y + logo_size + (big_font_size*0.1)), ticker_text, fill="black", font=big_font)
        draw.text((x1 + ((x2 - x1 - price_size) // 2), logo_y + logo_size + (big_font_size*1.3)), price_text, fill="black", font=little_font)
        draw.text((x1 + ((x2 - x1 - change_size) // 2), logo_y + logo_size + (big_font_size*1.4) + little_font_size), change_text, fill="black", font=little_font)

    
    filename = f"examples/stock_update_{datetime.date.today()}.png"
    img.save(filename)
    return filename

# Generate authentication signature for Cloudinary
def generate_signature(data, api_secret):
    sorted_params = "&".join(f"{key}={data[key]}" for key in sorted(data))
    final_params = sorted_params + api_secret
    hash_object = hashlib.sha1(final_params.encode())
    return hash_object.hexdigest()

# Upload image to Cloudinary
def upload_image(image_path):
    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"

    data = {
        "overwrite": "true",
        "public_id": "daily_stock_update",
        "timestamp": str(int(time.time()))
    }
    data["signature"] = generate_signature(data, api_secret)
    data["api_key"] = api_key

    files = {"file": open(image_path, "rb")}
    response = requests.post(url, data=data, files=files)

    if response.status_code == 200:
        image_url = response.json()["secure_url"]
        print(f"Image uploaded successfully: {image_url}")
        return image_url
    else:
        print("Upload failed:", response.json())
        return None


# Main script execution
if __name__ == "__main__":
    stock_data = fetch_stock_data(TICKERS)
    image_path = generate_stock_image(stock_data)
    image_link = upload_image(image_path)
