from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from finance.models import WithdrawRequest
from finance.serializers import WithdrawRequestSerializer



class WithdrawRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WithdrawRequestSerializer
    

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get(self, request):
        withdraw_requests = WithdrawRequest.objects.filter(user=request.user)
        serializer = self.serializer_class(withdraw_requests, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


