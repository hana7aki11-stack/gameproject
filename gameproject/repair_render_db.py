
import os

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "gameproject.settings"
)

import django
django.setup()

from django.db import connection, transaction
from django.db.migrations.recorder import MigrationRecorder
from turn_based_game.models import ClearLog


APP = "turn_based_game"

OLD_0010 = "0010_playsession"
OLD_0011 = "0011_playsession_last_seen_at"

NEW_0010 = (
    "0010_savedata_round_play_seconds_clearlog_playsession"
)
NEW_0011 = (
    "0011_remove_savedata_total_play_seconds"
)


def get_columns(cursor, table_name):
    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = %s
    """, [table_name])

    return {row[0] for row in cursor.fetchall()}


def repair():

    # Render以外では実行しない
    if not os.environ.get("RENDER"):
        raise RuntimeError(
            "Render環境以外では実行できません"
        )

    # PostgreSQL以外では実行しない
    if connection.vendor != "postgresql":
        raise RuntimeError(
            "PostgreSQL以外では実行できません"
        )

    print(
        "===== RENDER DB REPAIR START =====",
        flush=True
    )

    with transaction.atomic():

        recorder = MigrationRecorder(connection)
        applied = recorder.applied_migrations()

        new_0010_applied = (APP, NEW_0010) in applied
        new_0011_applied = (APP, NEW_0011) in applied

        # 修復済みの場合もテーブル構造を確認する
        if new_0010_applied and new_0011_applied:

            tables = set(connection.introspection.table_names())

            required_tables = {
                "turn_based_game_savedata",
                "turn_based_game_playsession",
                "turn_based_game_clearlog",
            }

            if not required_tables.issubset(tables):
                raise RuntimeError(
                    "修復済みの履歴がありますが、必要なテーブルが不足しています"
                )

            with connection.cursor() as cursor:
                save_columns = get_columns(
                    cursor, "turn_based_game_savedata"
                )
                play_columns = get_columns(
                    cursor, "turn_based_game_playsession"
                )

            if not {"round_play_seconds", "total_play_seconds"}.issubset(save_columns):
                raise RuntimeError(
                    "修復済みの履歴がありますが、SaveDataのカラムが不足しています"
                )

            required_play_columns = {
                "id", "user_id", "game_round", "started_at",
                "last_seen_at", "logged_out_at", "page_views",
            }

            if not required_play_columns.issubset(play_columns):
                raise RuntimeError(
                    "修復済みの履歴がありますが、PlaySessionのカラムが不足しています"
                )

            print("ALREADY REPAIRED: schema verified", flush=True)
            return

        # 片方だけ適用済みなら停止
        if new_0010_applied != new_0011_applied:
            raise RuntimeError(
                "新しい0010と0011の適用状態が一致しません"
            )

        # 古いマイグレーション履歴を確認
        if (
            (APP, OLD_0010) not in applied
            or (APP, OLD_0011) not in applied
        ):
            raise RuntimeError(
                "想定している古いマイグレーション履歴がありません"
            )

        with connection.cursor() as cursor:

            # 必要なテーブルが存在するか確認
            tables = set(
                connection.introspection.table_names()
            )

            required_tables = {
                "turn_based_game_savedata",
                "turn_based_game_playsession",
            }

            if not required_tables.issubset(tables):
                raise RuntimeError(
                    "必要な既存テーブルがありません"
                )

            # 既存プレイ時間データを確認
            save_columns = get_columns(
                cursor,
                "turn_based_game_savedata"
            )

            if "total_play_seconds" not in save_columns:
                raise RuntimeError(
                    "既存のtotal_play_secondsが見つかりません"
                )

            cursor.execute("""
                SELECT id, total_play_seconds
                FROM turn_based_game_savedata
                ORDER BY id
            """)

            preserved_play_times = cursor.fetchall()

            # 修復前のプレイ時間を退避する
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS
                repair_backup_savedata_play_seconds (
                    savedata_id bigint PRIMARY KEY,
                    total_play_seconds integer
                )
            """)

            cursor.execute("""
                INSERT INTO repair_backup_savedata_play_seconds
                    (savedata_id, total_play_seconds)
                SELECT id, total_play_seconds
                FROM turn_based_game_savedata
                ON CONFLICT (savedata_id) DO NOTHING
            """)

            print(
                "BACKUP: existing play time records preserved",
                flush=True
            )

            print(
                f"EXISTING PLAY TIME RECORDS: {len(preserved_play_times)}",
                flush=True
            )



            # SaveDataに新しいプレイ時間カラムを追加
            cursor.execute("""
                ALTER TABLE turn_based_game_savedata
                ADD COLUMN IF NOT EXISTS
                round_play_seconds integer NOT NULL DEFAULT 0
            """)

            # PlaySessionの不足カラムを追加
            cursor.execute("""
                ALTER TABLE turn_based_game_playsession
                ADD COLUMN IF NOT EXISTS
                game_round integer NOT NULL DEFAULT 1
            """)

            cursor.execute("""
                ALTER TABLE turn_based_game_playsession
                ADD COLUMN IF NOT EXISTS
                logged_out_at timestamp with time zone
            """)

            cursor.execute("""
                ALTER TABLE turn_based_game_playsession
                ADD COLUMN IF NOT EXISTS
                page_views integer NOT NULL DEFAULT 0
            """)

            # 最終操作時刻がNULLなら開始時刻で補完
            cursor.execute("""
                UPDATE turn_based_game_playsession
                SET last_seen_at = started_at
                WHERE last_seen_at IS NULL
            """)

            cursor.execute("""
                ALTER TABLE turn_based_game_playsession
                ALTER COLUMN last_seen_at SET NOT NULL
            """)

            # 古い必須カラムが新規保存を妨げないようにする
            cursor.execute("""
                ALTER TABLE turn_based_game_playsession
                ALTER COLUMN duration_seconds SET DEFAULT 0
            """)

            cursor.execute("""
                ALTER TABLE turn_based_game_playsession
                ALTER COLUMN created_at
                SET DEFAULT CURRENT_TIMESTAMP
            """)

        # ClearLogテーブルを作成
        if (
            ClearLog._meta.db_table
            not in connection.introspection.table_names()
        ):
            with connection.schema_editor(
                atomic=False
            ) as editor:
                editor.create_model(ClearLog)

            print(
                "CREATED: ClearLog",
                flush=True
            )

        # 修復結果を検証
        with connection.cursor() as cursor:

            play_columns = get_columns(
                cursor,
                "turn_based_game_playsession"
            )

            required_play_columns = {
                "id",
                "user_id",
                "game_round",
                "started_at",
                "last_seen_at",
                "logged_out_at",
                "page_views",
            }

            missing = required_play_columns - play_columns

            # 古い必須カラムのデフォルト値を確認
            cursor.execute("""
                SELECT column_name, column_default
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'turn_based_game_playsession'
                  AND column_name IN ('duration_seconds', 'created_at')
            """)

            legacy_defaults = dict(cursor.fetchall())

            if (
                    not legacy_defaults.get("duration_seconds")
                    or not legacy_defaults.get("created_at")
            ):
                raise RuntimeError(
                    "PlaySessionの古い必須カラムにデフォルト値がありません"
                )

            print(
                "VERIFIED: PlaySession legacy defaults",
                flush=True
            )

            if missing:
                raise RuntimeError(
                    f"PlaySessionのカラム不足: {missing}"
                )

            save_columns = get_columns(
                cursor,
                "turn_based_game_savedata"
            )

            if "round_play_seconds" not in save_columns:
                raise RuntimeError(
                    "round_play_secondsが存在しません"
                )

            # 古いプレイ時間データが残っているか確認
            if "total_play_seconds" not in save_columns:
                raise RuntimeError(
                    "古いプレイ時間カラムが消えています"
                )

            cursor.execute("""
                SELECT id, total_play_seconds
                FROM turn_based_game_savedata
                ORDER BY id
            """)

            after_play_times = cursor.fetchall()

            if after_play_times != preserved_play_times:
                raise RuntimeError(
                    "既存プレイ時間データの値が変化しました"
                )


        # 退避先のプレイ時間データも検証する
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT savedata_id, total_play_seconds
                FROM repair_backup_savedata_play_seconds
                WHERE savedata_id IN (
                    SELECT id FROM turn_based_game_savedata
                )
                ORDER BY savedata_id
            """)

            backup_play_times = cursor.fetchall()

        if backup_play_times != preserved_play_times:
            raise RuntimeError(
                "退避先のプレイ時間データが元データと一致しません"
            )

        print(
            "VERIFIED: existing play time data and backup match",
            flush=True
        )


        backup_play_times = cursor.fetchall()

        if backup_play_times != preserved_play_times:
            raise RuntimeError(
                "退避先のプレイ時間データが元データと一致しません"
            )

        print(
            "VERIFIED: existing play time data and backup match",
            flush=True
        )

        if (
            ClearLog._meta.db_table
            not in connection.introspection.table_names()
        ):
            raise RuntimeError(
                "ClearLogテーブルが存在しません"
            )

        # 最後に新しいマイグレーション履歴を登録
        recorder.record_applied(APP, NEW_0010)
        recorder.record_applied(APP, NEW_0011)

    print(
        "===== RENDER DB REPAIR SUCCESS =====",
        flush=True
    )


if __name__ == "__main__":
    repair()
