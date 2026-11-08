"""Prepare a compact, reproducible Steam game dataset for DSPC6000 Project 1.

Source: https://www.kaggle.com/datasets/fronkongames/steam-games-dataset

Usage (from project_1/):
    python prepare_data.py
Or provide the raw CSV location:
    python prepare_data.py "C:\\path\\to\\games.csv"

The script reads the 383 MB original using only Python's standard library.
It does not modify the original CSV.
"""

import csv
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

# Fixed observation cutoff: a reproducible snapshot of games released by this date.
CUTOFF_DATE = date(2026, 11, 7)

# Game genres (excluding Steam's Indie, Free To Play, and Early Access attributes).
GAME_GENRES = {
    "Action",
    "Adventure",
    "Casual",
    "RPG",
    "Simulation",
    "Strategy",
    "Sports",
    "Racing",
    "Massively Multiplayer",
}

COLUMNS = [
    "appid",
    "name",
    "release_date",
    "release_year",
    "genres",
    "all_genres",
    "tags",
    "price",
    "positive",
    "negative",
    "review_count",
    "approval_rate",
    "peak_ccu",
    "estimated_owners",
]


def main():
    base_dir = Path(__file__).resolve().parent
    source = (
        Path(sys.argv[1]).expanduser()
        if len(sys.argv) > 1
        else Path.home() / "Downloads" / "games.csv"
    )
    if not source.is_file():
        raise FileNotFoundError(
            f"Cannot find {source}\n"
            'Put games.csv in Downloads or run: python prepare_data.py "FULL_PATH_TO_GAMES_CSV"'
        )

    output = base_dir / "data" / "steam_games_clean.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    seen_appids = set()

    with (
        source.open("r", encoding="utf-8-sig", newline="") as infile,
        output.open("w", encoding="utf-8", newline="") as outfile,
    ):
        reader = csv.reader(infile)
        header = next(reader)

        # The downloaded Kaggle file has 39 header names and 40 values per row:
        # 'DiscountDLC count' must be split into 'Discount' + 'DLC count'.
        if "DiscountDLC count" in header:
            pos = header.index("DiscountDLC count")
            header[pos : pos + 1] = ["Discount", "DLC count"]
        if len(header) != 40:
            raise ValueError(f"Unexpected header: {len(header)} columns (expected 40)")

        writer = csv.DictWriter(outfile, fieldnames=COLUMNS)
        writer.writeheader()

        for row in reader:
            counts["raw_rows"] += 1
            if len(row) != len(header):
                counts["bad_column_count"] += 1
                continue
            game = dict(zip(header, row))

            appid = game["AppID"].strip()
            if not appid or appid in seen_appids:
                counts["duplicate_or_missing_appid"] += 1
                continue
            seen_appids.add(appid)

            name = game["Name"].strip()
            if re.search(r"\bplaytest\b", name, flags=re.IGNORECASE) or re.search(
                r"\bdemo$", name, flags=re.IGNORECASE
            ):
                counts["playtest_or_demo"] += 1
                continue

            try:
                released = datetime.strptime(game["Release date"], "%b %d, %Y").date()
            except ValueError:
                counts["invalid_release_date"] += 1
                continue
            if released > CUTOFF_DATE:
                counts["future_release"] += 1
                continue

            all_genres = [g.strip() for g in game["Genres"].split(",") if g.strip()]
            genres = [g for g in all_genres if g in GAME_GENRES]
            if not genres:
                counts["no_game_genre"] += 1
                continue

            try:
                positive = int(game["Positive"])
                negative = int(game["Negative"])
                peak_ccu = int(game["Peak CCU"])
                price = float(game["Price"])
            except ValueError:
                counts["invalid_numeric"] += 1
                continue
            if min(positive, negative, peak_ccu) < 0 or price < 0:
                counts["negative_numeric"] += 1
                continue

            review_count = positive + negative
            writer.writerow(
                {
                    "appid": appid,
                    "name": name,
                    "release_date": released.isoformat(),
                    "release_year": released.year,
                    "genres": ",".join(genres),
                    "all_genres": ",".join(all_genres),
                    "tags": game["Tags"],
                    "price": f"{price:.2f}",
                    "positive": positive,
                    "negative": negative,
                    "review_count": review_count,
                    "approval_rate": f"{positive / review_count:.6f}"
                    if review_count
                    else "",
                    "peak_ccu": peak_ccu,
                    "estimated_owners": game["Estimated owners"],
                }
            )
            counts["kept"] += 1

    print(f"Input:  {source}")
    print(f"Output: {output}")
    print("Cleaning summary:")
    for key, value in counts.items():
        print(f"  {key}: {value:,}")
    print(f"  included share: {counts['kept'] / counts['raw_rows']:.1%}")


if __name__ == "__main__":
    main()
