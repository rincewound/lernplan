from django.db import migrations


def remove_study_block_suffix(apps, schema_editor):
    LearningTask = apps.get_model("lernplan", "LearningTask")
    database = schema_editor.connection.alias
    tasks = LearningTask.objects.using(database).filter(
        source_kind="study_plan",
        title__endswith=" study block",
    )
    for task in tasks.iterator():
        task.title = task.title.removesuffix(" study block")
        task.save(using=database, update_fields=["title"])


class Migration(migrations.Migration):

    dependencies = [
        ("lernplan", "0002_remove_vacation_owner_studyplan_effective_from_and_more"),
    ]

    operations = [
        migrations.RunPython(remove_study_block_suffix, migrations.RunPython.noop),
    ]
