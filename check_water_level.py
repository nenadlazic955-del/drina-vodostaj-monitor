#!/usr/bin/env python3
"""
Proverava vodostaj Drine na stanici Bajina Basta (RHMZ Srbije) i salje
ntfy.sh notifikaciju na telefon kada se vrednost promeni u odnosu na
poslednju sacuvanu vrednost.

Izvor podataka (zvanicni, RHMZ):
https://www.hidmet.gov.rs/latin/hidrologija/izvestajne/bezprognoza.php?hm_id=45865
"""

import json
import os
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

STATION_URL = (
    "https://www.hidmet.gov.rs/latin/hidrologija/izvestajne/"
    "bezprognoza.php?hm_id=45865"
)
STATE_FILE = Path(__file__).parent / "state" / "last_state.json"

NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")


def fetch_reading():
    """Preuzima stranicu i vraca dict sa datumom, vodostajem, promenom, itd."""
    resp = requests.get(
        STATION_URL,
        headers={"User-Agent": "Mozilla/5.0 (drina-vodostaj-monitor bot)"},
        timeout=30,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")

    target_table = None
    for table in soup.find_all("table"):
        if "Vodostaj" in table.get_text():
            target_table = table
            break
    if target_table is None:
        raise RuntimeError("Nisam pronasao tabelu sa podacima o vodostaju.")

    rows = target_table.find_all("tr")

    datum = None
    header_idx = None
    for i, tr in enumerate(rows):
        text = tr.get_text(" ", strip=True)
        if "Datum:" in text:
            datum = text.split("Datum:")[-1].strip()
        tds = tr.find_all("td")
        if tds and tds[0].get_text(strip=True).startswith("Vodostaj"):
            header_idx = i

    if header_idx is None:
        raise RuntimeError("Nisam pronasao header red sa kolonom 'Vodostaj'.")

    value_tds = None
    for tr in rows[header_idx + 1 :]:
        tds = tr.find_all("td")
        if len(tds) == 4:
            value_tds = tds
            break

    if value_tds is None:
        raise RuntimeError("Nisam pronasao red sa vrednostima vodostaja.")

    vodostaj, promena, proticaj, temperatura = (
        td.get_text(strip=True) for td in value_tds
    )

    return {
        "datum": datum,
        "vodostaj_cm": vodostaj,
        "promena_cm": promena,
        "proticaj_m3s": proticaj,
        "temperatura_c": temperatura,
    }


def load_last_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return None


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def send_notification(title, message):
    if not NTFY_TOPIC:
        raise RuntimeError("NTFY_TOPIC nije podesen (environment variable).")
    url = f"{NTFY_SERVER.rstrip('/')}/{NTFY_TOPIC}"
    resp = requests.post(
        url,
        data=message.encode("utf-8"),
        headers={
            "Title": title.encode("utf-8"),
            "Tags": "droplet",
        },
        timeout=15,
    )
    resp.raise_for_status()


def main():
    reading = fetch_reading()
    print(f"Ocitano: {reading}")

    last = load_last_state()

    if last is None:
        print("Nema prethodnog stanja - cuvam bazno stanje bez notifikacije.")
        save_state(reading)
        return

    if reading["vodostaj_cm"] != last.get("vodostaj_cm") or reading["datum"] != last.get(
        "datum"
    ):
        message = (
            f"Vodostaj: {reading['vodostaj_cm']} cm "
            f"(promena: {reading['promena_cm']} cm)\n"
            f"Datum: {reading['datum']}\n"
            f"Prethodno: {last.get('vodostaj_cm')} cm"
        )
        print("Promena detektovana, saljem notifikaciju:\n" + message)
        send_notification("Vodostaj Drine - Bajina Basta", message)
        save_state(reading)
    else:
        print("Bez promene, notifikacija se ne salje.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"GRESKA: {exc}", file=sys.stderr)
        sys.exit(1)
