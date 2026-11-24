#!/usr/bin/env python3
# =====================================================================
#  LORCH & SÖHNE – INHALTE AUS inhalte.yml IN DIE HTML-SEITEN SCHREIBEN
# =====================================================================
#
#  Aufruf:   python3 aktualisieren.py            → schreibt die Änderungen
#            python3 aktualisieren.py --pruefen  → zeigt nur, was sich
#                                                  ändern würde
#
#  Ablauf:
#   1. inhalte.yml lesen und PRÜFEN (fehlende Angaben, falsches Format).
#      Bei einem Fehler bricht das Skript ab und ändert NICHTS.
#   2. In jeder Seite nur die markierten Stellen ersetzen:
#
#      a) Einzelne Werte:   <!--i:danziger.adresse.strasse-->…<!--/i-->
#         (auch die Absätze unter „texte“; Zeilenumbrüche werden
#          zu Leerzeichen, damit ein Absatz ein Absatz bleibt)
#      b) Ganze Blöcke:     <!-- INHALT danziger.oeffnungszeiten kurz ANFANG -->
#                           …
#                           <!-- INHALT ENDE -->
#      c) Route-Links:      <a … data-route="danziger" href="…">
#      d) E-Mail:           data-name / data-domain (rückwärts) und der
#                           verschlüsselte Ersatztext in Impressum/Datenschutz
#      e) Google-Angaben:   JSON-LD auf der Startseite (Adresse, Zeiten)
#      f) Speisekarte:      <!-- INHALT danziger.karte.kaffee liste ANFANG -->
#                           (Danziger-Seite) bzw. „tabelle“ (Startseite)
#      g) Pott Kaffee in der Google-Beschreibung der Kommode-Seite
#
#   Alles außerhalb der Markierungen bleibt unberührt.
#
#  Benötigt: Python 3 und PyYAML (pip3 install pyyaml)
# =====================================================================

import html
import re
import sys
import urllib.parse
from pathlib import Path

import yaml

ORDNER = Path(__file__).resolve().parent
SEITEN = [
    "index.html", "cafe-danziger-strasse.html", "cafe-kommode.html",
    "catering.html", "kontakt.html", "impressum.html", "datenschutz.html",
    "kaffeefahrrad-mieten.html",
]

# Name, unter dem Google Maps den Ort findet (vor der Adresse)
ROUTE_NAME = {"danziger": "", "kommode": "Lorch & Söhne Kommode, "}
# Startseite: JSON-LD-Eintrag je Ort (erkannt an der Seiten-URL)
JSONLD_URL = {
    "danziger": "https://lorchundsoehne.de/cafe-danziger-strasse.html",
    "kommode": "https://lorchundsoehne.de/cafe-kommode.html",
}

TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
TAGE_EN = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

fehler = []


# ---------------------------------------------------------------------
#  1. LESEN UND PRÜFEN
# ---------------------------------------------------------------------
def text(wert, wo):
    """Wert als Text holen; fehlt er, wird ein Fehler notiert."""
    if wert is None or str(wert).strip() == "":
        fehler.append(f"Angabe fehlt: {wo}")
        return ""
    return str(wert).strip()


def holen(daten, schluessel):
    """'danziger.adresse.strasse' → Wert aus der YML."""
    wert = daten
    for teil in schluessel.split("."):
        if not isinstance(wert, dict) or teil not in wert:
            fehler.append(f"Angabe fehlt: {schluessel}")
            return ""
        wert = wert[teil]
    return text(wert, schluessel)


def tage_bereich(tage, wo):
    """'Montag–Freitag' → Liste der Tage (für Google)."""
    teile = [t.strip() for t in re.split(r"[–-]", tage)]
    try:
        idx = [TAGE.index(t) for t in teile]
    except ValueError:
        fehler.append(f"{wo}: Tage „{tage}“ nicht erkannt (z. B. Montag–Freitag oder Samstag)")
        return []
    if len(idx) == 1:
        return [idx[0]]
    if len(idx) == 2 and idx[0] <= idx[1]:
        return list(range(idx[0], idx[1] + 1))
    fehler.append(f"{wo}: Tage „{tage}“ nicht erkannt")
    return []


RUBRIKEN = ["kaffee", "andere_getraenke", "saefte", "fruehstueck", "bagels", "kuchen", "suppen"]


