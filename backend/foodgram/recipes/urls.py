from django.urls import include, path
from rest_framework.routers import DefaultRouter

from recipes.views import TagsView, IngredientView

router_v1 = DefaultRouter()

router_v1.register('tags', TagsView, basename='tags')
router_v1.register('ingredients', IngredientView, basename='ingredients')


urlpatterns = [
    path('', include(router_v1.urls)),
]