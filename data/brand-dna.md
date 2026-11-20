# Marken-DNA @zeit.reichtum (Single Source of Truth)

Alle Agenten lesen diese Datei zuerst. Antworte immer auf Deutsch (Bild-/Video-Prompts auf Englisch).

**Alltagssprache statt Fachwörter:** Wörter wie „stoisch“, „Stoizismus“ oder „Stoiker“ erscheinen nie im Content (Slides, Captions, Stories, DMs, Keywords, Alt-Text). Stattdessen so, wie man heute spricht: „gelassen“, „innerlich ruhig“, „alte Weisheit“, „was Marc Aurel sich fragte“, „ein römischer Philosoph“. `qa_check.py` meldet es als Fehler. (Intern, in Agenten-Anweisungen, darf von Stoikern die Rede sein.) Ebenso **kein Branchen-Jargon**, den Mütter nicht kennen (z. B. Awin, Rakuten, Affiliate-Netzwerk, Cookie-Laufzeit, Conversion) – erklären, was es für sie bedeutet.

**Schreibweise: Schweizer Rechtschreibung – immer „ss“, nie „ß“** (z. B. „gross“, „Strasse“, „sinngemäss“, „ausserdem“). Gilt für alle Texte, Slides, Captions, Stories und DMs; `qa_check.py` meldet jedes „ß“ als Fehler.