def preis_pruefen(wert, wo, darf_fehlen=False):
    """'3,7' / '3,70' / 4 → '3,70'.  '–' → None (gibt es nicht)."""
    if wert is None or str(wert).strip() == "":
        fehler.append(f"Preis fehlt: {wo}")
        return ""
    s = str(wert).strip().replace("€", "").strip().replace(".", ",")
    if s in ("–", "-", "—"):
        if darf_fehlen:
            return None
        fehler.append(f"{wo}: „–“ geht nur bei Kaffee (einfach/doppelt)")
        return ""
    if not re.fullmatch(r"\d{1,3}(,\d{1,2})?", s):
        fehler.append(f"{wo}: Preis „{wert}“ bitte so schreiben: 3,70")
        return ""
    euro, _, cent = s.partition(",")
    return f"{euro},{cent.ljust(2, '0')}"


def karte_pruefen(karte):
    """Speisekarte prüfen; Ergebnis: Rubrik → Liste von Einträgen."""
    ergebnis = {}
    if not isinstance(karte, dict):
        fehler.append("danziger.karte fehlt")
        return ergebnis
    for rubrik in RUBRIKEN:
        wo = f"danziger.karte.{rubrik}"
        block = karte.get(rubrik)
        if not isinstance(block, dict):
            fehler.append(f"Angabe fehlt: {wo}")
            continue
        liste = block.get("eintraege")
        if rubrik == "kuchen" and liste is None:
            continue                      # Kuchen hat nur einen Satz
        if not isinstance(liste, list) or not liste:
            fehler.append(f"{wo}: keine Einträge gefunden (Einrückung prüfen?)")
            continue
        eintraege = []
        for n, e in enumerate(liste, 1):
            stelle = f"{wo}, Eintrag {n}"
            if not isinstance(e, dict):
                fehler.append(f"{stelle}: braucht „name“ und „preis“ (Einrückung prüfen?)")
                continue
            name = text(e.get("name"), f"{stelle}, name")
            stelle = f"{wo}, „{name}“"
            if rubrik == "kaffee":
                einfach = preis_pruefen(e.get("einfach"), f"{stelle}, einfach", True)
                doppelt = preis_pruefen(e.get("doppelt"), f"{stelle}, doppelt", True)
                eintraege.append({"name": name, "einfach": einfach, "doppelt": doppelt})
            else:
                preis = preis_pruefen(e.get("preis"), f"{stelle}, preis")
                zutaten = str(e.get("zutaten") or "").strip()
                eintraege.append({"name": name, "preis": preis, "zutaten": zutaten})
        ergebnis[rubrik] = eintraege
    return ergebnis


def zeiten_pruefen(liste, wo):
    """Öffnungszeiten prüfen und in einheitliche Form bringen."""
    if not isinstance(liste, list) or not liste:
        fehler.append(f"{wo}: keine Öffnungszeiten gefunden")
        return []
    ergebnis = []
    for n, z in enumerate(liste, 1):
        if not isinstance(z, dict):
            fehler.append(f"{wo}, Zeile {n}: braucht „tage“ und „zeit“")
            continue
        tage = text(z.get("tage"), f"{wo}, Zeile {n}, tage").replace("-", "–")
        zeit = text(z.get("zeit"), f"{wo}, Zeile {n}, zeit").replace("-", "–")
        tage_bereich(tage, f"{wo}, Zeile {n}")
        if zeit != "geschlossen" and not re.fullmatch(r"\d\d:\d\d–\d\d:\d\d Uhr", zeit):
            fehler.append(f"{wo}, Zeile {n}: Zeit „{zeit}“ bitte so schreiben: 08:00–17:00 Uhr (oder: geschlossen)")
        ergebnis.append({"tage": tage, "zeit": zeit})
    return ergebnis


# ---------------------------------------------------------------------
#  2. BAUSTEINE ERZEUGEN
# ---------------------------------------------------------------------
def kurz(tage):
    """'Montag–Freitag' → 'Mo–Fr' (für die Startseite)."""
    for t in TAGE:
        tage = tage.replace(t, t[:2])
    return tage


def zeiten_html(zeiten, form, einrueckung):
    zeilen = []
    for z in zeiten:
        tage = kurz(z["tage"]) if form == "kurz" else z["tage"]
        zeilen += [
            f"{einrueckung}<div>",
            f"{einrueckung}  <dt>{html.escape(tage)}</dt>",
            f"{einrueckung}  <dd>{html.escape(z['zeit'])}</dd>",
            f"{einrueckung}</div>",
        ]
    return "\n".join(zeilen)


