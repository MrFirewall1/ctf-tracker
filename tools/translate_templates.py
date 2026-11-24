"""Regelbaserte oversettelser av gjentatte maler i ICS-PCAP-katalogen (EN -> NO).

Brukes av tools/build_practice_no.py. Strenger som ikke matcher en mal oversettes for hånd i
tools/practice_no_manual.json. Ingen nettverk, ingen modell: kun faste regler.
"""
import re

CTF_TAIL_EN = ("ICS CTF flags usually hide in protocol fields — register values, write payloads, function codes or "
               "timing — rather than in plain text. Work it like an analyst: map the protocol, find the operations "
               "that don't belong, then decode.")
CTF_TAIL_NO = ("ICS CTF-flagg gjemmer seg vanligvis i protokollfelt — registerverdier, skrivenyttelast, funksjonskoder "
               "eller timing — og ikke i ren tekst. Jobb som en analytiker: kartlegg protokollen, finn operasjonene "
               "som ikke hører hjemme, og dekod.")

AEGIS_EN = ("AegisOT is a containerised OT testbed — HMIs and PLCs speaking Modbus/TCP over a simulated physical process. "
            "Each attack capture executes exactly one ATT&CK technique; this one is **{t}**, a network-level attack.\n\n"
            "Find the attacker host, the attack window and every packet that implements the technique, and explain the process impact.")
AEGIS_NO = ("AegisOT er et containerisert OT-testbed — HMI-er og PLS-er som snakker Modbus/TCP over en simulert fysisk prosess. "
            "Hver angrepsfangst utfører nøyaktig én ATT&CK-teknikk; denne er **{t}**, et angrep på nettverksnivå.\n\n"
            "Finn angriper-verten, angrepsvinduet og hver pakke som implementerer teknikken, og forklar effekten på prosessen.")

RULES = [
    (re.compile(r"^Show the packets that implement (.+)\.$"), r"Vis pakkene som implementerer \1."),
    (re.compile(r"^Read the ATT&CK page for (.+?) — the procedure examples tell you what to look for\.$"),
     r"Les ATT&CK-siden for \1 — prosedyreeksemplene viser hva du skal se etter."),
    (re.compile(r"^Map findings to ATT&CK for ICS \((.+)\)\.$"), r"Kartlegg funnene mot ATT&CK for ICS (\1)."),
    (re.compile(r"^Wireshark display filter for the protocol: (.+)$"), r"Wireshark-visningsfilter for protokollen: \1"),
    (re.compile(r"^Dangerous-operation filter: (.+)$"), r"Filter for farlige operasjoner: \1"),
    (re.compile(r"^Enumerate the (.+) operations present\.$"), r"List opp \1-operasjonene som finnes."),
    (re.compile(r"^Protocol deep-dive — (.+) \((\d+) unique captures?\)$"),
     lambda m: f"Protokoll-dykk — {m.group(1)} ({m.group(2)} unik{'e' if m.group(2) != '1' else ''} fangst{'er' if m.group(2) != '1' else ''})"),
]


def translate(s: str):
    """Returnerer norsk tekst hvis en mal passer, ellers None."""
    for rx, rep in RULES:
        if rx.match(s):
            return rx.sub(rep, s)
    m = re.match(re.escape(AEGIS_EN).replace(r"\{t\}", r"(.+?)"), s)
    if m:
        return AEGIS_NO.format(t=m.group(1))
    if s.endswith("\n\n" + CTF_TAIL_EN):
        head = s[: -len(CTF_TAIL_EN) - 2]
        m = re.match(r"A capture-the-flag challenge from (.+?)\.\s*(.*)$", head, re.S)
        if m:
            extra = m.group(2).strip()
            return f"En capture-the-flag-oppgave fra {m.group(1)}." + (f" {extra}" if extra else "") + "\n\n" + CTF_TAIL_NO
    return None


