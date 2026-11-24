// Das Handy-Menü funktioniert ohne JS (Popover: öffnen, Escape, Klick daneben).
// Dieses Skript ergänzt nur zwei Komfortfunktionen.
const navigation = document.getElementById('navigation');
if (navigation) {
  const closeNavigation = () => navigation.matches(':popover-open') && navigation.hidePopover();

  // Nach Klick auf einen Menüpunkt schließen
  navigation.addEventListener('click', event => {
    if (event.target.closest('a')) closeNavigation();
  });

  // Beim Wechsel auf Desktop-Breite schließen
  matchMedia('(min-width: 801px)').addEventListener('change', event => {
    if (event.matches) closeNavigation();
  });
}

// „Bewegung reduzieren“ im Betriebssystem: dann keine Animationen.
// Einmal abgefragt und überall unten genutzt.
const bewegungErlaubt = !matchMedia('(prefers-reduced-motion: reduce)').matches;

// Gemeinsamer Scroll-Takt für Ritter, Schwein und Tasse: Statt dass jede
// Figur bei jedem Scroll-Ereignis einen eigenen Frame anmeldet, gibt es
// einen Listener und höchstens einen Frame pro Bild – darin rechnen
// alle Figuren nacheinander. Beim Ändern der Fenstergröße ebenso.
const scrollFiguren = [];
let frameGeplant = false;
const alleFigurenBewegen = () => {
  frameGeplant = false;
  scrollFiguren.forEach(bewegen => bewegen());
};
const imScrollTakt = bewegen => {
  if (!scrollFiguren.length) {
    const planen = () => {
      if (frameGeplant) return;
      frameGeplant = true;
      requestAnimationFrame(alleFigurenBewegen);
    };
    addEventListener('scroll', planen, { passive: true });
    addEventListener('resize', planen);
  }
  scrollFiguren.push(bewegen);
  bewegen(); // gleich richtige Startposition
};

// Mitlaufende Kopfleiste: Sobald das große Logo im Startbild
// aus dem Bild gescrollt ist, bekommt die Kopfleiste die Klasse
// „ist-gescrollt“ (weißer Hintergrund, dunkle Schrift, Tasse sichtbar).
const kopfleiste = document.querySelector('.kopfleiste');
const startbildLogo = document.querySelector('.startbild-logo img');
// Seiten ohne Startbild (Impressum, Datenschutz) haben kein großes Logo –
// dort ist die Kopfleiste fest hell, der Beobachter entfällt.
if (kopfleiste && startbildLogo) {
  new IntersectionObserver(([eintrag]) => {
    kopfleiste.classList.toggle('ist-gescrollt', !eintrag.isIntersecting);
  }, { rootMargin: '-80px 0px 0px 0px' }).observe(startbildLogo);
}

// Sanftes Einblenden: Überschriften, Bilder und Texte gleiten beim
// Runterscrollen leicht von unten herein. Ohne JavaScript (oder bei
// „Bewegung reduzieren“ im Betriebssystem) ist einfach alles sofort da.
if (bewegungErlaubt) {
  const einblenden = document.querySelectorAll('main h2, .speise, .preisliste, .kachel, .karten-block, .espressomaschine-bild, .espressobar-kachel, .kaffeefahrrad-bild, .kaffeefahrrad-text, .adresse, .foto-text');
  const beobachter = new IntersectionObserver(eintraege => {
    eintraege.forEach(eintrag => {
      if (eintrag.isIntersecting) {
        eintrag.target.classList.add('ist-sichtbar');
        beobachter.unobserve(eintrag.target);
      }
    });
  }, { rootMargin: '0px 0px -8% 0px' });
  einblenden.forEach(element => {
    element.classList.add('blendet-ein');
    beobachter.observe(element);
  });
}

