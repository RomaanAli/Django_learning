from django.db import migrations, models


def grandfather_instructors(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    InstructorDocument = apps.get_model("accounts", "InstructorDocument")

    # Grandfather all existing instructors so existing demo and instructor accounts retain course management
    User.objects.filter(role="instructor").update(is_approved_instructor=True)

    # Also grandfather any user who already has an approved InstructorDocument
    approved_user_ids = InstructorDocument.objects.filter(status="approved").values_list("user_id", flat=True)
    if approved_user_ids:
        User.objects.filter(id__in=approved_user_ids).update(is_approved_instructor=True)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_instructordocument"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="is_approved_instructor",
            field=models.BooleanField(
                default=False,
                help_text="Designates whether this instructor has been approved to teach courses.",
                verbose_name="approved instructor",
            ),
        ),
        migrations.AddField(
            model_name="instructordocument",
            name="review_note",
            field=models.TextField(
                blank=True,
                help_text="Reason for denial or reviewer notes shown to the instructor.",
                verbose_name="review note",
            ),
        ),
        migrations.RunPython(
            grandfather_instructors,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