# ---- Del 2: gjentatte avsnitt med variable biter -------------------------------------------------------------
CONTROLS = {
    "baseline operation": "baseline-drift", "active directory": "Active Directory",
    "baseline after a software update": "baseline etter programvareoppdatering",
    "boundary firewall": "grensebrannmur", "centralised syslog": "sentralisert syslog",
    "Cisco ASA 5506 firewall": "Cisco ASA 5506-brannmur", "directory backup": "katalogsikkerhetskopi",
    "full disk-image backup": "full diskavbildningskopi", "host backups": "vertssikkerhetskopier",
    "least-privilege enforcement": "håndheving av minste privilegium",
    "MAC-address filtering": "MAC-adressefiltrering",
    "network-hardware patching": "patching av nettverksmaskinvare",
    "physical network connection controls": "fysiske kontroller av nettverkstilkobling",
    "server and ICS-device patching": "patching av servere og ICS-enheter",
}
NIST_PC_X = {
    "host-based firewalls enabled on the control-network hosts.": "vertsbaserte brannmurer aktivert på vertene i kontrollnettverket.",
    "a Veeam incremental backup.": "en inkrementell Veeam-sikkerhetskopi.",
    "Wireshark capturing on a control-network host.": "Wireshark som fanger på en vert i kontrollnettverket.",
    "a process historian collecting plant data.": "en prosesshistorian som samler anleggsdata.",
}
NIST_PC_TITLE = {"incremental backup": "inkrementell sikkerhetskopi", "packet capture on a host": "pakkefangst på en vert",
                 "process historian": "prosesshistorian"}