// Wackeln: Die gezeichneten Illustrationen wackeln kurz, sobald sie
// ins Bild gescrollt werden – aber nur EINMAL pro Seitenaufruf
// (auch am Handy). Bei „Bewegung reduzieren“ nicht.
if (bewegungErlaubt) {
  // „Desktop“ = breiter als 800 px (wie in style.css). Die Abfrage
  // „(hover: hover)“ war unzuverlässig, z. B. bei Laptops mit Touchscreen.
  const mitMaus = matchMedia('(min-width: 801px)').matches;
  // Desktop: Bagel und Kuchen wackeln nicht (auch nicht beim Drüberfahren). Auf der Danziger-Karte
  // bleiben Genießer, Kuchen und Suppe still (wirkt sonst zu inszeniert).
  // Handy: Alle Illustrationen wackeln.
  // Startseite (Desktop und Handy): Suppe, Genießer (nur sanft, siehe
  // .figur-geniesser in style.css) und die Passenger-Blend-Tüte wackeln
  // beim Reinscrollen. Buddha und Kiwi bleiben bewusst still.
  // Kommode: das Garderobenschloss (.schloss-figur) ebenso.
  // Kaffeefahrrad: das Rad (.fahrrad-figur) und der Becher am Formular.
  const startseite = '.speise img[src*="suppe"], .figur-geniesser img, .kaffeebohnen-zeichnung, .schloss-figur, .fahrrad-figur, .anfrage-figur';
  const illustrationen = document.querySelectorAll(mitMaus
    // Kaffeefahrrad-Karte: nur die Espressomaschine wackelt, das Rad (.fahrrad-vignette) nicht
    ? startseite + ', .karten-vignette:not([src*="geniesser"]):not([src*="kuchen"]):not([src*="suppe"]):not(.fahrrad-vignette)'
    : startseite + ', .speise img, .karten-vignette');
  const wackelBeobachter = new IntersectionObserver(eintraege => {
    eintraege.forEach(eintrag => {
      if (eintrag.isIntersecting) {
        eintrag.target.classList.add('wackelt');
        // nur einmal: danach wird die Figur nicht mehr beobachtet
        wackelBeobachter.unobserve(eintrag.target);
      }
    });
  }, { threshold: .15 }); // startet, sobald gut ein Siebtel der Figur zu sehen ist
  illustrationen.forEach((bild, nummer) => {
    // am Handy leicht versetzt, damit Bagel, Kuchen und Suppe nacheinander wackeln
    if (!mitMaus && bild.closest('.speise')) bild.style.animationDelay = nummer * 0.15 + 's';
    bild.addEventListener('animationend', () => bild.classList.remove('wackelt'));
    wackelBeobachter.observe(bild);
  });
}

// Ritter-Ritt: Der Ritter mit der Kaffeefahne reitet beim Scrollen
// über seine Bahn – je weiter man scrollt, desto weiter nach links
// (er schaut nach links, also galoppiert er auch dorthin).
// Startseite: über das Laufband (.figur-ritter in .ritter-bahn).
// Danziger Straße: unter der Überschrift (.einleitung-ritter), als Bahn
// dient die linke Spalte .einleitung-kopf.
// Bei „Bewegung reduzieren“ bleibt er einfach stehen.
if (bewegungErlaubt) {
  document.querySelectorAll('.figur-ritter, .einleitung-ritter').forEach(ritter => {
    const bahn = ritter.parentElement;
    const nachRechts = ritter.classList.contains('ritter-nach-rechts');
    const reiten = () => {
      const oben = bahn.getBoundingClientRect().top;
      // 0 = Bahn taucht unten auf, 1 = Bahn verschwindet oben
      const fortschritt = Math.min(Math.max(1 - oben / innerHeight, 0), 1);
      const strecke = bahn.offsetWidth - ritter.offsetWidth;
      // Gespiegelter Ritter (.ritter-nach-rechts) startet links und reitet
      // nach rechts. Weil CSS ihn per „scale: -1 1“ spiegelt, wirkt auch
      // die Verschiebung gespiegelt – darum hier mit Minus.
      const versatz = nachRechts ? -fortschritt * strecke : (1 - fortschritt) * strecke;
      ritter.style.transform = `translateX(${versatz}px)`;
    };
    imScrollTakt(reiten);
  });
}

// Schwein-Flug: Das Schwein schwebt beim Scrollen vom rechten Rand ins
// Foto „Wie alles anfing.“ – am Anfang steht es fast ganz rechts draußen,
// wenn das Foto die Bildschirmmitte erreicht, ist es angekommen.
// Gilt auch für das Schwein in „Komm vorbei.“ (Danziger Straße) – das
// Hereinschweben dort ist gewollt. Das Davonfliegen darunter läuft über
// CSS-Animationen, die das hier gesetzte transform nur solange überdecken.
// Bei „Bewegung reduzieren“ ist es einfach gleich da.
const schwein = document.querySelector('.figur-schwein');
const schweinFoto = schwein?.closest('section');
if (schweinFoto && bewegungErlaubt) {
  const foto = schweinFoto;
  const fliegen = () => {
    const oben = foto.getBoundingClientRect().top;
    // 0 = Foto taucht unten auf, 1 = Foto ist im oberen Drittel
    const fortschritt = Math.min(Math.max((innerHeight - oben) / (innerHeight * .7), 0), 1);
    schwein.style.transform = `translateX(${(1 - fortschritt) * 90}%)`;
  };
  imScrollTakt(fliegen);
}

