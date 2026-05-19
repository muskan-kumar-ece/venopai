from django.db import migrations


def create_paymentevent_immutable_triggers(apps, schema_editor):
    if schema_editor.connection.vendor == "sqlite":
        schema_editor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS payments_paymentevent_prevent_update
            BEFORE UPDATE ON payments_paymentevent
            BEGIN
                SELECT RAISE(ABORT, 'PaymentEvent is immutable and cannot be updated.');
            END;
            """
        )
        schema_editor.execute(
            """
            CREATE TRIGGER IF NOT EXISTS payments_paymentevent_prevent_delete
            BEFORE DELETE ON payments_paymentevent
            BEGIN
                SELECT RAISE(ABORT, 'PaymentEvent is immutable and cannot be deleted.');
            END;
            """
        )
    elif schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            """
            CREATE OR REPLACE FUNCTION payments_paymentevent_immutable()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'PaymentEvent is immutable and cannot be %%', TG_OP;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        schema_editor.execute(
            """
            CREATE TRIGGER payments_paymentevent_prevent_update
            BEFORE UPDATE ON payments_paymentevent
            FOR EACH ROW EXECUTE FUNCTION payments_paymentevent_immutable();
            """
        )
        schema_editor.execute(
            """
            CREATE TRIGGER payments_paymentevent_prevent_delete
            BEFORE DELETE ON payments_paymentevent
            FOR EACH ROW EXECUTE FUNCTION payments_paymentevent_immutable();
            """
        )


def drop_paymentevent_immutable_triggers(apps, schema_editor):
    if schema_editor.connection.vendor == "sqlite":
        schema_editor.execute("DROP TRIGGER IF EXISTS payments_paymentevent_prevent_update;")
        schema_editor.execute("DROP TRIGGER IF EXISTS payments_paymentevent_prevent_delete;")
    elif schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP TRIGGER IF EXISTS payments_paymentevent_prevent_update ON payments_paymentevent;")
        schema_editor.execute("DROP TRIGGER IF EXISTS payments_paymentevent_prevent_delete ON payments_paymentevent;")
        schema_editor.execute("DROP FUNCTION IF EXISTS payments_paymentevent_immutable();")


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0003_paymentevent_prevent_update"),
    ]

    operations = [
        migrations.RunPython(
            create_paymentevent_immutable_triggers,
            reverse_code=drop_paymentevent_immutable_triggers,
        ),
    ]
