# CTF-tracker (norsk)

> Dette er den opprinnelige norske beskrivelsen. Hovedfilen er nå [README.md](README.md) (engelsk). Raskeste oppstart: `./setup.sh` og så `./run.sh`. Appen er åpen kildekode (MIT, se [LICENSE](LICENSE)).

Lokal webapp for å logge CTF-oppgaver, skrive egne forklaringer og se fremgang. Ingen AI-funksjoner, ingen eksterne API-er, ingen CDN: den fungerer helt offline.

> ## ⚠️ Advarsel: hva du IKKE skal skrive eller sjekke inn
> Datamappen blir et git-repo som pushes til GitHub (antatt privat, men reg det som delt).
> - **Ikke** skriv interne firmaopplysninger, passord, tokens eller ekte nettverksdata (IP-er, vertsnavn, trafikk fra ekte miljøer) i forklaringene.
> - **Ikke** sjekk inn rå konkurransefiler eller PCAP-er du ikke har rett til å dele. Appen lagrer bare tekst; hold filene dine utenfor datamappen.

## Oppstart

```bash
cd ~/ctf-tracker
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # første gang
export CTF_DATA_DIR=/mnt/d/ctf-data      # SSD-stien din (eller sett data_dir i config.json)
.venv/bin/python -m app init             # første gang: setter opp mappen
.venv/bin/python -m app                  # starter på http://127.0.0.1:5000
```

## Peke appen mot SSD-en

Stien settes av, i prioritert rekkefølge:
1. miljøvariabelen `CTF_DATA_DIR`
2. `data_dir` i `config.json` (kopier `config.example.json`)

Det finnes ingen standardsti. Mappen må **allerede finnes** og være satt opp med `python -m app init`, som lager `tasks/`, `.gitignore` og markørfilen `.ctf-tracker`. Hvis stien mangler, SSD-en ikke er montert (tom monteringsmappe uten markørfil), eller mappen ikke er skrivbar, viser appen et rødt banner og nekter å lagre (HTTP 503). Den oppretter aldri data et annet sted.

## Datalagring

- Én fil per oppgave: `<CTF_DATA_DIR>/tasks/ÅÅÅÅ-MM-DD-tittel.md`, med YAML-frontmatter og forklaringen som markdown. Filene er fasit og passer godt i git.
- Skriving er trygg: skriver til en midlertidig fil, `fsync`, og så `rename` over målfilen. Trekker du ut SSD-en midt i en lagring, er enten gammel eller ny versjon intakt.
- Ingen SQLite-indeks ennå: statistikken beregnes direkte fra filene, noe som er raskt nok for hundrevis av oppgaver.

## Definisjoner i dashboardet

- **Løst** = løst alene eller med hint. **Løst med fasit teller som ikke løst**, slik at svake områder ikke skjules.
- **Treningsdag** = dag med minst én logget oppgave. **Streak** = sammenhengende dager (i går teller fortsatt).
- **Svakeste områder** = kategorier/protokoller med minst 2 oppgaver og løsningsrate under 100 %, sortert stigende.

## Git og GitHub

Datamappen på SSD-en er et eget git-repo (ikke selve appkoden).

1. Opprett et **tomt, privat** repo på GitHub (uten README, ellers får du ulik historikk).
2. Koble det til, én gang:
   ```bash
   .venv/bin/python -m app git-init git@github.com:MrFirewall1/ctf-data.git
   ```
   Kommandoen kjører `git init`, setter remote `origin`, og committer `.gitignore`, markørfilen og `tasks/`. Den kan kjøres flere ganger. Hvis du ikke har satt `user.name`/`user.email` i git, settes en nøytral identitet (`CTF-tracker`) kun i dette repoet.
3. Hver gang du lagrer en oppgave committes akkurat den filen: `Legg til oppgave: <tittel>` (ny) eller `Oppdater oppgave: <tittel>`. Mislykkes git, er oppgaven likevel lagret, og du får en melding i skjemaet.
4. **Push er manuell**: siden **Git** i appen har en knapp. Det skjer aldri automatisk.