DETAILS = {
    "the managing node's SoC/PReq/PRes/SoA cycle is deterministic — anything off-cycle or a second managing node is an anomaly.":
        "den styrende nodens SoC/PReq/PRes/SoA-syklus er deterministisk — alt utenfor syklusen, eller en andre styrende node, er en anomali.",
    "Emerson ROC Plus (oil & gas flow computers) has no Wireshark dissector — use CISA's Zeek ICSNPP roc-plus parser; parameter writes and configuration changes are the targets.":
        "Emerson ROC Plus (strømningscomputere for olje og gass) har ingen Wireshark-dissektor — bruk CISAs Zeek ICSNPP roc-plus-parser; parameterskriving og konfigurasjonsendringer er målene.",
    "TriStation is the Triconex SIS engineering protocol — program download/upload and run/halt commands against a safety controller are the TRITON tradecraft.":
        "TriStation er Triconex SIS-ingeniørprotokollen — programnedlasting/-opplasting og run/halt-kommandoer mot en sikkerhetsstyring er TRITON-håndverket.",
    "C12.22 carries C12.19 table reads/writes to revenue meters — writes to configuration tables or procedure calls (e.g. disconnect) are the high-value operations.":
        "C12.22 bærer C12.19-tabell-lesinger/-skrivinger til avregningsmålere — skriving til konfigurasjonstabeller eller prosedyrekall (f.eks. frakobling) er operasjonene med høyest verdi.",
    "atomicWriteFile (7), createObject/deleteObject (10/11), writeProperty/writePropertyMultiple (15/16), deviceCommunicationControl (17 — silence a device) and reinitializeDevice (20); Who-Is (unconfirmed 8) is the discovery sweep.":
        "atomicWriteFile (7), createObject/deleteObject (10/11), writeProperty/writePropertyMultiple (15/16), deviceCommunicationControl (17 — gjør en enhet stille) og reinitializeDevice (20); Who-Is (ubekreftet 8) er oppdagelsessveipet.",
    "Write (3), WriteControl (5 — change the TwinCAT run state) and ReadWrite (9).":
        "Write (3), WriteControl (5 — endrer TwinCAT-kjøretilstanden) og ReadWrite (9).",
    "command frames (frame type 4) can turn PMU data transmission off or request configuration — normal from the PDC, suspicious from anywhere else.":
        "kommandorammer (rammetype 4) kan slå av PMU-dataoverføring eller be om konfigurasjon — normalt fra PDC-en, mistenkelig fra alle andre.",
    "WRITE (2), SELECT/OPERATE (3/4), DIRECT_OPERATE (5/6), COLD/WARM_RESTART (13/14), INITIALIZE_DATA/APPL (15/16), START/STOP_APPL (17/18), DISABLE_UNSOLICITED (21), OPEN/DELETE_FILE (25/27), ACTIVATE_CONFIG (31).":
        "WRITE (2), SELECT/OPERATE (3/4), DIRECT_OPERATE (5/6), COLD/WARM_RESTART (13/14), INITIALIZE_DATA/APPL (15/16), START/STOP_APPL (17/18), DISABLE_UNSOLICITED (21), OPEN/DELETE_FILE (25/27), ACTIVATE_CONFIG (31).",
    "CIP Reset (0x05), Start (0x06), Stop (0x07), Set Attribute Single (0x10), Execute PCCC (0x4B), Write Tag (0x4D), Write Tag Fragmented (0x53); ENIP ListIdentity (0x63) is the classic discovery broadcast.":
        "CIP Reset (0x05), Start (0x06), Stop (0x07), Set Attribute Single (0x10), Execute PCCC (0x4B), Write Tag (0x4D), Write Tag Fragmented (0x53); ENIP ListIdentity (0x63) er den klassiske oppdagelsesbroadcasten.",
    "GOOSE has no confirmed 'write' — the attack surface is the event stream itself: stNum jumping without a real state change, sqNum resets, bursts far above the retransmission curve, the test/simulation flag, or an unexpected source MAC publishing a known gocbRef.":
        "GOOSE har ingen bekreftet «write» — angrepsflaten er selve hendelsesstrømmen: stNum som hopper uten reell tilstandsendring, sqNum-tilbakestillinger, byger langt over retransmisjonskurven, test-/simuleringsflagget, eller en uventet kilde-MAC som publiserer en kjent gocbRef.",
    "write (service 5) changes IED settings or operates controls; getNameList (1) and getVariableAccessAttributes (6) map the IED data model; file services (fileOpen/fileRead/obtainFile) move configuration in and out.":
        "write (tjeneste 5) endrer IED-innstillinger eller betjener kontroller; getNameList (1) og getVariableAccessAttributes (6) kartlegger IED-ens datamodell; filtjenester (fileOpen/fileRead/obtainFile) flytter konfigurasjon inn og ut.",
    "control commands (TypeID 45 single, 46 double, 47 regulating step, 48–50 set-points, 51 bitstring, 58–64 time-tagged variants), interrogations (100 general, 101 counter), read (102), clock sync (103) and reset process (105).":
        "kontrollkommandoer (TypeID 45 enkel, 46 dobbel, 47 reguleringstrinn, 48–50 settpunkter, 51 bitstreng, 58–64 tidsstemplede varianter), interrogasjoner (100 generell, 101 teller), read (102), klokkesynkronisering (103) og tilbakestilling av prosess (105).",
    "writes (FC 5/6/15/16/22/23), diagnostics (FC 8 — restart / force-listen-only), device identification (FC 43/14, recon) and Schneider UMAS (FC 90, engineering).":
        "skrivinger (FC 5/6/15/16/22/23), diagnostikk (FC 8 — omstart / tving kun-lytting), enhetsidentifikasjon (FC 43/14, rekognosering) og Schneider UMAS (FC 90, ingeniørarbeid).",
    "memory-area write (0x0102), RUN (0x0401) and STOP (0x0402); controller data read (0x0501) identifies the PLC.":
        "skriving til minneområde (0x0102), RUN (0x0401) og STOP (0x0402); lesing av styringsdata (0x0501) identifiserer PLS-en.",
    "Write (node 673) and Call (712, method execution); Browse (527) maps the address space; check OpenSecureChannel/CreateSession for SecurityMode None and anonymous ActivateSession.":
        "Write (node 673) og Call (712, metodekjøring); Browse (527) kartlegger adresserommet; sjekk OpenSecureChannel/CreateSession for SecurityMode None og anonym ActivateSession.",
    "DCP Set (service 4) renames a device or changes its IP — an attacker can knock an IO-device off its controller; DCP Identify (5) is discovery.":
        "DCP Set (tjeneste 4) endrer navn på en enhet eller endrer IP-en — en angriper kan slå en IO-enhet av fra styringen sin; DCP Identify (5) er oppdagelse.",
    "write variable (0x05), program download (0x1A–0x1C), program upload (0x1D–0x1F — logic theft), PI-service (0x28 — start/restart/compress), PLC STOP (0x29) and security/password userdata (function group 5); SZL reads (function group 4) are device recon.":
        "write variable (0x05), programnedlasting (0x1A–0x1C), programopplasting (0x1D–0x1F — logikktyveri), PI-tjeneste (0x28 — start/omstart/komprimer), PLS STOP (0x29) og sikkerhets-/passord-userdata (funksjonsgruppe 5); SZL-lesinger (funksjonsgruppe 4) er enhetsrekognosering.",
    "S7comm-plus (0x72) from TIA Portal / HMIs to S7-1200/1500 PLCs; version 3 adds a 32-byte integrity digest and tshark has no built-in dissector, so read it structurally: who talks to the PLC, how often, message sizes, and payloads that repeat (a replay repeats its digest).":
        "S7comm-plus (0x72) fra TIA Portal / HMI-er til S7-1200/1500-PLS-er; versjon 3 legger til en 32-byte integritetssjekksum, og tshark har ingen innebygd dissektor, så les den strukturelt: hvem som snakker med PLS-en, hvor ofte, meldingsstørrelser, og nyttelaster som gjentar seg (en avspilling gjentar sjekksummen sin).",
}

