from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.portfolio.models import CallLog, Debtor, Payment, Portfolio, PromiseToPay
from apps.users.models import AppUser, UserRole


class Command(BaseCommand):
    help = 'Seed demo users and sample debt/risk data for local testing.'

    @transaction.atomic
    def handle(self, *args, **options):
        users = self._seed_users()
        portfolio = self._seed_portfolio(users['manager'])
        debtors = self._seed_debtors(portfolio)
        self._seed_payments_and_calls(debtors, users['analyst'])

        self.stdout.write(self.style.SUCCESS('Demo data ready.'))
        self.stdout.write('Users:')
        self.stdout.write('  manager_demo / DemoPass123! (Manager)')
        self.stdout.write('  analyst_demo / DemoPass123! (Analyst)')
        self.stdout.write('  admin_demo / DemoPass123! (Admin)')
        self.stdout.write(f'Portfolio: {portfolio.name} ({portfolio.id})')

    def _seed_users(self):
        manager, _ = AppUser.objects.get_or_create(
            username='manager_demo',
            defaults={
                'email': 'manager_demo@example.com',
                'role': UserRole.MANAGER,
                'is_staff': True,
            },
        )
        manager.role = UserRole.MANAGER
        manager.is_staff = True
        manager.set_password('DemoPass123!')
        manager.save()

        analyst, _ = AppUser.objects.get_or_create(
            username='analyst_demo',
            defaults={
                'email': 'analyst_demo@example.com',
                'role': UserRole.ANALYST,
            },
        )
        analyst.role = UserRole.ANALYST
        analyst.set_password('DemoPass123!')
        analyst.save()

        admin, _ = AppUser.objects.get_or_create(
            username='admin_demo',
            defaults={
                'email': 'admin_demo@example.com',
                'role': UserRole.ADMIN,
                'is_staff': True,
                'is_superuser': True,
            },
        )
        admin.role = UserRole.ADMIN
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password('DemoPass123!')
        admin.save()

        return {'manager': manager, 'analyst': analyst, 'admin': admin}

    def _seed_portfolio(self, manager):
        portfolio, _ = Portfolio.objects.get_or_create(
            name='Demo Portfolio March 2026',
            defaults={
                'source_company': 'Ubb Demo Source',
                'purchase_date': date(2026, 3, 1),
                'purchase_price': Decimal('15000.00'),
                'face_value': Decimal('65000.00'),
                'currency': 'BGN',
                'created_by': manager,
            },
        )
        return portfolio

    def _seed_debtors(self, portfolio):
        rows = [
            ('DM-001', 'Ivan Petrov', 'new', 210, Decimal('5400.00'), Decimal('6100.00'), 88, 'high'),
            ('DM-002', 'Georgi Ivanov', 'promise_to_pay', 95, Decimal('2200.00'), Decimal('2600.00'), 66, 'medium'),
            ('DM-003', 'Maria Koleva', 'contacted', 35, Decimal('750.00'), Decimal('920.00'), 48, 'medium'),
            ('DM-004', 'Nikolay Dimitrov', 'paying', 18, Decimal('340.00'), Decimal('410.00'), 31, 'low'),
            ('DM-005', 'Elena Stoyanova', 'closed', 5, Decimal('0.00'), Decimal('0.00'), 10, 'low'),
        ]

        debtors = {}
        for external_id, name, status, dpd, principal, total, score, band in rows:
            debtor, _ = Debtor.objects.get_or_create(
                portfolio=portfolio,
                external_id=external_id,
                defaults={
                    'full_name': name,
                    'status': status,
                    'days_past_due': dpd,
                    'outstanding_principal': principal,
                    'outstanding_total': total,
                    'risk_score': score,
                    'risk_band': band,
                    'risk_factors': 'seed_demo_data command',
                    'phone_number': '+359888000000',
                    'region': 'Sofia',
                },
            )
            debtors[external_id] = debtor

        return debtors

    def _seed_payments_and_calls(self, debtors, analyst):
        today = timezone.localdate()

        Payment.objects.get_or_create(
            debtor=debtors['DM-002'],
            reference='DEMO-PMT-002',
            defaults={
                'paid_amount': Decimal('150.00'),
                'payment_date': today - timedelta(days=2),
                'channel': 'bank_transfer',
                'is_confirmed': True,
            },
        )
        payment_dm004, _ = Payment.objects.get_or_create(
            debtor=debtors['DM-004'],
            reference='DEMO-PMT-004',
            defaults={
                'paid_amount': Decimal('120.00'),
                'payment_date': today - timedelta(days=1),
                'channel': 'cash',
                'is_confirmed': True,
            },
        )

        call_dt = timezone.make_aware(datetime.combine(today - timedelta(days=1), datetime.min.time()))
        call_log, _ = CallLog.objects.get_or_create(
            debtor=debtors['DM-002'],
            call_datetime=call_dt,
            defaults={
                'agent': analyst,
                'outcome': CallLog.Outcome.PROMISE_TO_PAY,
                'duration_seconds': 240,
                'promised_amount': Decimal('250.00'),
                'notes': 'Demo promise to pay call',
            },
        )

        PromiseToPay.objects.get_or_create(
            debtor=debtors['DM-002'],
            call_log=call_log,
            defaults={
                'promised_amount': Decimal('250.00'),
                'due_date': today + timedelta(days=3),
                'status': PromiseToPay.PromiseStatus.PENDING,
                'fulfilled_payment': None,
                'notes': 'Seeded promise',
            },
        )

        Payment.objects.get_or_create(
            debtor=debtors['DM-005'],
            reference='DEMO-PMT-005',
            defaults={
                'paid_amount': Decimal('300.00'),
                'payment_date': today - timedelta(days=4),
                'channel': 'bank_transfer',
                'is_confirmed': True,
            },
        )
