from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Tags
from .serializers import TagsSerializer


class TagsView(viewsets.ReadOnlyModelViewSet):
    serializer_class = TagsSerializer
    queryset = Tags.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly,)
    pagination_class = None