_NIST_ROB_P = ("NIST's Cybersecurity for Smart Manufacturing Systems testbed includes a collaborative-robotics work cell: "
               "robots, a PLC and an HMI exchanging Modbus/TCP, captured at the cell switch and at each station. The captures "
               "are normal operation — no attacks — recorded while NIST exercised one low-baseline security control at a time.")
_NIST_ROB_NO = ("NISTs testbed for cybersikkerhet i smarte produksjonssystemer har en samarbeidende robotarbeidscelle: roboter, "
                "en PLS og et HMI som utveksler Modbus/TCP, fanget ved cellesvitsjen og ved hver stasjon. Fangstene er normal "
                "drift — ingen angrep — registrert mens NIST testet én sikkerhetskontroll med lav baseline om gangen.")
_NIST_PC_P = ("NIST's process-control testbed runs a Tennessee-Eastman-style chemical process with PLCs and HMIs talking "
              "EtherNet/IP-CIP, plus DCE-RPC from the Windows side. NIST recorded one run per low-baseline security control; this run is ")
_NIST_PC_T = (" A process-simulation log (*_simlog.dat) sits next to the capture.\n\nCharacterize the control network, measure the "
              "footprint of this run's control on it, and decide whether the control is safe for the process.")
_QS7 = ("QUT built a small Siemens S7 process plant — a reactor, a conveyor belt with a diverter gate and a water tank, controlled by "
        "S7 PLCs and an HMI — and attacked it with crafted S7comm writes from an attacker host. Each attack run was captured from "
        "the **attacker**, the **HMI** and the **master** PLC.")
_QS7_NO = ("QUT bygde et lite Siemens S7-prosessanlegg — en reaktor, et transportbånd med en avledergrind og en vanntank, styrt av "
           "S7-PLS-er og et HMI — og angrep det med konstruerte S7comm-skrivinger fra en angriper-vert. Hver angrepskjøring ble "
           "fanget fra **angriperen**, **HMI-et** og **master**-PLS-en.")
_QD = ('QUT built a DNP3 testbed — a master polling an outstation over DNP3/TCP — and used a Scapy-based attack framework to run each '
       'attack many times, capturing every run from three vantage points: the **master**, the **outstation** ("slave") and the '
       '**attacker**. Every packet of the master and outstation captures is labelled in the matching CSV (frame number, summary, label).')
_QD_NO = ("QUT bygde et DNP3-testbed — en master som poller en utstasjon over DNP3/TCP — og brukte et Scapy-basert angrepsrammeverk "
          "til å kjøre hvert angrep mange ganger, og fanget hver kjøring fra tre utsiktspunkter: **masteren**, **utstasjonen** "
          "(«slave») og **angriperen**. Hver pakke i master- og utstasjonsfangstene er merket i den tilhørende CSV-filen "
          "(rammenummer, sammendrag, etikett).")
_ADSC = ("ADSC (Singapore) recorded GOOSE traffic for normal operation, protection events (busbar, breaker failure, "
         "under-frequency load shedding), DoS, message suppression and data manipulation.\n\nThis challenge is the capture labeled ")
_ADSC_NO = ("ADSC (Singapore) registrerte GOOSE-trafikk for normal drift, vernhendelser (samleskinne, bryterfeil, "
            "underfrekvens-lastfrakobling), DoS, meldingsundertrykking og datamanipulering.\n\nDenne oppgaven er fangsten merket ")
