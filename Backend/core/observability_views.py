from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .observability import metrics_snapshot


class MetricsSnapshotView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        return Response({"metrics": metrics_snapshot()})
