# Vodostaj Drine - Bajina Basta -> ntfy notifikacija

Mala automatizacija koja proverava vodostaj Drine na stanici Bajina Basta
(zvanicni podaci RHMZ Srbije) i salje ti push notifikaciju na telefon
(preko [ntfy.sh](https://ntfy.sh)) kad god se vrednost promeni.

Izvor podataka: https://www.hidmet.gov.rs/latin/osmotreni/nrt_tabela_grafik.php?hm_id=45865&period=7
("Casovne vrednosti vodostaja, poslednjih 7 dana" - automatska stanica,
ocitavanje na svakih 30 min). RHMZ ove podatke oznacava kao "privremene,
nekontrolisane" - nagle promene mogu biti realne (npr. ispustanje vode
iz HE Bajina Basta / Perucac), a ne nuzno greska.

## Kako radi

1. GitHub Actions na svakih 30 minuta (podesivo u
   `.github/workflows/check.yml`) pokrece `check_water_level.py`.
2. Skripta skine i parsira najnoviji (prvi) red iz RHMZ tabele.
3. Poredi novu vrednost sa poslednjom sacuvanom (`state/last_state.json`).
4. Ako se vrednost promenila, posalje notifikaciju preko ntfy.sh i
   commit-uje novo stanje nazad u repo.
5. Ako nema promene - nista se ne desava (tih rad).

## Podesavanje (jednom)

### 1. Instaliraj ntfy na telefon

- Android: [ntfy na Google Play](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
- iOS: [ntfy na App Store](https://apps.apple.com/us/app/ntfy/id1625396347)

Ntfy topici nisu zasticeni lozinkom - ko god zna naziv topica moze da
salje/cita poruke na njemu. Zato izaberi dovoljno "nepogodljiv" naziv,
npr. neki nasumican string:

```
drina-bb-9f2k7x1qz
```

U aplikaciji dodaj (subscribe) topik sa tim tacnim nazivom.

### 2. Napravi GitHub repo i push-uj ovaj kod

```bash
cd drina-vodostaj-monitor
git init
git add .
git commit -m "Initial commit: monitor vodostaja Drine"
git branch -M main
git remote add origin <URL_TVOG_GITHUB_REPO>
git push -u origin main
```

### 3. Dodaj GitHub Secret

U repo-u na GitHub-u: **Settings -> Secrets and variables -> Actions ->
New repository secret**

- Name: `NTFY_TOPIC`
- Value: naziv topica koji si izabrao gore (npr. `drina-bb-9f2k7x1qz`)

### 4. Testiraj odmah

U tabu **Actions** izaberi workflow "Provera vodostaja Drine (Bajina
Basta)" i klikni **Run workflow** da odmah pokrenes proveru bez cekanja
na cron. Prvi run samo cuva bazno stanje (bez notifikacije) - tek od
drugog runa, kad se vrednost promeni, stize notifikacija.

## Podesavanje ucestalosti provere

U `.github/workflows/check.yml`, linija sa `cron: "*/30 * * * *"` - format
je standardni cron (UTC vreme). Trenutno proverava na svakih 30 minuta,
sto prati ucestalost same RHMZ automatske stanice.

## Lokalno testiranje

```bash
pip install -r requirements.txt
export NTFY_TOPIC=drina-bb-9f2k7x1qz
python check_water_level.py
```
