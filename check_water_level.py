#!/usr/bin/env python3
"""
Proverava vodostaj Drine na stanici Bajina Basta (RHMZ Srbije, automatska
stanica - ocitavanje na svakih 30 min) i salje ntfy.sh notifikaciju na
telefon kada se vrednost promeni u odnosu na poslednju sacuvanu vrednost.

Izvor podataka (zvanicni, RHMZ - "casovne vrednosti vodostaja, poslednjih
7 dana"):
https://www.hidmet.gov.rs/latin/osmotreni/nrt_tabela_grafik.php?hm_id=45865&period=7

Napomena RHMZ-a o ovim podacima: "Podaci su privremeni, nekontrolisani,
nisu provereni i mogu sadrzati pogresne vrednosti." Nagle promene mogu
biti realne (npr. ispustanje vode iz HE Bajina Basta / Perucac), a ne
nuzno greska senzora.
"""

import json
import os
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

STATION_URL = (
    "https://www.hidmet.gov.rs/latin/osmotreni/"
    "nrt_tabela_grafik.php?hm_id=45865&period=7"
)
STATE_FILE = Path(__file__).parent / "state" / "last_state.json"

NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")


def fetch_reading():
    """Preuzima stranicu i vraca najnovije (prvo) ocitavanje iz tabele."""
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

    # Ne oslanjamo se na <tbody> - sirovi HTML ga cesto nema eksplicitno
    # (samo ga browser DOM automatski dodaje), pa direktno trazimo prvi
    # red koji ima tacno 2 <td> celije (header ima <th>, footer/napomena
    # ima 1 <td colspan="2">, pa se prirodno preskacu).
    data_row = None
    for tr in target_table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) == 2:
            data_row = tds
            break

    if data_row is None:
        raise RuntimeError("Nisam pronasao red sa ocitavanjem (2 kolone).")

    datum_vreme = data_row[0].get_text(strip=True)
    vodostaj = data_row[1].get_text(strip=True)

    return {"datum_vreme": datum_vreme, "vodostaj_cm": vodostaj}


def load_last_state():
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data or None
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

    if reading["vodostaj_cm"] != last.get("vodostaj_cm"):
        message = (
            f"Vodostaj: {reading['vodostaj_cm']} cm\n"
            f"Vreme merenja: {reading['datum_vreme']}\n"
            f"Prethodno: {last.get('vodostaj_cm')} cm"
        )
        print("Promena detektovana, saljem notifikaciju:\n" + message)
        send_notification("Vodostaj Drine - Bajina Basta", message)
        save_state(reading)
    else:
        print("Bez promene vodostaja, notifikacija se ne salje.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"GRESKA: {exc}", file=sys.stderr)
        sys.exit(1)