def zeiten_jsonld(zeiten, einrueckung):
    eintraege = []
    for z in zeiten:
        if z["zeit"] == "geschlossen":
            continue
        tage = ",".join(f'"{TAGE_EN[i]}"' for i in tage_bereich(z["tage"], ""))
        auf, zu = z["zeit"].replace(" Uhr", "").split("–")
        eintraege.append(
            f'{einrueckung}{{ "@type": "OpeningHoursSpecification", "dayOfWeek": [{tage}], '
            f'"opens": "{auf}", "closes": "{zu}" }}'
        )
    return ",\n".join(eintraege)


def karte_liste_html(rubrik, eintraege, einr):
    """Danziger-Seite: eine <li> je Eintrag."""
    e = lambda s: html.escape(s, quote=False)
    zeilen = []
    for x in eintraege:
        if rubrik == "kaffee":
            teile = []
            for art, klasse in (("einfach", "preis"), ("doppelt", "preis preis-doppelt")):
                if x[art] is None:
                    inhalt = f'<span aria-hidden="true">—</span><span class="sr-only">{art}: gibt es nicht</span>'
                else:
                    inhalt = f'<span class="sr-only">{art}: </span>{x[art]} €'
                teile.append(f'<span class="{klasse}">{inhalt}</span>')
            zeilen.append(f'{einr}<li><span class="gericht">{e(x["name"])}</span>{"".join(teile)}</li>')
        else:
            zutaten = f'<span class="zutaten">{e(x["zutaten"])}</span>' if x["zutaten"] else ""
            zeilen.append(f'{einr}<li><span class="gericht">{e(x["name"])}</span>'
                          f'<span class="preis">{x["preis"]} €</span>{zutaten}</li>')
    return "\n".join(zeilen)


def karte_tabelle_html(eintraege, einr):
    """Startseite: Kaffee-Preistabelle."""
    zeilen = []
    for x in eintraege:
        zeilen += [f"{einr}<tr>", f'{einr}  <th scope="row">{html.escape(x["name"], quote=False)}</th>']
        for art in ("einfach", "doppelt"):
            zeilen.append(f"{einr}  <td>{'—' if x[art] is None else x[art] + ' €'}</td>")
        zeilen.append(f"{einr}</tr>")
    return "\n".join(zeilen)


def email_entities(adresse):
    return "".join(f"&#{ord(c)};" for c in adresse)


# ---------------------------------------------------------------------
#  3. SEITEN BEARBEITEN
# ---------------------------------------------------------------------
def seite_bearbeiten(inhalt, daten, zeiten, karte, datei):
    # a) Einzelne Werte
    inhalt = re.sub(
        r"<!--i:([\w.]+)-->.*?<!--/i-->",
        lambda m: f"<!--i:{m[1]}-->{html.escape(' '.join(holen(daten, m[1]).split()), quote=False)}<!--/i-->",
        inhalt, flags=re.S,
    )

    # b) Blöcke: Öffnungszeiten (kurz|lang) und Speisekarte (liste|tabelle)
    def block(m):
        pfad, form, einr = m["pfad"], m["form"], m["einr"]
        teile = pfad.split(".")
        if len(teile) == 2 and teile[1] == "oeffnungszeiten" and teile[0] in zeiten and form in ("kurz", "lang"):
            neu = zeiten_html(zeiten[teile[0]], form, einr)
        elif len(teile) == 3 and teile[:2] == ["danziger", "karte"] and teile[2] in karte:
            if form == "liste":
                neu = karte_liste_html(teile[2], karte[teile[2]], einr)
            elif form == "tabelle" and teile[2] == "kaffee":
                neu = karte_tabelle_html(karte["kaffee"], einr)
            else:
                fehler.append(f"{datei}: unbekannte Form „{form}“ bei {pfad}")
                return m[0]
        else:
            fehler.append(f"{datei}: unbekannter Block {pfad} {form}")
            return m[0]
        return (f"{einr}<!-- INHALT {pfad} {form} ANFANG -->\n{neu}\n"
                f"{einr}<!-- INHALT ENDE -->")
    inhalt = re.sub(
        r"(?P<einr>[ \t]*)<!-- INHALT (?P<pfad>[\w.]+) (?P<form>\w+) ANFANG -->.*?<!-- INHALT ENDE -->",
        block, inhalt, flags=re.S,
    )

    # c) Route-Links zu Google Maps
    def route(m):
        ort = m[1]
        ziel = (ROUTE_NAME.get(ort, "") + holen(daten, f"{ort}.adresse.strasse")
                + ", " + holen(daten, f"{ort}.adresse.plz_ort"))
        url = "https://www.google.com/maps/dir/?api=1&amp;destination=" + urllib.parse.quote_plus(ziel)
        return f'data-route="{ort}" href="{url}"'
    inhalt = re.sub(r'data-route="(\w+)" href="[^"]*"', route, inhalt)

    # d) E-Mail (rückwärts gespeichert gegen Spam)
    email = daten["kontakt"]["email"]
    name, domain = email.split("@")
    inhalt = re.sub(
        r'data-name="[^"]*" data-domain="[^"]*">(&#[^<]*)?',
        lambda m: f'data-name="{name[::-1]}" data-domain="{domain[::-1]}">'
                  + (email_entities(email) if m[1] else ""),
        inhalt,
    )

    # e) Google-Angaben (JSON-LD) – nur auf der Startseite
    for ort, url in JSONLD_URL.items():
        start = inhalt.find(f'"url": "{url}"')
        if start < 0:
            continue
        ende = inhalt.find("]\n", inhalt.find('"openingHoursSpecification"', start))
        abschnitt = inhalt[start:ende]
        strasse = holen(daten, f"{ort}.adresse.strasse")
        gebaeude = daten[ort]["adresse"].get("gebaeude")
        if gebaeude:
            strasse += ", " + str(gebaeude)
        plz = holen(daten, f"{ort}.adresse.plz_ort").split()[0]
        abschnitt = re.sub(r'"streetAddress": "[^"]*"', f'"streetAddress": "{strasse}"', abschnitt)
        abschnitt = re.sub(r'"postalCode": "[^"]*"', f'"postalCode": "{plz}"', abschnitt)
        abschnitt = re.sub(
            r'("openingHoursSpecification": \[\n)(.*?)(\n *)$',
            lambda m: m[1] + zeiten_jsonld(zeiten[ort], " " * 10) + m[3],
            abschnitt, flags=re.S,
        )
        inhalt = inhalt[:start] + abschnitt + inhalt[ende:]

    # g) Pott-Kaffee-Preis in der Google-Beschreibung (meta description)
    inhalt = re.sub(
        r"(Pott Kaffee für )[\d,]+( €)",
        lambda m: m[1] + preis_pruefen(daten["kommode"].get("pott_kaffee_preis"), "kommode.pott_kaffee_preis") + m[2],
        inhalt,
    )

    return inhalt