_D4C = ("Data4Cyber is a labeled cyber-physical dataset for distribution-grid management systems: each scenario folder holds "
        "network-tap, attacker-only and benign-only captures plus aligned physical measurements.\n\n")
_D4C_NO = ("Data4Cyber er et merket cyberfysisk datasett for styringssystemer i distribusjonsnett: hver scenariomappe inneholder "
           "nettverks-tap-, bare-angriper- og bare-godartede fangster pluss tilhørende fysiske målinger.\n\n")
_LEMAY = ("Lemay & Fernandez (CSET 2016) built simulated SCADA networks — a master polling Modbus RTUs — and recorded normal "
          "operation plus labelled malicious activity, to give ICS intrusion-detection research realistic data.")
_CY4 = ("Cyber4OT (Warsaw University of Technology testbed) records an OT network's normal activity and a full attack: "
        "reconnaissance, then disconnection of the legitimate Modbus/TCP session and PLC hijacking. This challenge covers one band "
        "of the dataset's 96 traces, as described in its README.")
_CY4_NO = ("Cyber4OT (testbed ved Warszawa teknologiske universitet) registrerer normal aktivitet i et OT-nettverk og et fullt "
           "angrep: rekognosering, deretter frakobling av den legitime Modbus/TCP-sesjonen og kapring av PLS-en. Denne oppgaven "
           "dekker ett bånd av datasettets 96 spor, slik det er beskrevet i README-filen.")

_QDNP3_RUN = re.compile(r"^\n\nThis challenge is one run of \*\*(.+?)\*\*: (.+?) The dataset contains (\d+) runs of this attack type in total — once you have solved this one, the others are practice\.$", re.S)
_QS7_ATT = re.compile(r"^\n\nThis challenge contains one run of each attack on \*\*(.+?)\*\*: (.+?)\. Each run is tiny — the skill is decoding S7comm precisely\.$", re.S)
_DESC = {
    "the attacker ARP-poisons both ends and relays the traffic unchanged.": "angriperen ARP-forgifter begge ender og videresender trafikken uendret.",
    "the attacker scans the network and probes for DNP3 devices.": "angriperen skanner nettverket og leter etter DNP3-enheter.",
}
_TARGET = {"set-points, global reset and emergency stop": "settpunkter, global tilbakestilling og nødstopp",
           "the conveyor belt": "transportbåndet", "the reactor": "reaktoren", "the water tank": "vanntanken"}
_RUNTITLE = {"Man-in-the-middle — forwarding only": "Mann-i-midten — kun videresending",
             "Reconnaissance — nmap and DNP3 discovery": "Rekognosering — nmap og DNP3-oppdagelse"}

