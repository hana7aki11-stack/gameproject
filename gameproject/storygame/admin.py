from django.contrib import admin
from .models import Scene, Choice


class ChoiceInline(admin.TabularInline):
    model = Choice
    fk_name = 'scene'
    extra = 1


class SceneAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]


admin.site.register(Scene, SceneAdmin)