# ---------------------------------------------------------------------
#  HAUPTPROGRAMM
# ---------------------------------------------------------------------
def main():
    nur_pruefen = "--pruefen" in sys.argv

    try:
        daten = yaml.safe_load((ORDNER / "inhalte.yml").read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        zeile = getattr(getattr(e, "problem_mark", None), "line", None)
        wo = f" (ungefähr Zeile {zeile + 1})" if zeile is not None else ""
        print(f"FEHLER: inhalte.yml lässt sich nicht lesen{wo}.")
        print("Meist ist die Einrückung verrutscht oder ein Doppelpunkt fehlt.")
        sys.exit(1)

    email = holen(daten, "kontakt.email")
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", email):
        fehler.append(f"E-Mail-Adresse „{email}“ sieht nicht richtig aus")

    zeiten = {ort: zeiten_pruefen(daten.get(ort, {}).get("oeffnungszeiten"), f"{ort}.oeffnungszeiten")
              for ort in ("danziger", "kommode")}

    karte = karte_pruefen(daten.get("danziger", {}).get("karte"))
    preis_pruefen(daten.get("kommode", {}).get("pott_kaffee_preis"), "kommode.pott_kaffee_preis")
    preis_pruefen((daten.get("kommode", {}).get("schloss") or {}).get("pfand"), "kommode.schloss.pfand")

    # Erst wenn die Angaben stimmen, werden die Seiten angefasst
    if not fehler:
        neu = seiten_erzeugen(daten, zeiten, karte)
    melden_und_schreiben(neu if not fehler else {}, nur_pruefen)


def seiten_erzeugen(daten, zeiten, karte):
    neu = {}
    for datei in SEITEN:
        pfad = ORDNER / datei
        alt = pfad.read_text(encoding="utf-8")
        ergebnis = seite_bearbeiten(alt, daten, zeiten, karte, datei)
        if ergebnis != alt:
            neu[pfad] = ergebnis
    return neu


def melden_und_schreiben(neu, nur_pruefen):
    if fehler:
        print("FEHLER – es wurde nichts geändert:")
        for f in dict.fromkeys(fehler):
            print("  •", f)
        sys.exit(1)

    if not neu:
        print("Alles aktuell – keine Änderungen.")
        return
    for pfad, inhalt in neu.items():
        print(("Würde ändern: " if nur_pruefen else "Geändert: ") + pfad.name)
        if not nur_pruefen:
            pfad.write_text(inhalt, encoding="utf-8")


if __name__ == "__main__":
    main()
