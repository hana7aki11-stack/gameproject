
import os
import django

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "gameproject.settings"
)

django.setup()

from django.db import connection

print("\n========== RENDER DB CHECK ==========", flush=True)

with connection.cursor() as cursor:

    # 現在接続しているデータベースの種類
    print(
        "DATABASE ENGINE:",
        connection.vendor,
        flush=True
    )

    # 既存テーブルを確認
    tables = set(connection.introspection.table_names(cursor))

    for table in [
        "turn_based_game_clearlog",
        "turn_based_game_playsession",
        "turn_based_game_savedata",
        "django_migrations",
    ]:
        print(
            f"TABLE {table}: {table in tables}",
            flush=True
        )

    # SaveDataのカラムを確認
    if "turn_based_game_savedata" in tables:
        columns = {
            col.name
            for col in connection.introspection.get_table_description(
                cursor,
                "turn_based_game_savedata"
            )
        }

        for column in [
            "round_play_seconds",
            "total_play_seconds",
        ]:
            print(
                f"COLUMN {column}: {column in columns}",
                flush=True
            )

    # マイグレーション履歴を確認
    if "django_migrations" in tables:
        cursor.execute(
            """
            SELECT name
            FROM django_migrations
            WHERE app = %s
            ORDER BY name
            """,
            ["turn_based_game"]
        )

        migrations = [row[0] for row in cursor.fetchall()]

        print("APPLIED MIGRATIONS:", flush=True)
        for migration in migrations:
            print(migration, flush=True)

print("========== END DB CHECK ==========\n", flush=True)


# ==========================================
# PlaySessionテーブルの構造を確認
# ==========================================

print("\n===== PLAYSESSION STRUCTURE CHECK =====", flush=True)

with connection.cursor() as cursor:

    table_name = "turn_based_game_playsession"

    if table_name in connection.introspection.table_names(cursor):

        columns = connection.introspection.get_table_description(
            cursor,
            table_name
        )

        for column in columns:
            print(
                f"COLUMN: {column.name}",
                flush=True
            )

    else:
        print("PlaySession table not found", flush=True)

print("===== END PLAYSESSION CHECK =====", flush=True)


# ==========================================
# PlaySessionのカラム制約を確認
# ==========================================

print("\n===== PLAYSESSION COLUMN DETAILS =====", flush=True)

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'turn_based_game_playsession'
        ORDER BY ordinal_position
    """)

    for name, data_type, nullable, default in cursor.fetchall():
        print(
            f"{name} | type={data_type} | "
            f"nullable={nullable} | default={default}",
            flush=True
        )

print("===== END COLUMN DETAILS =====", flush=True)


# ==========================================
# PlaySessionのID自動採番を確認
# ==========================================

print("\n===== PLAYSESSION ID CHECK =====", flush=True)

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT
            column_name,
            is_identity,
            identity_generation,
            column_default
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'turn_based_game_playsession'
          AND column_name = 'id'
    """)

    for name, is_identity, generation, default in cursor.fetchall():
        print(f"COLUMN: {name}", flush=True)
        print(f"IS IDENTITY: {is_identity}", flush=True)
        print(f"IDENTITY GENERATION: {generation}", flush=True)
        print(f"DEFAULT: {default}", flush=True)

print("===== END ID CHECK =====", flush=True)


