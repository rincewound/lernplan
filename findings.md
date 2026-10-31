* The way vacations are modeled is bad. The current impl requires us to create each vacation for each user individually, making it prone to errors. What we actually want is:
  * Be able to create vacations
  * Assign a vacation to an arbitrary number of users. 
  * A vacation that is assigned to a user is active WRT that user's tasks#
* Es ist nicht möglich existierende Lerneinheiten zu bearbeiten. Was funktionieren sollte:
  * CRUD
  * Gültigkeit von - bis, mit bis = optional. Wenn kein "bis" gesetzt ist gültig für immer.
  * Achtung: Wenn Lerneinheiten bearbeitet werden dürfen Tasks, die in der Vergangenheit von den Lerneinheiten erzeugt wurden nicht mehr geändert werden. Auch wenn eine LE gelöscht wird dürfen die Tasks in der vergangenheit nicht verschwinden. Beispiel:
    * LE 1: Jeden Tag, 30 Min, ab 1.11.2026, offenes Ende
    * Am 10.11. wird LE 1 bearbeitet, nur noch 20 Minuten, weiter offenes Ende
    => Die Tasks vor dem 10.11. sind weiterhin 30 min. 
    * Am 31.11. wird LE1 gelöscht
    => Die Tasks vor dem 31.11. für LE1 bleiben vorhanden und können im Kalender nachvollzogen werden.
* Die Kalenderansicht muss auch in die Vergangenheit gehen, sodass geprüft werden kann ob in der Vergangenheit alle Tasks bearbeitet werden können.

Du must keine kompatibilität mit der vorherigen Version erhalten.