# Overskrifter/korte setninger som oversettes ordrett
EXACT = {
    "Identify master, outstation and attacker (IP **and** MAC).": "Identifiser master, utstasjon og angriper (IP **og** MAC).",
    "Find the attack window and every attack packet.": "Finn angrepsvinduet og hver angrepspakke.",
    "Explain what the attack does to the DNP3 session and the process data.": "Forklar hva angrepet gjør med DNP3-sesjonen og prosessdataene.",
    "Write a detection that survives the other runs.": "Skriv en deteksjon som holder mot de andre kjøringene.",
    "Read the master's and the outstation's captures side by side — what one sends and the other receives should match.":
        "Les masterens og utstasjonens fangster side om side — det den ene sender og den andre mottar skal stemme overens.",
    "MACs do not lie as easily as IPs on a switched LAN.": "MAC-adresser lyver ikke like lett som IP-adresser på et svitsjet LAN.",
    "For each run: which PLC, which memory area / DB, which byte.bit address, which value?":
        "For hver kjøring: hvilken PLS, hvilket minneområde / DB, hvilken byte.bit-adresse, hvilken verdi?",
    "Write a detection for unauthorised writes to those addresses.": "Skriv en deteksjon for uautoriserte skrivinger til de adressene.",
    "S7comm function 0x05 = Write Var; 0x04 = Read Var.": "S7comm-funksjon 0x05 = Write Var; 0x04 = Read Var.",
    "The run's name tells you the effect — your job is to prove which bytes cause it.":
        "Kjøringens navn forteller effekten — jobben din er å bevise hvilke byte som forårsaker den.",
    "R-GOOSE and tunnelled GOOSE": "R-GOOSE og tunnelert GOOSE",
    "Establish the device's normal communication partners.": "Fastslå enhetens normale kommunikasjonspartnere.",
    "Find reconnaissance against it.": "Finn rekognosering mot den.",
    "Find any control, write or exploit traffic and its source.": "Finn all kontroll-, skrive- eller utnyttelsestrafikk og kilden til den.",
    "Compare the first minutes (setup/normal) with the rest of the capture.": "Sammenlign de første minuttene (oppsett/normal) med resten av fangsten.",
    "Attribute every write/control operation to a source IP.": "Tilskriv hver skrive-/kontrolloperasjon en kilde-IP.",
    "Characterize the capture.": "Karakteriser fangsten.",
    "Find the malicious or abnormal activity it is labeled for.": "Finn den ondsinnede eller unormale aktiviteten den er merket for.",
    "Write a detection and test it against the normal capture.": "Skriv en deteksjon og test den mot den normale fangsten.",
    "The filename is the dataset's label — prove it from the packets.": "Filnavnet er datasettets etikett — bevis det ut fra pakkene.",
    "Compare against the normal/baseline capture of the same dataset.": "Sammenlign med den normale fangsten/baselinen i samme datasett.",
    "Identify the CIP service and object/attribute targeted in each capture.": "Identifiser CIP-tjenesten og objektet/attributtet som er målet i hver fangst.",
    "Determine whether each attempt succeeded (CIP general status).": "Avgjør om hvert forsøk lyktes (CIP general status).",
    "Map each attempt to ATT&CK for ICS.": "Kartlegg hvert forsøk mot ATT&CK for ICS.",
    "Set Attribute Single (0x10) / Set Attribute List (0x04) against the Time Sync or TCP/IP Interface / Ethernet Link objects is what to look for.":
        "Det du skal se etter er Set Attribute Single (0x10) / Set Attribute List (0x04) mot objektene Time Sync eller TCP/IP Interface / Ethernet Link.",
    "The response's general status tells you if the controller accepted the change.": "Svarets general status forteller om styringen godtok endringen.",
    "Cyber4OT — macof + tcpkill: hijacking the Modbus session": "Cyber4OT — macof + tcpkill: kapring av Modbus-sesjonen",
    "Data4Cyber — S1 — Industroyer against the PV system": "Data4Cyber — S1 — Industroyer mot solcelleanlegget",
    "Data4Cyber — S1 — Industroyer against the PV system (alternate run)": "Data4Cyber — S1 — Industroyer mot solcelleanlegget (alternativ kjøring)",
    "ICS CTF (工控CTF) — find the flag in industrial traffic": "ICS CTF (工控CTF) — finn flagget i industriell trafikk",
    "Identify the protocols and endpoints.": "Identifiser protokollene og endepunktene.",
    "Read writes, not just reads — attackers 'leave' the flag by writing it.": "Les skrivinger, ikke bare lesinger — angripere «legger igjen» flagget ved å skrive det.",
    "Concatenate register values in order and decode big-endian pairs to ASCII.": "Sett sammen registerverdiene i rekkefølge og dekod big-endian-par til ASCII.",
    "QUT DNP3 — Man-in-the-middle — forwarding only": "QUT DNP3 — Mann-i-midten — kun videresending",
    "QUT DNP3 — Reconnaissance — nmap and DNP3 discovery": "QUT DNP3 — Rekognosering — nmap og DNP3-oppdagelse",
    "QUT S7comm — attacking set-points, global reset and emergency stop": "QUT S7comm — angrep på settpunkter, global tilbakestilling og nødstopp",
    "QUT S7comm — attacking the conveyor belt": "QUT S7comm — angrep på transportbåndet",
    "QUT S7comm — attacking the reactor": "QUT S7comm — angrep på reaktoren",
    "QUT S7comm — attacking the water tank": "QUT S7comm — angrep på vanntanken",
    "QUT S7comm — flooding the process": "QUT S7comm — flooding av prosessen",
    "ControlLogix 5000 — change date/time and port-configuration attempts": "ControlLogix 5000 — forsøk på å endre dato/tid og portkonfigurasjon",
    "S7comm — engineering actions (downloads, passwords, mode changes)": "S7comm — ingeniørhandlinger (nedlastinger, passord, moduswitching)",
    "S4x15 CTF — BACnet building controllers": "S4x15 CTF — BACnet-bygningsstyringer",
    "S4x15 CTF — corporate IT host & Advantech device": "S4x15 CTF — bedrifts-IT-vert og Advantech-enhet",
    "S4x15 CTF — the GE iFIX HMI client & server": "S4x15 CTF — GE iFIX HMI-klient og -server",
    "S4x15 CTF — the PLCs (Modicon & MicroLogix)": "S4x15 CTF — PLS-ene (Modicon og MicroLogix)",
    "S4x15 ICS Village CTF — reconstruct the competition": "S4x15 ICS Village CTF — rekonstruer konkurransen",
    "Identify every device and its role from the per-host captures.": "Identifiser hver enhet og rollen den har ut fra fangstene per vert.",
    "Find reconnaissance against each device.": "Finn rekognosering mot hver enhet.",
    "Find the control/engineering operations that would have scored CTF points.": "Finn kontroll-/ingeniøroperasjonene som ville gitt CTF-poeng.",
    "Build a timeline of the attacks.": "Bygg en tidslinje over angrepene.",
    "The Modicon speaks Modbus (and Schneider's UMAS function 90); the MicroLogix speaks EtherNet/IP with PCCC encapsulated in CIP (service 0x4B).":
        "Modicon snakker Modbus (og Schneiders UMAS-funksjon 90); MicroLogix snakker EtherNet/IP med PCCC innkapslet i CIP (tjeneste 0x4B).",
    "The iFIX HMI captures show what the operators saw — and whether anyone else talked to the PLCs directly.":
        "iFIX HMI-fangstene viser hva operatørene så — og om noen andre snakket direkte med PLS-ene.",
    "Look for BACnet writeProperty/reinitializeDevice against the building controllers.":
        "Let etter BACnet writeProperty/reinitializeDevice mot bygningsstyringene.",
    "Measure the rate of each flood.": "Mål raten til hver flood.",
    "Identify what each flood writes.": "Identifiser hva hver flood skriver.",
    "Assess the process impact vs a single write.": "Vurder prosesseffekten mot en enkelt skriving.",
    "Write a rate-based detection.": "Skriv en ratebasert deteksjon.",
    "Compare with the single-write runs in the other QUT S7comm challenges.": "Sammenlign med kjøringene med enkeltskriving i de andre QUT S7comm-oppgavene.",
    "Dangerous-operation filter:": "Filter for farlige operasjoner:",
    "TU Delft substation — Baseline": "TU Delft transformatorstasjon — Baseline",
    "NIST process-control testbed — Active Directory with least privilege": "NIST prosesskontroll-testbed — Active Directory med minste privilegium",
    "Characterize the traffic.": "Karakteriser trafikken.",
}