// Schwein auf der Startseite („Wie alles anfing.“) und auf der Danziger
// Straße („Komm vorbei.“): wackelt beim Drüberfahren (oder Antippen) kurz
// und fliegt dann nach links oben davon. Nach 4,5 Sekunden schwebt es
// wieder zurück. Die Animation steht in style.css
// (.schwein-fliegt-davon / .schwein-kommt-zurueck).
const besuchSchwein = document.querySelector('.figur-schwein');
if (besuchSchwein && bewegungErlaubt) {
  // Timer und Beobachter für den Handy-Wink (siehe unten)
  let winkTimer, abflugTimer, winkBeobachter;
  const davonfliegen = () => {
    // Egal ob selbst getippt oder automatisch: ausstehende Wink- und
    // Abflug-Timer stoppen, sonst gäbe es später einen zweiten,
    // ungewollten Abflug.
    clearTimeout(winkTimer);
    clearTimeout(abflugTimer);
    winkBeobachter?.disconnect();
    erledigt = true; // kein automatischer Wink mehr danach
    if (besuchSchwein.classList.contains('schwein-fliegt-davon')) return;
    besuchSchwein.classList.remove('schwein-kommt-zurueck', 'schwein-wackelt');
    besuchSchwein.classList.add('schwein-fliegt-davon');
  };
  besuchSchwein.addEventListener('pointerenter', davonfliegen);
  besuchSchwein.addEventListener('click', davonfliegen);
  // Handy (Geräte ohne Maus) und schmale Fenster (unter 1188 px, dort
  // liegt das Schwein über dem Text): Ist das Schwein gut zu sehen,
  // wackelt es nach 2 Sekunden einmal als Wink. Kommt dann 6 Sekunden
  // lang niemand dran, fliegt es von selbst davon. Einmal pro Seitenaufruf.
  // Die Breite wird jedes Mal live geprüft – zieht man das Fenster
  // schmaler, gilt das sofort, ohne Neuladen.
  const automatisch = matchMedia('(hover: none), (max-width: 1187px)');
  const winkStarten = () => {
    clearTimeout(winkTimer);
    winkTimer = setTimeout(() => {
      if (!automatisch.matches || erledigt) return;
      erledigt = true;
      besuchSchwein.classList.add('schwein-wackelt');
      abflugTimer = setTimeout(davonfliegen, 6000);
      winkBeobachter.disconnect(); // ab jetzt läuft es, nur einmal
    }, 2000);
  };
  let sichtbar = false, erledigt = false;
  winkBeobachter = new IntersectionObserver(([eintrag]) => {
    sichtbar = eintrag.isIntersecting;
    if (sichtbar && automatisch.matches) winkStarten();
    else clearTimeout(winkTimer); // zu früh weggescrollt: später nochmal
  }, { threshold: .3 }); // 30 % sichtbar reicht: das große Schwein ragt teils aus dem Foto
  winkBeobachter.observe(besuchSchwein);
  // Fenster wird schmaler, während das Schwein schon zu sehen ist
  automatisch.addEventListener('change', () => {
    if (automatisch.matches && sichtbar) winkStarten();
    else clearTimeout(winkTimer);
  });

  besuchSchwein.addEventListener('animationend', e => {
    if (e.animationName !== 'schwein-davonfliegen') return;
    // weg ist es – kurz warten, dann wieder einschweben lassen
    besuchSchwein.style.visibility = 'hidden';
    setTimeout(() => {
      besuchSchwein.classList.remove('schwein-fliegt-davon');
      besuchSchwein.style.visibility = '';
      besuchSchwein.classList.add('schwein-kommt-zurueck');
    }, 4500); // 4,5 Sekunden Pause, dann kommt es von rechts zurück
  });
}

// Geschützte E-Mail-Adresse (kontakt.html): Die Adresse steht nur
// rückwärts und in zwei Teilen im HTML (data-name, data-domain).
// Erst hier im Browser wird sie umgedreht, zusammengesetzt und als
// klickbarer mailto-Link eingesetzt – einfache Spam-Bots, die nur das
// HTML lesen, finden so keine Adresse.
// Fehlen die data-Angaben, bleibt der Ersatztext („E-Mail schreiben“
// bzw. die kodierte Adresse) einfach stehen.
const umdrehen = text => [...text].reverse().join('');
document.querySelectorAll('.email-geschuetzt').forEach(feld => {
  const { name, domain } = feld.dataset;
  if (!name || !domain) return;
  const adresse = umdrehen(name) + '@' + umdrehen(domain);
  // Ist das Feld selbst schon ein Link (Fußbereich, .email-link), wird er
  // direkt ergänzt – sonst kommt ein neuer Link hinein (Kontaktseite).
  const link = feld.matches('a') ? feld : document.createElement('a');
  link.href = 'mailto:' + adresse;
  link.textContent = adresse;
  if (link !== feld) feld.replaceChildren(link);
});