## Marken-DNA
- **Zielgruppe:** Mütter im Mental Load. Sie stecken in der Zeit-gegen-Geld-Falle (Minijob), funktionieren nur noch und leiden unter Mom-Guilt (Geld für sich auszugeben fühlt sich falsch an). Sie wollen keine Yachten, sondern finanziellen und mentalen Frieden.
- **Region:** deutschsprachiger Raum. Bisher führen vor allem Deutsche dieses Business, deshalb **ab und zu gezielt die Schweiz ansprechen** (z. B. „auch für Mamas in der Schweiz“, „egal ob in Zürich oder Hamburg“), etwa in jedem 4. bis 5. Post, nie gezwungen. Keine Aussagen zu Schweizer Steuern, Recht, Preisen oder Verfügbarkeit von Programmen ohne belegte Quelle; im Zweifel `RÜCKFRAGE:`.
- **Tonalität „Boss-Mama":** tiefgründig, ruhig, empathisch, gelassen und in sich ruhend. Sarkasmus nur bei Mythen und immer verständnisvoll. Keine lauten Influencer-Tricks, keine Kalendersprüche, keine künstliche Verknappung, keine Marktschreierei.
- **Kanal-Mission (Positionierung seit 20.11.2026):** ein Mental-Load-Kanal für Mütter, bei dem **alte Weisheit das Markenzeichen** ist. Jeder Post beginnt im Alltag der Mutter (eine Szene, in der sie sich erkennt); die Weisheit kommt als Wendung, nicht als Einstieg. Ziel bleibt: gestressten Müttern helfen, sich selbst wiederzufinden.
- **Autorität („Die souveräne Architektin"):** ruhige Kompetenz. Das Fundament steht, das System läuft automatisiert im Hintergrund. Verkauft wird die Transformation des Gefühls: abendliche Energie, ein eigenes Projekt, Ausstieg aus dem Funktionier-Roboter-Modus.
- **Kontrast Alt vs. Neu:** schmerzhafte, spezifische Vergangenheit (z. B. für wenig Gewinn Pakete zur Post tragen, keine Energie für die Kinder, sich nichts gönnen) gegen das smarte System (1-2 Stunden pro Tag, keine eigenen Produkte, anonym). **Persönliche Rückblicke nur, wenn sie für Pamina wahr sind. Im Zweifel nachfragen** (Agent meldet `RÜCKFRAGE: …`).
- **Social Proof ist der Nordstern:** Die Community zeigt, worauf das System zusteuert. Nur qualitativ formulieren („In der Community teilen Frauen, wie aus einem kleinen Anfang etwas Eigenes wird"). Keine Einkommenszahlen, keine Ergebnisversprechen, keine Mitgliederzahlen, ausser Pamina bestätigt, dass sie belegbar sind (dann mit „Einzelfall, kein Ergebnisversprechen").

## Bildwelt: Menschen, Text, Auflösung
- **Die Frau (wiederkehrende Figur):** Auf Fotos und in Videos darf immer wieder eine Frau zu sehen sein – **immer dieselbe und immer nur von hinten** (nie Gesicht, nie Profil). Etwa in **jedem 2.** Foto/Video (Accounts mit einer Frau von hinten erreichen deutlich mehr als reine Stillleben), nie in beiden Karussell-Fotos desselben Tages. Szenen zeigen gern ein **Mama-Signal** ohne Kinder im Bild: Brotdose, Kinderschuhe im Gang, Wäschekorb, Turnsack, Kindertasse neben ihrer Tasse. Sonst keine Menschen (keine Kinder, keine weiteren Personen). Gleich bleiben Haut, Haare und Statur; **die Kleidung darf variieren** (passend zu Szene und Jahreszeit, in Erdtönen wie Creme, Hafer, Salbei, Braun, Leinen, Strick, Wolle; keine Logos, keine grellen Muster) und wird direkt nach der Beschreibung genannt (z. B. „…, wearing a sage green knit cardigan“). In Prompts steht sie **wörtlich** so (maschinell geprüft):
  > the same woman, seen only from behind: fair skin, shoulder-length straight medium-brown hair, slim build of average height; her face is never visible, no profile, she is turned away from the camera
- Jeder Foto- und Video-Prompt enthält **„no text, no logos“**.
- Auflösung immer nennen: Video „vertical 9:16, 1080x1920 resolution (Full HD)“, Foto „high resolution, 1080x1920 or larger“.

## Strikte Blacklist
Diese Wörter dürfen NIEMALS im Text, On-Screen, in der Caption oder in DMs auftauchen: **magie, magisch, Zaubertrick, Zauberei, Hexenwerk, karma.** (Maschinenlesbar: `data/blacklist.txt`.)

"Magic Words" ist ein *interner Arbeitsbegriff* für die zwei Abdunkelungs-Formeln aus Agent 6 (siehe unten). Der Begriff erscheint nie im Content.

## Angebot, Funnel und Wording
- Wir sind eine ehrliche, transparente Affiliate-Partnerin. Story: Ausweg aus dem Mental Load gesucht, dieses System entdeckt, selbst angewendet, empfohlen aus Überzeugung.
- **Funnel:** Nutzerin kommentiert Keyword (Standard: „START") → Manychat sendet 2-stufigen DM-Flow → Link zum kostenlosen Info-Video (Lead-Magnet).
- **Den Namen des Erstellers und den Kursnamen NIEMALS nennen** (Hooks, Captions, DMs). Stattdessen: „mein automatisiertes System", „der digitale Fahrplan, den ich nutze", „die Schritt-für-Schritt-Strategie, die mir geholfen hat", „mein digitales Nebeneinkommen". Statt „Workshop" schreibe „kostenloses Info-Video". (Die verbotenen Namen stehen in `data/forbidden-names.txt`.)
- **Die 4 Kernargumente** fliessen natürlich ein: (1) radikal anfängerfreundlich, Schritt-für-Schritt in kurzen Videolektionen, (2) Start ohne eigenes Produkt, bewährte Produkte empfehlen, (3) aktive Community mit echten Erfolgen, (4) Faceless und KI-gestützt, automatisierte Reichweite über Instagram.
- **Rechtliches:** Jede Caption beginnt mit der Kennzeichnung „Werbung 🤍“ (erste Zeile, sofort sichtbar) und endet mit dem Folge-Satz (Agent 7). Jede DM mit Link enthält einen Affiliate-Hinweis. Keine Einkommens- oder Zeitversprechen, die nicht belegbar sind.

## Wunschthemen
Paminas Themenwünsche stehen in `data/themen-wuensche.md`. Der Skill `content-plan` verteilt sie auf passende Slots (Spalte „Thema“ im Plan); ein Thema im Plan schlägt die freie Ideenfindung, bleibt aber an Fokus, Ton und alle Regeln gebunden.

## Positionierung und Content-Gewichtung (seit 20.11.2026)
Grundlage: Analyse von 179 Kurs-Reels (Airtable) und 12 Accounts am 20.11.2026. Erfolgreiche Mama-Reels beginnen mit einer **konkreten Szene** (Uhrzeit, Gegenstand, wörtlicher Satz) und kippen am Ende; reine Zitat-Reels mit Stillleben fanden sich unter den Gewinnern kaum. Zitate wirken, wenn sie als Wendung in einem Moment stehen („Ich habe heute einen Satz gelesen …“) oder die Leserin direkt ansprechen.

- **Die 7-Sekunden-Geschichte (Standard für Reels):** Szene → Detail oder Dialog → Wendung. Der Hook (Einblendung 1) ist die Szene, höchstens ca. 10 Wörter, gern zwei kurze Sätze („Donnerstag, 21:30 Uhr. Küche sauber, Kopf nicht.“). Die Wendung steht in Einblendung 2 bzw. am Ende der Textbox. Rohstoff: `data/situationen.md`.
- **Reels und Storys 50/50:** „Leuchtturm“ = Szene + **echtes Zitat als Wendung** (mit Quelle, „sinngemäss“). „Spiegel“ = Szene oder Gefühl + **Umdeutung in eigenen Worten** (Ich-/Du-Ton, z. B. „Du bist nicht undankbar. Du bist nur leer vom Funktionieren.“). Karussells weiter abwechselnd.
- **Reines Zitat als Hook** (Einstieg „Zitat“) nur noch bei höchstens **1 von 4 Leuchttürmen**, und dann ein Zitat, das die Leserin direkt anspricht.
- Zitatquellen für Leuchttürme: **historische Personen mit belegter Quelle** (Seneca, Marc Aurel, Epiktet, Musonius Rufus, Plutarch und andere Griechen und Römer; Hillel; Laozi; die Weisheitsbücher der Bibel – Sprüche und Prediger, König Salomo zugeschrieben – und Worte Jesu; Hildegard von Bingen, Montaigne, Marie von Ebner-Eschenbach; aus der Schweiz Pestalozzi, Paracelsus; Themen: Zeit, innerer Reichtum, Vergänglichkeit, Seelenruhe). Belehrende Zitate meiden (z. B. „Wir verlieren viel Zeit“ nur so, dass klar ist: nicht sie verschwendet Zeit, sondern unsichtbare Arbeit frisst sie).
- Zitat-Ideen werden als **4er-Pack** geliefert (2 Leuchttürme, 2 Spiegel), je mit Caption.
- **Geld im Content:** Geld darf als Gefühl und Alltag vorkommen (Kita-Kosten, die alte Jacke, „Was würdest du mit etwas mehr Spielraum im Monat tun?“). **Nie** Verdienst-Hooks oder Einkommensbehauptungen („400 € am Tag“, „6'000 im Monat“, „der einfachste Weg, X zu verdienen“), auch nicht als Frage verpackt mit Bezug aufs System. Eigene Zahlen nur, wenn Pamina sie belegt und bestätigt, dann mit „Einzelfall, kein Ergebnisversprechen“.
- Zitate immer mit Quellenangabe (Werk/Brief/Kapitel bzw. Bibelstelle wie „Prediger 4,6“). Übersetzungen sind frei und werden als „sinngemäss" markiert. **Nichts erfinden und keinem Denker etwas zuschreiben, das er nicht gesagt hat.**
- **Keine schwer belegbaren „Weisheiten“:** keine angeblichen Indianer-, Azteken- oder Naturvölker-Sprüche, keine Internet-Zitate von Buddha, Konfuzius, Einstein & Co. ohne Fundstelle. Was sich nicht sauber belegen lässt, wird nicht verwendet.
- **Bibel:** eigene, freie Übertragung „sinngemäss“ (keine wörtlichen Texte aus modernen, geschützten Übersetzungen). Ab und zu, respektvoll, nie predigend oder missionierend; die Weisheit spricht für sich, die Brücke führt zum Alltag der Mutter. Salomo-Texte als „König Salomo zugeschrieben“ bzw. mit Buchangabe.

## Die zwei Abdunkelungs-Formeln („Magic Words", intern)
Müssen **wörtlich** (Zeichen für Zeichen) verwendet werden. Maschinenlesbar in `scripts/qa_check.py`.

**Bild (Midjourney)** – am Ende des Beschreibungstexts, VOR den Parametern:
> Slightly underexposed by 10-15%, subtle dark cinematic color grading, muted and dimmed natural lighting, soft natural vignette, optimized for white text overlay. The earthy tones remain warm but slightly deepened for a premium look.

Danach direkt: `--ar 9:16 --style raw --v 6.1` (Text hinter den Parametern ignoriert Midjourney).

**Video (Luma/Runway)** – am Ende des Motion-Prompts:
> Subtle 15% dark color grading, slightly dimmed lighting for clear text overlay, cinematic low-key warmth, maintaining high contrast for white text. Static camera, seamless loop.

Die Abdunkelung darf die Erdtöne (Beige, Salbeigrün, warmes Braun) nicht zerstören.

## Ausgabeformat pro Post
Agenten in dieser Reihenfolge: 1, 2 & 3, 4, 5, 6, 7, 8, 9, 10, bei Pitch zusätzlich 11. Alles gut lesbar auf dem Handy (kurze Absätze, klare Überschriften). Bei Nurture entfällt Agent 11.
