# Docker deployment

The Compose stack stores SQLite at `/data/db.sqlite3` in the named volume
`lernplan_data`. Recreating or updating the web container keeps that volume.
Do not delete the volume when removing the stack (`docker compose down -v`),
because that permanently deletes the database.

## Migrating data from the previous stack

The previous setup stored SQLite inside the container at `/app/db.sqlite3`.
That file is not copied automatically into the new volume. Before updating the
stack, create a consistent backup on the Docker host:

```sh
docker exec lernplan-web python -c \
  "import sqlite3; source=sqlite3.connect('/app/db.sqlite3'); backup=sqlite3.connect('/tmp/lernplan-backup.sqlite3'); source.backup(backup); backup.close(); source.close()"
docker cp lernplan-web:/tmp/lernplan-backup.sqlite3 ./lernplan-backup.sqlite3
```

After updating the stack, stop its new web container and copy the backup into
the persistent data directory (replace `<new-container>` with its container
name or ID):

```sh
docker cp ./lernplan-backup.sqlite3 <new-container>:/data/db.sqlite3
docker start <new-container>
```

The container applies any pending Django migrations when it starts. Keep the
backup until you have confirmed the data is present in the updated app.

Demo data is no longer created automatically on startup. To create it
intentionally in a fresh installation, run:

```sh
docker compose exec web python manage.py seed_demo_data
```