// Tasse von oben (Kommode, über dem Fußbereich): Beim Scrollen schiebt
// sie sich an ihren Platz (ohne Drehung) – am Anfang etwas nach
// rechts versetzt, wenn das Foto zu drei Vierteln zu sehen ist, steht
// sie gerade da, wie frisch serviert. Bei „Bewegung reduzieren“ steht
// sie einfach still.
const tasseOben = document.querySelector('.figur-tasse-oben');
const tasseFoto = tasseOben?.closest('section');
if (tasseFoto && bewegungErlaubt) {
  const foto = tasseFoto;
  const servieren = () => {
    const oben = foto.getBoundingClientRect().top;
    const fortschritt = Math.min(Math.max((innerHeight - oben) / (innerHeight * .75), 0), 1);
    const rest = 1 - fortschritt;
    tasseOben.style.transform = `translateX(${rest * 30}%)`;
  };
  imScrollTakt(servieren);
}

// ── Ausklappmenü „Cafés“: Tastatur & Touchscreen ──────────────
// Maus: klappt per :hover auf (reines CSS).
// Tastatur: klappt per :focus-within auf; NEU: Escape klappt es wieder zu
//   und setzt den Fokus zurück auf „Cafés“.
// Touchscreen (Tablet in Desktop-Breite, kein Hover): der erste Tipp auf
//   „Cafés“ öffnet nur die Liste, erst der zweite Tipp folgt dem Link.
//   Ein Tipp daneben schließt die Liste wieder.
// aria-expanded verrät Screenreadern, ob die Liste gerade offen ist.
// (Kein aria-haspopup: Das ist für echte Menüs mit Pfeiltasten-Steuerung
// gedacht – hier ist es eine einfache Linkliste zum Aufklappen.)
document.querySelectorAll('.ausklappmenue').forEach(menue => {
  const ausloeser = menue.querySelector(':scope > a');
  if (!ausloeser) return;
  const ohneHover = matchMedia('(hover: none) and (min-width: 801px)');
  ausloeser.setAttribute('aria-expanded', 'false');

  const setzeOffen = offen => {
    menue.classList.toggle('ist-offen', offen);
    ausloeser.setAttribute('aria-expanded', String(offen));
  };

  // Öffnen/Schließen-Zustand für Screenreader mitführen
  menue.addEventListener('mouseenter', () => { menue.classList.remove('ist-zu'); ausloeser.setAttribute('aria-expanded', 'true'); });
  menue.addEventListener('mouseleave', () => { menue.classList.remove('ist-zu'); setzeOffen(false); });
  menue.addEventListener('focusin', event => {
    // Nach Escape springt der Fokus auf den Auslöser zurück – das darf
    // die Liste nicht gleich wieder öffnen. Erst wer weiter in die Liste
    // tabbt, öffnet sie erneut.
    if (event.target === ausloeser && menue.classList.contains('ist-zu')) return;
    menue.classList.remove('ist-zu');
    ausloeser.setAttribute('aria-expanded', 'true');
  });
  menue.addEventListener('focusout', event => {
    if (!menue.contains(event.relatedTarget)) { menue.classList.remove('ist-zu'); setzeOffen(false); }
  });

  // Escape: Liste zu, Fokus zurück auf den Auslöser
  menue.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    menue.classList.add('ist-zu');
    setzeOffen(false);
    ausloeser.focus();
  });

  // Touch: erster Tipp öffnet nur
  ausloeser.addEventListener('click', event => {
    if (!ohneHover.matches || menue.classList.contains('ist-offen')) return;
    event.preventDefault();
    event.stopPropagation();
    setzeOffen(true);
  });
  document.addEventListener('click', event => {
    if (!menue.contains(event.target)) setzeOffen(false);
  });
});

// Startbild: Klasse „geladen“ setzen, sobald das Foto da ist –
// dann blendet der Kopfbereich ein (siehe style.css „Startbild: erst hell“).
// Ist das Foto schon im Browser-Speicher, passiert das sofort.
const startbild = document.querySelector('.startbild');
const startbildFoto = document.querySelector('.startbild-foto');
if (startbild && startbildFoto) {
  const zeigen = () => startbild.classList.add('geladen');
  if (startbildFoto.complete) zeigen();
  else {
    startbildFoto.addEventListener('load', zeigen);
    startbildFoto.addEventListener('error', zeigen);
  }
}
