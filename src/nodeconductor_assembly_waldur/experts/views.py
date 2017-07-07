from __future__ import unicode_literals

from django.conf import settings
from django.db.models import Q
from rest_framework import decorators, exceptions, permissions, status, response, viewsets
from django_filters.rest_framework import DjangoFilterBackend

from nodeconductor.core import views as core_views
from nodeconductor.structure import filters as structure_filters
from nodeconductor.structure import models as structure_models

from . import serializers, models, filters


class ExpertProviderViewSet(viewsets.ModelViewSet):
    queryset = models.ExpertProvider.objects.all()
    serializer_class = serializers.ExpertProviderSerializer
    lookup_field = 'uuid'
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = (structure_filters.GenericRoleFilter, DjangoFilterBackend)
    filter_class = filters.ExpertProviderFilter


def is_expert_manager(user):
    if user.is_staff:
        return True

    return models.ExpertProvider.objects.filter(
        customer__permissions__is_active=True,
        customer__permissions__user=user,
        customer__permissions__role=structure_models.CustomerRole.OWNER,
    ).exists()


class ExpertRequestViewSet(core_views.ActionsViewSet):
    queryset = models.ExpertRequest.objects.all()
    serializer_class = serializers.ExpertRequestSerializer
    lookup_field = 'uuid'
    filter_backends = (structure_filters.GenericRoleFilter, DjangoFilterBackend)
    filter_class = filters.ExpertRequestFilter
    disabled_actions = ['destroy']

    def get_queryset(self):
        qs = super(ExpertRequestViewSet, self).get_queryset()

        if not is_expert_manager(self.request.user):
            qs = qs.filter(
                project__customer__permissions__is_active=True,
                project__customer__permissions__user=self.request.user,
                project__customer__permissions__role=structure_models.CustomerRole.OWNER,
            )

        return qs

    @decorators.list_route()
    def configured(self, request):
        return response.Response(settings.WALDUR_SUPPORT['OFFERINGS'], status=status.HTTP_200_OK)


class ExpertBidViewSet(core_views.ActionsViewSet):
    queryset = models.ExpertBid.objects.all()
    serializer_class = serializers.ExpertBidSerializer
    lookup_field = 'uuid'
    filter_backends = (structure_filters.GenericRoleFilter, DjangoFilterBackend)
    filter_class = filters.ExpertBidFilter
    disabled_actions = ['destroy', 'update']

    def is_expert_manager(request, view, obj=None):
        if not is_expert_manager(request.user):
            raise exceptions.PermissionDenied()

    create_permissions = [is_expert_manager]

    def get_queryset(self):
        qs = super(ExpertBidViewSet, self).get_queryset()

        expert_manager_query = Q(
            team__customer__permissions__is_active=True,
            team__customer__permissions__user=self.request.user,
            team__customer__permissions__role=structure_models.CustomerRole.OWNER,
        )
        request_customer_query = Q(
            request__project__customer__permissions__is_active=True,
            request__project__customer__permissions__user=self.request.user,
            request__project__customer__permissions__role=structure_models.CustomerRole.OWNER,
        )

        if not self.request.user.is_staff:
            qs = qs.filter(expert_manager_query | request_customer_query)

        return qs
