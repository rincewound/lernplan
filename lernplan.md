# Ziel
Ein Lernplan für verschiedene Personen.

- Es können Prüfungen eingegeben werden, mit geplantem Lernpensum (z.B. 10h, ab 2 Wochen im Voraus)
- Es können "Standardlern" Einheiten angeben werden  (z.B. "Französisch, jeden Tag 30 min")
- Die Nutzer können für den aktuellen Tag sehen, was sie noch tun müssen.
- Die Nutzer können abhaken, was schon getan wurde

## Umsetzung:

### Screens
#### My
Für einen Nutzer:
Aktueller Tag: 
 * Offene Lerneinheiten (mit "Done" Häkchen, macht die LE "bearbeitet"), 
 * Bearbeitete Lerneinheiten (mit "Doch nicht gemacht x", macht die LE "Offen")
Kommende Prüfungen in den nächsten 3 Wochen

#### Kalender
Kalendersicht (Liste) - tageweise.
* Tage mit Prüfungen Rot markiert (Hover Zeigt Fach)
* Click auf Tag: Tag Bearbeiten Screen

* Tage mit Ferien werden grün hinterlegt (Hover zeigt Ferienname)
* Button um Ferien anzulegen  (siehe "Ferien/Freie Zeit")

#### Tag Bearbeiten
* Zeigt Liste mit Prüfungen an diesem Tag
* Prüfungen können gelöscht werden (Rückfragemodal!)
* Neue Prüfungen hinzufügen:
    * Fach
    * Lernplandefinition:
        * Tagebasiert: N Tage vorher je X Zeigt
    * Inhalte, Freitext, optional
* Prüfungen können bearbeitet werden (gleiche Maske wie neue Prüfung)

Effekt von Prüfungen:
Prüfungen wirden via Lernplandefinition wie ein temporäres Pensum, d.h. wenn eine 
Prüfung "Französisch" mit 30min pro Tag 4 Tage vorher angelegt wurde werden an den entsprechenden Tagen 
Lerneinheiten für den "Eigentümer" der Prüfung angezeigt.

#### Tägliches Pensum
* Es kann ein Tägliches Pensum eines Fachs definiert werden (z.B. "Französisch, 30 min, jeden Tag")
* Es können mehrere Pensen für jeden Nutzer aktiv sein.
* Für jedes Pensum kann definiert werden an welchen Wochentagen es aktiv ist (z.B. Mo, Di, Mi, rest nicht)
* Für jedes Pensum kann definiert werden ob es von Ferien übersteuert wird

#### Ferien / Freie Zeit 
* Es können Ferien definiert werden. Während Ferien werden tägliche Aufgaben, die aus Pensen abgeleitet wurdne, und bei denen das Pensum das "übersteuert durch Ferien" Flag hat nicht angezeigt.
* Ferien haben einen Namen
* Achtung: Jeder Nutzer wählt selbst, ob definierte Ferien für ihn gelten.

#### Berechtigungsmodell
* Adminbenutzer
  * Anlegen neuer Nutzer
  * Kann alle Nutzer sehen
* Aufsichtsnutzer
  * Kann alle Nutzer sehen 
* Normaler Nutzer 
  * Kann nur eigene Daten sehen

Anlegen von Ferien: Alle Nutzer 
Anlegen von Lernplänen: Alle für sich selbst, Admin + Aufsicht für andere
Anlegen von Prüfungen: Alle für sich selbst, Admin + Aufsicht für andere 
Sehen der Tasks für einen Tag: Alle für sich selbst, Admin + Aufsicht für andere 

### Techstack:
HTML5 + Django + SQLite 

Ziel: Deploybarer Dockercontainer für Portainer 192.168.0.153:9443

### Sonstiges
* Verwende existierende Packages und vermeide Reimplementierungen
* 100% Coverage mit Unittests
* Typechecker verwenden
* Warnings = Error 
* Python: uv + Ruff verwenden