_DEEP_RX = re.compile(r"^Every public (.+?) sample in this range, deduplicated by SHA-256 across (.+?)\. Use it to learn what the "
                      r"protocol looks like on the wire — roles, operations, normal cadence — and to practice spotting the "
                      r"operations attackers abuse: (.+)$", re.S)


def translate_all(s: str):
    """Mal-/frasebasert oversettelse. None hvis ingenting passer (teksten beholdes da på engelsk)."""
    if s in EXACT:
        return EXACT[s]
    t = translate(s)
    if t is not None:
        return t
    m = _DEEP_RX.match(s)
    if m and m.group(3) in DETAILS:
        return (f"Hvert offentlige {m.group(1)}-eksempel i denne samlingen, dedupliserte på SHA-256 på tvers av {m.group(2)}. "
                f"Bruk det til å lære hvordan protokollen ser ut på ledningen — roller, operasjoner, normal takt — og til å "
                f"øve på å se operasjonene angripere misbruker: {DETAILS[m.group(3)]}")
    m = re.match(r"^NIST robotics cell — (.+?)( \(CL\d+\.\d\))?$", s)
    if m and m.group(1) in CONTROLS:
        return f"NIST robotcelle — {CONTROLS[m.group(1)]}{m.group(2) or ''}"
    m = re.match(r"^NIST process-control testbed — (.+)$", s)
    if m and m.group(1) in NIST_PC_TITLE:
        return f"NIST prosesskontroll-testbed — {NIST_PC_TITLE[m.group(1)]}"
    m = re.match(r"^Characterize the traffic (.+) adds to the cell\.$", s)
    if m and m.group(1) in CONTROLS:
        return f"Karakteriser trafikken {CONTROLS[m.group(1)]} tilfører cellen."
    if s.startswith(_NIST_ROB_P):
        m = re.match(r"^\n\nThis scenario \((CL\d+\.\d)\) exercises \*\*(.+?)\*\*\. Your job is the question OT defenders actually "
                     r"face: what does this security activity look like on the wire, and does it disturb the control loop\?$",
                     s[len(_NIST_ROB_P):], re.S)
        if m and m.group(2) in CONTROLS:
            return (_NIST_ROB_NO + f"\n\nDette scenarioet ({m.group(1)}) tester **{CONTROLS[m.group(2)]}**. Oppgaven er spørsmålet "
                    "OT-forsvarere faktisk møter: hvordan ser denne sikkerhetsaktiviteten ut på ledningen, og forstyrrer den "
                    "reguleringssløyfen?")
    if s.startswith(_NIST_PC_P) and s.endswith(_NIST_PC_T):
        x = s[len(_NIST_PC_P):-len(_NIST_PC_T)]
        if x in NIST_PC_X:
            return ("NISTs prosesskontroll-testbed kjører en kjemisk prosess i Tennessee-Eastman-stil, med PLS-er og HMI-er som "
                    "snakker EtherNet/IP-CIP, pluss DCE-RPC fra Windows-siden. NIST registrerte én kjøring per sikkerhetskontroll "
                    f"med lav baseline; denne kjøringen er {NIST_PC_X[x]} En prosessimuleringslogg (*_simlog.dat) ligger ved siden "
                    "av fangsten.\n\nKarakteriser kontrollnettverket, mål fotavtrykket til denne kjøringens kontroll på det, og "
                    "avgjør om kontrollen er trygg for prosessen.")
    if s.startswith(_QD):
        m = _QDNP3_RUN.match(s[len(_QD):])
        if m and m.group(1) in _RUNTITLE and m.group(2) in _DESC:
            return (_QD_NO + f"\n\nDenne oppgaven er én kjøring av **{_RUNTITLE[m.group(1)]}**: {_DESC[m.group(2)]} Datasettet "
                    f"inneholder totalt {m.group(3)} kjøringer av denne angrepstypen — når du har løst denne, er de andre øvelse.")
    if s.startswith(_QS7):
        rest = s[len(_QS7):]
        m = _QS7_ATT.match(rest)
        if m and m.group(1) in _TARGET:
            return (_QS7_NO + f"\n\nDenne oppgaven inneholder én kjøring av hvert angrep på **{_TARGET[m.group(1)]}**: {m.group(2)}. "
                    "Hver kjøring er liten — ferdigheten er å dekode S7comm presist.")
        m = re.match(r"^\n\nThese are the master-side captures of 9 flooding runs \((.+?)\): the attacker repeats one process write at high rate\.$", rest, re.S)
        if m:
            return (_QS7_NO + f"\n\nDette er masterside-fangstene av 9 flooding-kjøringer ({m.group(1)}): angriperen gjentar én "
                    "prosesskriving i høy rate.")
    if s.startswith(_ADSC):
        return _ADSC_NO + s[len(_ADSC):]
    if s.startswith(_D4C):
        m = re.match(r"^This challenge covers the '(.+?)' set \((\d+) capture file\(s\)\)\. Characterize it, find the attack \(if any\) and write a detection\.$", s[len(_D4C):])
        if m:
            return _D4C_NO + (f"Denne oppgaven dekker settet «{m.group(1)}» ({m.group(2)} fangstfil(er)). Karakteriser det, finn "
                              "angrepet (hvis det finnes) og skriv en deteksjon.")
    if s.startswith(_LEMAY):
        return None
    if s.startswith(_CY4):
        tail = s[len(_CY4):]
        if tail.startswith("\n\nMAC flooding (macof)"):
            return _CY4_NO + "\n\nMAC-flooding (macof) for å se slave-PLS-ens trafikk, deretter tcpkill for å rive ned masterens Modbus TCP-forbindelse."
    return None
