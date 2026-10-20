from django.contrib import admin
from .models import SaveData, ActionLog


@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):

    # 一覧画面に表示する項目
    list_display = (
        'user',
        'action',
        'turn',
        'result',
        'energy',
        'fullness',
        'satisfaction',
        'growth',
        'timestamp',
    )

    # 検索
    search_fields = (
        'user__username',
        'action',
    )

    # 絞り込み
    list_filter = (
        'action',
        'user',
    )

    # 新しい順に並べる
    ordering = ('-timestamp',)

    # 編集不可（ログは読み取り専用にする）
    readonly_fields = (
        'user',
        'action',
        'turn',
        'energy',
        'fullness',
        'satisfaction',
        'growth',
        'result',
        'timestamp',
    )


@admin.register(SaveData)
class SaveDataAdmin(admin.ModelAdmin):

    # ========================================
    # 一覧画面に表示する項目
    # ========================================
    list_display = (
        'user',
        'growth',
        'energy',
        'satisfaction',
        'fullness',
        'turn',
        'play_count',
        'clear_count',
        'game_over_count',
        'total_play_seconds',
    )

    # ========================================
    # 検索
    # ========================================
    search_fields = (
        'user__username',
    )

    # ========================================
    # 絞り込み
    # ========================================
    list_filter = (
        'character_state',
        'room_wallpaper',
    )

    # ========================================
    # 詳細画面の項目をグループ化
    # ========================================
    fieldsets = (

        (
            'ユーザー情報',
            {
                'fields': (
                    'user',
                )
            }
        ),

        (
            'キャラクターの基本ステータス',
            {
                'fields': (
                    'satisfaction',
                    'energy',
                    'growth',
                    'fullness',
                )
            }
        ),

        (
            'ゲーム進行状況',
            {
                'fields': (
                    'turn',
                    'remaining_time',
                )
            }
        ),

        (
            'プレイ状況',
            {
                'fields': (
                    'play_count',
                    'play_session_count',
                    'total_play_seconds',
                    'play_started_at',
                )
            }
        ),

        (
            '食事関連',
            {
                'fields': (
                    'healthy_food_count',
                    'snack_count',
                )
            }
        ),

        (
            '行動の選択回数',
            {
                'fields': (
                    'action_rest_count',
                    'action_ball_count',
                    'action_food_count',
                    'action_dodge_count',
                    'action_dance_count',
                    'action_timing_count',
                    'action_count_count',
                    'action_next_day_count',
                )
            }
        ),

        (
            '育成結果',
            {
                'fields': (
                    'clear_count',
                    'game_over_count',
                    'clear_time_seconds',
                )
            }
        ),

        (
            'ボールキャッチ',
            {
                'fields': (
                    'minigame_ball_play',
                    'minigame_ball_success',
                )
            }
        ),

        (
            'ごはん選び',
            {
                'fields': (
                    'minigame_food_play',
                    'minigame_food_success',
                )
            }
        ),

        (
            '障害物よけ',
            {
                'fields': (
                    'minigame_dodge_play',
                    'minigame_dodge_success',
                )
            }
        ),

        (
            'ダンスまね',
            {
                'fields': (
                    'minigame_dance_play',
                    'minigame_dance_success',
                )
            }
        ),

        (
            '火加減チャレンジ',
            {
                'fields': (
                    'minigame_timing_play',
                    'minigame_timing_success',
                )
            }
        ),

        (
            '食材かぞえ',
            {
                'fields': (
                    'minigame_count_play',
                    'minigame_count_success',
                )
            }
        ),

        (
            'キャラクター・部屋',
            {
                'fields': (
                    'character_state',
                    'room_wallpaper',
                )
            }
        ),

        (
            'アイテム',
            {
                'fields': (
                    'items',
                    'placed_items',
                )
            }
        ),
    )