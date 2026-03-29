import argparse
import time
from pathlib import Path

import pyautogui
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# --- Configuration --- #
# Update these to match your screen setup (pixels, no scaling).
PRIMARY_CLICK_1 = (1690, 301)
PRIMARY_CLICK_2 = (1610, 301)
BUY_CLICK = (1475, 1262)

# Region to crop for price OCR: (left, top, width, height)
PRICE_REGION = (1323, 1063, 82, 100)

# Delay (seconds) between the two primary clicks
PRIMARY_INTERVAL = 0.1

# Delay after finishing the buy sequence (seconds)
BUY_COOLDOWN = 1.0

# Delay before checking price after the two refresh clicks
POST_REFRESH_DELAY = 0.5


def grab_price(region: tuple[int, int, int, int]) -> Image.Image:
    return pyautogui.screenshot(region=region)


def parse_price(img: Image.Image) -> int | None:
    # Scale up for cleaner OCR
    scale = 3
    img = img.resize(
        (img.width * scale, img.height * scale),
        resample=Image.Resampling.LANCZOS,
    )

    gray = img.convert("L")
    gray = gray.point(lambda x: min(255, int(x * 1.2)))
    bw = gray.point(lambda x: 255 if x > 150 else 0)

    config = "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789"
    text = pytesseract.image_to_string(bw, config=config)
    digits = "".join(ch for ch in text if ch.isdigit())

    print(f"OCR raw: {text!r}, digits: {digits!r}")

    return int(digits) if digits else None


def click(point: tuple[int, int], clicks: int = 1, interval: float = 0.1):
    pyautogui.click(x=point[0], y=point[1], clicks=clicks, interval=interval)


def main(threshold: int, loop_delay: float, safe_mode: bool, use_second_click: bool):
    print("Starting market bot. Press Ctrl+C to stop.")
    time.sleep(2.5)

    out_dir = Path("debugregion")
    out_dir.mkdir(exist_ok=True)

    try:
        while True:
            click(PRIMARY_CLICK_1)

            if use_second_click:
                time.sleep(PRIMARY_INTERVAL)
                click(PRIMARY_CLICK_2)

            time.sleep(POST_REFRESH_DELAY)

            price_img = grab_price(PRICE_REGION)

            timestamp = int(time.time() * 1000)
            price_img.save(out_dir / f"region_{timestamp}.png")

            price = parse_price(price_img)

            if price is None:
                print("OCR failed, skipping buy.")
            else:
                print(f"Detected price: {price}")
                if price <= threshold:
                    print("Price ? threshold — buying (disabled in test mode).")
                    # click(BUY_CLICK, clicks=2, interval=0.15)
                    time.sleep(BUY_COOLDOWN)
                else:
                    print("Price above threshold — refreshing again.")

            if safe_mode:
                time.sleep(loop_delay)
            else:
                time.sleep(max(loop_delay, 0.05))

    except KeyboardInterrupt:
        print("\nStopped by user.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refresh market and auto-buy below target price.")
    parser.add_argument(
        "--threshold",
        type=int,
        required=False,
        help="Maximum price to trigger purchase.",
    )
    parser.add_argument(
        "--loop-delay",
        type=float,
        default=1.2,
        help="Delay between refresh cycles (seconds).",
    )
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="Adds extra delay to avoid overwhelming the UI.",
    )
    args = parser.parse_args()

    threshold = args.threshold
    if threshold is None:
        while True:
            try:
                threshold = int(input("Price Treshold: ").strip())
                break
            except ValueError:
                print("Enter a valid number.")

    use_second_click = input("Do you want to double click (y/n) ").strip().lower() == "y"

    main(
        threshold=threshold,
        loop_delay=args.loop_delay,
        safe_mode=args.safe_mode,
        use_second_click=use_second_click,
    )
