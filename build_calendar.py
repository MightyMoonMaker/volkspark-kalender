"""
Volkspark-Kalender
==================
Erzeugt die Kalenderdatei docs/volkspark.ics mit allen Veranstaltungen in
Barclays Arena und Volksparkstadion. Ablauf:
  1. Termine aus drei Quellen holen (Arena-PDF, HSV-Spielplan, Baustellen).
  2. Pro Tag und Ort einen Kalendertermin bauen, der das Sperrfenster abdeckt.
  3. Werktags eine Erinnerung anhaengen.
  4. Alles als .ics-Datei speichern.
"""

import io, re, uuid
import xml.etree.ElementTree as ET            # zum Lesen der XML-Daten der Stadt
from datetime import datetime, timedelta, time, date
from zoneinfo import ZoneInfo
from pathlib import Path

import requests                               # Webseiten/Dateien herunterladen
import pdfplumber                             # Text aus PDF auslesen
from icalendar import Calendar, Event, Alarm  # Kalenderdatei bauen

# ---------------------------------------------------------------------------
# Einstellungen: Hier kann man das Verhalten anpassen, ohne den Rest anzufassen
# ---------------------------------------------------------------------------

TZ = ZoneInfo("Europe/Berlin")  # Alle Zeiten in deutscher Zeit

# Quelle 1: Terminliste der Barclays Arena als PDF
ARENA_PDF = "https://www.barclays-arena.de/events-tickets/pdf/"

# Quelle 2: HSV-Spielplan als iCal-Feed (von fussball-spielplan.de),
# enthaelt Heim- und Auswaertsspiele, wir filtern unten die Heimspiele heraus
HSV_ICS = ("https://www.google.com/calendar/ical/"
           "akmeuj5pmof2818296883hrrok@group.calendar.google.com/public/basic.ics")

# Quelle 3: Offener Datendienst der Stadt Hamburg mit Baustellen und Sperrungen
BAUSTELLEN_WFS = ("https://geodienste.hamburg.de/hh_wfs_baustellen?SERVICE=WFS"
                  "&VERSION=1.1.0&REQUEST=GetFeature&typename=de.hh.up:baustelle")
# Nur Meldungen, die eine dieser Strassen erwaehnen, landen im Kalender
STRASSEN = ["Uwe-Seeler-Allee", "Sylvesterallee", "Stadionstraße"]

# Sperrfenster: Termin beginnt VORLAUF vor dem Event und endet
# DAUER + NACHLAUF nach dem Beginn der letzten Vorstellung des Tages
VORLAUF = timedelta(hours=3)      # Sperrung vor Beginn
DAUER = timedelta(hours=3)        # geschaetzte Dauer einer Veranstaltung
NACHLAUF = timedelta(hours=1)     # Abreise-Stau nach dem Ende

ERINNERUNG = time(14, 30)         # Uhrzeit der Erinnerung an Werktagen

# ---------------------------------------------------------------------------
# Muster zum Erkennen von Daten im Text
# ---------------------------------------------------------------------------

# Eine Zeile im Arena-PDF sieht so aus: "11.11.2026 Mi. 19:30 koRn"
# -> Datum, Wochentag, Uhrzeit, Name der Veranstaltung
ZEILE = re.compile(r"^(\d{2}\.\d{2}\.\d{4})\s+\w{2}\.\s+(\d{1,2}:\d{2})\s+(.+)$")
DATUM_DE = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b")   # z. B. 24.12.2026
DATUM_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})")       # z. B. 2026-12-24


# ---------------------------------------------------------------------------
# Quelle 1: Barclays Arena
# ---------------------------------------------------------------------------

def arena_events():
    """Laedt das Arena-PDF und liefert pro Vorstellung (Beginn, Titel, Ort)."""
    pdf = requests.get(ARENA_PDF, timeout=60).content

    # Den Text aller Seiten zu einem langen Text zusammenfuegen
    text = ""
    with pdfplumber.open(io.BytesIO(pdf)) as doc:
        for page in doc.pages:
            text += (page.extract_text() or "") + "\n"

    # Jede Zeile pruefen: Passt sie zum Muster "Datum Tag Uhrzeit Titel"?
    # Zeilen ohne Datum (z. B. Tour-Untertitel) werden einfach uebersprungen.
    for line in text.splitlines():
        m = ZEILE.match(line.strip())
        if m:
            start = datetime.strptime(f"{m[1]} {m[2]}", "%d.%m.%Y %H:%M")
            yield start.replace(tzinfo=TZ), m[3].strip(), "Barclays Arena"


# ---------------------------------------------------------------------------
# Quelle 2: HSV-Heimspiele
# ---------------------------------------------------------------------------

def hsv_heimspiele():
    """Liest den HSV-Spielplan und liefert nur die Heimspiele."""
    cal = Calendar.from_ical(requests.get(HSV_ICS, timeout=60).content)
    for ev in cal.walk("VEVENT"):
        titel = str(ev.get("summary", ""))

        # Bei Fussball steht die Heimmannschaft vorne: "Hamburger SV - Bayern".
        # Steht der HSV nicht vor dem Bindestrich, ist es ein Auswaertsspiel.
        heim = titel.split("-")[0]
        if "Hamburger" not in heim and "HSV" not in heim:
            continue

        start = ev.decoded("dtstart")
        # Ist der Anstoss noch nicht festgelegt, steht oft nur ein Datum drin.
        # Dann nehmen wir vorsichtshalber Samstag-Standard 15:30 Uhr an.
        if not isinstance(start, datetime):
            start = datetime.combine(start, time(15, 30))
        if start.tzinfo is None:
            start = start.replace(tzinfo=TZ)
        yield start.astimezone(TZ), titel, "Volksparkstadion"


