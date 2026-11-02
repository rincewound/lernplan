import random

SENTENCES = (
    "Jeder kleine Schritt bringt dich deinem Ziel näher.",
    "Dein Wissen wächst mit jeder Frage, die du stellst.",
    "Heute ist ein guter Tag, etwas Neues zu entdecken.",
    "Du musst nicht alles können, um mutig anzufangen.",
    "Aus kleinen Lerneinheiten werden große Fortschritte.",
    "Dein Einsatz heute ist die Stärke von morgen.",
    "Eine neue Vokabel öffnet eine weitere Tür.",
    "Auch ein schwieriger Weg beginnt mit einem ersten Schritt.",
    "Fehler sind Wegweiser auf deiner Reise zum Wissen.",
    "Bleib neugierig, denn hinter jeder Frage wartet eine Entdeckung.",
    "Du lernst in deinem Tempo, und jeder Fortschritt zählt.",
    "Ein klarer Gedanke ist mehr wert als hastiges Lernen.",
    "Mit jeder Wiederholung wird dein Wissen ein wenig sicherer.",
    "Trau dich an die nächste Aufgabe, Schritt für Schritt.",
    "Deine Ausdauer macht aus Herausforderungen Möglichkeiten.",
    "Du darfst stolz auf das sein, was du schon geschafft hast.",
    "Eine Pause schenkt deinem nächsten Gedanken neue Kraft.",
    "Wissen ist ein Schatz, den du mit jedem Lerntag erweiterst.",
    "Auch fünf konzentrierte Minuten können etwas bewegen.",
    "Dein nächstes Aha-Erlebnis wartet vielleicht schon auf dich.",
    "Du brauchst keinen perfekten Start, sondern einen ersten Versuch.",
    "Was heute schwierig ist, kann morgen vertraut sein.",
    "Jede gelöste Aufgabe stärkt dein Vertrauen in dich selbst.",
    "Deine Neugier ist der Kompass auf deinem Lernweg.",
    "Lass dich von einer Hürde nicht vom ganzen Weg abbringen.",
    "Du kannst mehr entdecken, als du dir heute vorstellst.",
    "Ein guter Lernplan lässt auch Raum zum Durchatmen.",
    "Vergleiche dich mit deinem Gestern, nicht mit anderen.",
    "Dein Mut zum Fragen ist eine echte Stärke.",
    "Mit Geduld und Übung wächst dein Können.",
    "Jede neue Idee ist ein Funke für deinen Wissensschatz.",
    "Du darfst langsam gehen und trotzdem weit kommen.",
    "Ein kleiner Erfolg ist ein guter Grund zum Freuen.",
    "Dein Ziel bleibt erreichbar, auch wenn du eine Pause brauchst.",
    "Aus einem Versuch wird Erfahrung, aus Erfahrung wird Sicherheit.",
    "Gib deiner Aufmerksamkeit heute eine Aufgabe nach der anderen.",
    "Du musst den ganzen Weg noch nicht kennen, um loszugehen.",
    "Wiederholen heißt, deinem Wissen feste Wurzeln zu geben.",
    "Dein Lernen gehört dir, gestalte es mit Neugier.",
    "Eine schwierige Frage kann der Anfang einer großartigen Erkenntnis sein.",
    "Mit jedem Lerntag zeichnest du deine eigene Landkarte des Wissens.",
    "Dein Fortschritt muss nicht laut sein, um wichtig zu sein.",
    "Du darfst Hilfe holen und trotzdem stolz auf deinen Weg sein.",
    "Eine erledigte Lerneinheit ist ein verdienter kleiner Sieg.",
    "Manchmal zeigt sich dein Fortschritt erst beim zweiten Blick.",
    "Dein Wissen ist ein Werkzeug für die Abenteuer von morgen.",
    "Beginne mit dem, was du kannst, und entdecke den nächsten Schritt.",
    "Auch nach einem Umweg kannst du dein Ziel erreichen.",
    "Du bringst mit jeder Übung mehr Licht ins Unbekannte.",
    "Heute zählt nicht Perfektion, sondern dein nächster guter Schritt.",
)


def choose_motivations(request):
    previous = request.session.get("motivation_indices", [])
    available = [index for index in range(len(SENTENCES)) if index not in previous]
    indices = random.sample(available, 3)
    request.session["motivation_indices"] = indices
    return dict(zip(("top", "open", "done"), (SENTENCES[index] for index in indices), strict=True))