Push bruker SSH-nøkkelen din uten passordspørsmål (`BatchMode`). Har nøkkelen passfrase, må den ligge i `ssh-agent`. Nøkkelen må være lagt til på GitHub. Bare ssh- og https-URL-er godtas. `.gitignore` utelater `*.pdf`, `reports/`, `*.tmp` og SQLite-filer.

## PDF-rapport

Siden **Rapport**: velg periode og/eller oppgaver, og trykk «Lag PDF». Forside, sammendrag med diagrammer, og så én side per oppgave med metadata og forklaringene dine uendret (kun lange kodelinjer brytes visuelt). Laget med reportlab, uten systembibliotek. En kopi lagres i `<CTF_DATA_DIR>/reports/`, som ligger i `.gitignore`. Uten SSD nekter appen å lage rapport.

## Oppvarming, Oppgaver og egne øvelser

- **Oppvarming** gir en intro til hver kategori og to små oppgaver i hver. **Oppgaver** viser hele den lokale katalogen (`app/practice.json`) med filtre og søk. Den lastes ikke fra nett. «Logg denne» forhåndsutfyller skjemaet, og oppgaven markeres som logget via taggen `practice-<id>`.
- LabEx-oppgavene er bare titler og lenker med korte beskrivelser skrevet av meg. Selve labene åpnes hos LabEx (krever nett).
- **Språk (EN/NO):** oppgavene er engelske som standard, med en «Norsk»-knapp (og «Oversett» per kort). Norsk tekst ligger ferdig i `app/practice.json` (feltet `no`). Den ble laget på forhånd, så appen bruker verken AI, nett eller oversettelsestjeneste. «Logg denne» bruker språket du ser.
- **Import fra ICS-PCAP-Challenges** (engangs): `python -I tools/import_ics_pcap.py ~/ctf-downloads/ICS-PCAP-Challenges 12`, deretter `python -I tools/build_practice_no.py`. Importerer bare tittel, scenario, mål og hint, aldri løsninger. Datasettene (PCAP) lastes ned separat med `scripts/fetch.py` i det repoet, til en mappe utenfor datamappen din.
- Fire egne øvelser med **tilfeldige flagg** genereres lokalt. Flaggene skrives aldri ut, og bare hash lagres:

```bash
.venv/bin/python -m labs generate ~/ctf-labs     # mappen må være ny/tom og utenfor datamappen
.venv/bin/python -m labs check ~/ctf-labs hidden-file 'CTF{...}'
```

Øvelser: `hidden-file`, `log-secret`, `env-leak`, `modbus-flag` (liten PCAP med syntetiske adresser fra 192.0.2.0/24). Kjør `generate` på nytt i en ny mappe for nye flagg.

## Tester

```bash
.venv/bin/python -m pytest
```

## Kjøre i Kali (eller på en annen maskin)

Appen er bare Flask og kjører lokalt på `127.0.0.1:5000`, så du åpner den i nettleseren på samme maskin. Ingen nettside på GitHub trengs, og ingen skal legges ut offentlig.

1. Legg **appkoden** i et eget *privat* GitHub-repo (ikke datamappen, ikke `.venv`, ikke `config.json`), og `git clone` det i Kali.
2. `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
3. Klon **datarepoet** ditt (det som har oppgavefilene dine) til en mappe i Kali, og pek `CTF_DATA_DIR` dit. Skriv og push derfra, så følger Windows og Kali samme historikk (`git pull` før du begynner).
4. Last ned PCAP-er rett i Kali, bare det du trenger: `git clone https://github.com/SackOfHacks/ICS-PCAP-Challenges` og `python3 scripts/fetch.py <datasett>` (trenger `p7zip-full`). Sett `CTF_DOWNLOADS_DIR` til `<repo>/data`.

Under «Åpne oppgaven» på Oppvarming står hver fil med størrelse og en «Last ned»-lenke når filen finnes.