# ---------------------------------------------------------------------------
# Quelle 3: Baustellen und Sperrungen der Stadt
# ---------------------------------------------------------------------------

def baustellen():
    """Durchsucht die Baustellen-Daten der Stadt nach unseren Strassen.
    Liefert (erster Tag, letzter Tag, Beschreibung)."""
    root = ET.fromstring(requests.get(BAUSTELLEN_WFS, timeout=60).content)

    # Jede Baustelle steht in einem eigenen "featureMember"-Eintrag
    for member in root.iter():
        if not member.tag.endswith("featureMember"):
            continue

        # Den ganzen Text des Eintrags zusammensetzen und nach Strassen suchen
        text = " ".join(t.strip() for t in member.itertext() if t.strip())
        if not any(s.lower() in text.lower() for s in STRASSEN):
            continue

        # Alle Datumsangaben im Text einsammeln (deutsches und ISO-Format)
        daten = [date(int(y), int(m), int(d)) for d, m, y in DATUM_DE.findall(text)]
        daten += [date(int(y), int(m), int(d)) for y, m, d in DATUM_ISO.findall(text)]
        if not daten:
            # Ohne Datum koennen wir keinen Termin bauen -> nur im Log melden
            print("Sperrung ohne Datum gefunden:", text[:200])
            continue

        # Fruehestes Datum = Beginn, spaetestes = Ende der Sperrung
        yield min(daten), max(daten), text[:500]


# ---------------------------------------------------------------------------
# Hilfsfunktion
# ---------------------------------------------------------------------------

def nach_tagen(events):
    """Gruppiert Vorstellungen nach (Tag, Ort), damit z. B. eine Nachmittags-
    und eine Abendvorstellung zu einem einzigen Kalendertermin werden."""
    tage = {}
    for start, titel, ort in events:
        tage.setdefault((start.date(), ort), []).append((start, titel))
    return tage


# ---------------------------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------------------------

def main():
    # Leeren Kalender anlegen, der Name erscheint in der Kalender-App
    cal = Calendar()
    cal.add("prodid", "-//Volkspark Sperrungen//DE")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "Volkspark Events")

    # --- Veranstaltungen aus Arena und Stadion ---
    alle = list(arena_events()) + list(hsv_heimspiele())
    for (tag, ort), liste in nach_tagen(alle).items():
        liste.sort()
        erster, letzter = liste[0][0], liste[-1][0]

        # Sperrfenster: ab VORLAUF vor der ersten bis nach der letzten Vorstellung
        von, bis = erster - VORLAUF, letzter + DAUER + NACHLAUF
        titel = " / ".join(sorted({t for _, t in liste}))

        ev = Event()
        # Feste ID pro Tag und Ort: So erkennt die Kalender-App bei jedem
        # Update denselben Termin wieder, statt Dubletten anzulegen.
        ev.add("uid", str(uuid.uuid5(uuid.NAMESPACE_URL, f"{tag}-{ort}")))
        ev.add("summary", f"Sperrung Uwe-Seeler-Allee: {titel}")
        ev.add("location", ort)
        ev.add("dtstart", von)
        ev.add("dtend", bis)
        ev.add("description", "Beginn: " + ", ".join(s.strftime('%H:%M') for s, _ in liste))

        # Erinnerung nur Montag (0) bis Freitag (4)
        if tag.weekday() < 5:
            zeitpunkt = datetime.combine(tag, ERINNERUNG, TZ)
            # Beginnt die Sperrung schon frueh (z. B. Nachmittagsvorstellung),
            # kommt die Erinnerung eine Stunde vor Beginn des Sperrfensters.
            zeitpunkt = min(zeitpunkt, von - timedelta(hours=1))
            alarm = Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", f"Heute Sperrung ab {von:%H:%M}: {titel}")
            alarm.add("trigger", zeitpunkt.astimezone(ZoneInfo("UTC")))
            ev.add_component(alarm)
        cal.add_component(ev)

    # --- Baustellen der Stadt ---
    # In try/except, damit ein Ausfall dieser Quelle nicht den ganzen
    # Kalender verhindert. Arena und HSV werden trotzdem gespeichert.
    try:
        for von, bis, text in baustellen():
            ev = Event()
            ev.add("uid", str(uuid.uuid5(uuid.NAMESPACE_URL, f"bau-{von}-{text[:80]}")))
            ev.add("summary", "Baustelle/Sperrung Volkspark-Umfeld")
            ev.add("dtstart", von)                       # ganztaegig
            ev.add("dtend", bis + timedelta(days=1))     # Endtag zaehlt nicht mit, daher +1
            ev.add("description", text)
            cal.add_component(ev)
    except Exception as fehler:
        print("Baustellen-Abruf fehlgeschlagen:", fehler)

    # --- Speichern ---
    out = Path("docs/volkspark.ics")
    out.parent.mkdir(exist_ok=True)   # Ordner docs anlegen, falls noch nicht da
    out.write_bytes(cal.to_ical())
    print(f"{len(cal.subcomponents)} Termine geschrieben")


if __name__ == "__main__":
    main()
