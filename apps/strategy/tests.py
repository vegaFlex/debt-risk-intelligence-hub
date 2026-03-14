from django.test import TestCase
from django.urls import reverse

from apps.users.models import AppUser, UserRole


class StrategyWorkspaceAccessTests(TestCase):
    def setUp(self):
        self.visitor = AppUser.objects.create_user(username='strategy_visitor', password='DemoPass123!', role=UserRole.VISITOR)
        self.analyst = AppUser.objects.create_user(username='strategy_analyst', password='DemoPass123!', role=UserRole.ANALYST)

    def test_visitor_can_open_strategy_workspace(self):
        self.client.force_login(self.visitor)
        response = self.client.get(reverse('strategy-workspace'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Collections Intelligence')

    def test_analyst_gets_friendly_denial_for_strategy_workspace(self):
        self.client.force_login(self.analyst)
        response = self.client.get(reverse('strategy-workspace'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You do not have permission to access this page.')
