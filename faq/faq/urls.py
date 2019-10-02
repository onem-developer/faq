from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path(
        'search_wizard/', views.SearchView.as_view(),
        name='search_wizard'
    ),
    path(
        'faqs/<str:category>/', views.FaqsView.as_view(),
        name='faqs'
    ),
    path(
        'faq/<int:id>/', views.FaqView.as_view(),
        name='faq'
    ),
    path(
        'add_faq/', views.AddFaqView.as_view(),
        name='add_faq'
    ),
    path(
        'edit_faq/<int:id>/<str:type>', views.EditFaqView.as_view(),
        name='edit_faq'
    ),
]
