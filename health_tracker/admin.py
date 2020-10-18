from django.contrib import admin
from django.contrib.auth.models import Group, User

from django.apps import apps

models = apps.get_models()

for model in models:
    if model != Group and model != User:
        admin.site.register(model)
