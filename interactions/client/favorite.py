from rest_framework import generics, permissions, status
from rest_framework.response import Response
from ..models import  Favorite
from ..serializers import  FavoriteSerializer


class FavoriteListCreateView(generics.ListCreateAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        gym = self.request.data.get('gym')
        if Favorite.objects.filter(user=self.request.user, gym_id=gym).exists():
            raise serializers.ValidationError({'detail': 'This gym is already in favorites.'})
        serializer.save(user=self.request.user)


class FavoriteDetailView(generics.DestroyAPIView):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user)