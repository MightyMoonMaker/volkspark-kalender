# Volkspark-Kalender

## Ziel
Ein abonnierbarer Kalender (docs/volkspark.ics) mit allen Veranstaltungen in
Barclays Arena und Volksparkstadion in Hamburg. Bei jeder Veranstaltung ist die
Uwe-Seeler-Allee gesperrt, Navis zeigen das oft nicht an. Zielgruppe: Pendler,
die zwischen den Stadien durchfahren.

## Aufbau
- build_calendar.py erzeugt die ICS-Datei.
- .github/workflows/update.yml fuehrt das Skript taeglich aus.
- Veroeffentlichung ueber GitHub Pages aus dem Ordner /docs.

## Quellen
- Barclays Arena: PDF-Terminliste https://www.barclays-arena.de/events-tickets/pdf/
- HSV: iCal-Feed von fussball-spielplan.de, nur Heimspiele
- Stadt Hamburg: WFS "Baustellen Hamburg" (geodienste.hamburg.de),
  gefiltert auf Uwe-Seeler-Allee, Sylvesterallee, Stadionstrasse

## Fachliche Regeln
- Termin: 3 h vor Beginn bis 1 h nach geschaetztem Ende (Eventdauer 3 h).
- Mehrere Vorstellungen am selben Tag und Ort = ein Termin.
- Erinnerung nur Mo-Fr um 14:30 Uhr, frueher falls die Sperrung frueher beginnt.
- Wochenende: Termin ja, Erinnerung nein.
- Baustellen: ganztaegige Termine ohne Erinnerung.
- Faellt eine Quelle aus, laufen die anderen weiter.
- Zeitzone immer Europe/Berlin.

## Bekannte Punkte
- Google Kalender ignoriert Erinnerungen in abonnierten Kalendern.
  Loesung fuer die 14:30-Erinnerung ist noch offen.
- Formate von HSV-Feed und Baustellen-Dienst beim ersten Lauf pruefen.

## Datenschutz
- Dieses Repository ist oeffentlich. Keine Namen, Arbeitgeber, Adressen,
  Wohnorte oder persoenlichen Routen in Code, Commits oder Doku aufnehmen.

## Arbeitsweise
- Der Nutzer moechte moeglichst wenig selbst tun. Arbeite selbststaendig.
- Frag vor wichtigen Entscheidungen: neue Quellen, geaenderte Regeln,
  Kosten, alles was Abonnenten sehen.
- Kleine Fixes und Aufraeumen ohne Rueckfrage erledigen.
- Vor groesseren Aenderungen kurz den Plan beschreiben.
- Erklaerungen auf Deutsch, kurz und ohne Fachchinesisch.
- Code einfach halten, keine unnoetigen Abhaengigkeiten.
- Nach Aenderungen das Skript lokal ausfuehren und die Anzahl Termine pruefen.
