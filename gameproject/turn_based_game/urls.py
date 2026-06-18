from django.urls import path
from . import views
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('debug/', views.debug_view, name='debug'),

    path('signup/', views.signup, name='signup'),
]

