from datetime import date, datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.portfolio.models import CallLog, Debtor, Payment, Portfolio, PromiseToPay
from apps.users.models import AppUser, UserRole


PACKAGE_COUNT = 5
DEBTORS_PER_PACKAGE = 500

FIRST_NAMES = [
    'Ivan', 'Georgi', 'Maria', 'Nikolay', 'Elena', 'Petar', 'Desislava', 'Kalin', 'Teodora', 'Martin',
    'Simona', 'Viktor', 'Kristina', 'Radoslav', 'Yoana', 'Dimitar', 'Borislava', 'Simeon', 'Nadezhda', 'Milen',
]

LAST_NAMES = [
    'Petrov', 'Ivanov', 'Koleva', 'Dimitrov', 'Stoyanova', 'Iliev', 'Todorova', 'Vasilev', 'Nikolova', 'Georgiev',
    'Kostova', 'Pavlov', 'Ruseva', 'Hristov', 'Yordanova', 'Atanasov', 'Angelova', 'Mihaylov', 'Dobreva', 'Kanev',
]

REGIONS = [
    'Sofia', 'Plovdiv', 'Varna', 'Burgas', 'Ruse', 'Stara Zagora', 'Pleven', 'Sliven', 'Dobrich', 'Shumen',
]

PACKAGE_DEFINITIONS = [
    ('Retail Recovery Pack Alpha', 'DSK Retail Recovery', date(2025, 10, 1), Decimal('185000.00'), Decimal('812000.00')),
    ('Consumer Debt Pack Beta', 'Postbank Consumer Finance', date(2025, 10, 8), Decimal('212000.00'), Decimal('905000.00')),
    ('SME Collections Pack Gamma', 'UniCredit Business Leasing', date(2025, 10, 14), Decimal('276000.00'), Decimal('1140000.00')),
    ('Telecom Arrears Pack Delta', 'A1 Telecom Portfolio Sales', date(2025, 10, 21), Decimal('148000.00'), Decimal('689000.00')),
    ('Utilities Debt Pack Epsilon', 'National Utilities Recovery', date(2025, 10, 28), Decimal('193000.00'), Decimal('861000.00')),
]


class Command(BaseCommand):
    help = 'Seed demo users and sample debt/risk data for local testing.'

    @transaction.atomic
    def handle(self, *args, **options):
        users = self._seed_users()
        portfolio = self._seed_portfolio(users['manager'])
        debtors = self._seed_debtors(portfolio)
        self._seed_payments_and_calls(debtors, users['analyst'])
        bulk_portfolios = self._seed_bulk_packages(users['manager'], users['analyst'])

        self.stdout.write(self.style.SUCCESS('Demo data ready.'))
        self.stdout.write('Users:')
        self.stdout.write('  manager_demo / DemoPass123! (Manager)')
        self.stdout.write('  analyst_demo / DemoPass123! (Analyst)')
        self.stdout.write('  admin_demo / DemoPass123! (Admin)')
        self.stdout.write(f'Portfolio: {portfolio.name} ({portfolio.id})')
        self.stdout.write(f'Bulk packages: {len(bulk_portfolios)} portfolios x {DEBTORS_PER_PACKAGE} debtors each')
        for package in bulk_portfolios:
            self.stdout.write(f'  - {package.name}')

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

    def _seed_bulk_packages(self, manager, analyst):
        portfolios = []
        today = timezone.localdate()

        for package_index, definition in enumerate(PACKAGE_DEFINITIONS, start=1):
            name, source_company, purchase_date, purchase_price, face_value = definition
            portfolio, _ = Portfolio.objects.update_or_create(
                name=name,
                defaults={
                    'source_company': source_company,
                    'purchase_date': purchase_date,
                    'purchase_price': purchase_price,
                    'face_value': face_value,
                    'currency': 'BGN',
                    'created_by': manager,
                },
            )
            portfolio.debtors.all().delete()
            debtors = self._build_bulk_debtors(portfolio, package_index)
            Debtor.objects.bulk_create(debtors, batch_size=250)
            self._seed_bulk_activity(portfolio, analyst, today)
            portfolios.append(portfolio)

        return portfolios

    def _build_bulk_debtors(self, portfolio, package_index):
        debtors = []
        for debtor_index in range(1, DEBTORS_PER_PACKAGE + 1):
            status = self._status_for_index(debtor_index)
            days_past_due = self._days_past_due_for_status(status, debtor_index)
            outstanding_principal = self._principal_amount(package_index, debtor_index, status)
            outstanding_total = self._outstanding_total(outstanding_principal, status, debtor_index)
            risk_score = self._risk_score(status, days_past_due, outstanding_total)
            risk_band = self._risk_band(risk_score)

            debtors.append(
                Debtor(
                    portfolio=portfolio,
                    external_id=f'PK{package_index:02d}-{debtor_index:04d}',
                    full_name=self._full_name(package_index, debtor_index),
                    national_id=f'{package_index:02d}{debtor_index:08d}',
                    phone_number=f'+35988{package_index}{debtor_index:06d}'[:13],
                    email=f'portfolio{package_index}_{debtor_index}@demo-risk.local',
                    region=REGIONS[(package_index + debtor_index) % len(REGIONS)],
                    status=status,
                    days_past_due=days_past_due,
                    outstanding_principal=outstanding_principal,
                    outstanding_total=outstanding_total,
                    risk_score=risk_score,
                    risk_band=risk_band,
                    risk_factors=self._risk_factors(status, days_past_due, risk_band),
                )
            )

        return debtors

    def _seed_bulk_activity(self, portfolio, analyst, today):
        debtors = list(portfolio.debtors.order_by('id'))
        payments = []
        call_logs = []
        promise_candidates = []

        for idx, debtor in enumerate(debtors, start=1):
            if debtor.status in {'contacted', 'promise_to_pay', 'paying', 'closed'}:
                call_datetime = timezone.make_aware(
                    datetime.combine(today - timedelta(days=(idx % 12) + 1), datetime.min.time())
                ) + timedelta(hours=9 + (idx % 8), minutes=(idx * 7) % 60)
                outcome = self._call_outcome_for_status(debtor.status)
                call_log = CallLog(
                    debtor=debtor,
                    agent=analyst,
                    call_datetime=call_datetime,
                    outcome=outcome,
                    duration_seconds=90 + (idx % 6) * 45,
                    promised_amount=Decimal('0.00'),
                    notes='Seeded bulk package activity',
                )
                if debtor.status == 'promise_to_pay':
                    call_log.promised_amount = min(debtor.outstanding_total, Decimal('420.00'))
                    promise_candidates.append((debtor, call_log))
                call_logs.append(call_log)

            if debtor.status in {'paying', 'closed'} or (debtor.status == 'promise_to_pay' and idx % 3 == 0):
                payment_amount = self._payment_amount(debtor)
                payments.append(
                    Payment(
                        debtor=debtor,
                        paid_amount=payment_amount,
                        payment_date=today - timedelta(days=(idx % 20) + 1),
                        channel='bank_transfer' if idx % 2 == 0 else 'cash',
                        reference=f'SEED-{portfolio.id}-{debtor.external_id}',
                        is_confirmed=True,
                    )
                )

        if call_logs:
            CallLog.objects.bulk_create(call_logs, batch_size=250)

        if payments:
            Payment.objects.bulk_create(payments, batch_size=250)

        promises = []
        for debtor, call_log in promise_candidates:
            promises.append(
                PromiseToPay(
                    debtor=debtor,
                    call_log=call_log,
                    promised_amount=min(debtor.outstanding_total, Decimal('420.00')),
                    due_date=today + timedelta(days=(debtor.id % 10) + 2),
                    status=PromiseToPay.PromiseStatus.PENDING,
                    notes='Seeded bulk promise to pay',
                )
            )

        if promises:
            PromiseToPay.objects.bulk_create(promises, batch_size=250)

    def _status_for_index(self, debtor_index):
        cycle = debtor_index % 20
        if cycle < 6:
            return 'new'
        if cycle < 10:
            return 'contacted'
        if cycle < 13:
            return 'promise_to_pay'
        if cycle < 17:
            return 'paying'
        return 'closed'

    def _days_past_due_for_status(self, status, debtor_index):
        if status == 'new':
            return 120 + (debtor_index % 240)
        if status == 'contacted':
            return 45 + (debtor_index % 120)
        if status == 'promise_to_pay':
            return 30 + (debtor_index % 90)
        if status == 'paying':
            return 10 + (debtor_index % 60)
        return debtor_index % 25

    def _principal_amount(self, package_index, debtor_index, status):
        base = Decimal('280.00') + Decimal(package_index * 75) + Decimal((debtor_index % 90) * 18)
        if status == 'new':
            multiplier = Decimal('1.85')
        elif status == 'contacted':
            multiplier = Decimal('1.35')
        elif status == 'promise_to_pay':
            multiplier = Decimal('1.15')
        elif status == 'paying':
            multiplier = Decimal('0.72')
        else:
            multiplier = Decimal('0.05')
        return (base * multiplier).quantize(Decimal('0.01'))

    def _outstanding_total(self, principal, status, debtor_index):
        if status == 'closed':
            return Decimal('0.00')
        fee_rate = Decimal('0.08') + Decimal(debtor_index % 5) / Decimal('100')
        if status == 'paying':
            fee_rate = Decimal('0.05')
        return (principal * (Decimal('1.00') + fee_rate)).quantize(Decimal('0.01'))

    def _risk_score(self, status, days_past_due, outstanding_total):
        score = 18
        if status == 'new':
            score += 24
        elif status == 'contacted':
            score += 14
        elif status == 'promise_to_pay':
            score += 10
        elif status == 'paying':
            score += 4

        score += min(days_past_due // 6, 36)
        if outstanding_total >= Decimal('6000.00'):
            score += 14
        elif outstanding_total >= Decimal('2500.00'):
            score += 8
        elif outstanding_total >= Decimal('900.00'):
            score += 4

        return min(int(score), 95)

    def _risk_band(self, risk_score):
        if risk_score >= 70:
            return Debtor.RiskBand.HIGH
        if risk_score >= 40:
            return Debtor.RiskBand.MEDIUM
        return Debtor.RiskBand.LOW

    def _risk_factors(self, status, days_past_due, risk_band):
        return f'bulk_seed::{status}::{days_past_due}_dpd::{risk_band}'

    def _payment_amount(self, debtor):
        if debtor.status == 'closed':
            return min(debtor.outstanding_principal or Decimal('0.00'), Decimal('520.00'))
        if debtor.status == 'paying':
            return min(debtor.outstanding_total * Decimal('0.22'), Decimal('380.00')).quantize(Decimal('0.01'))
        return min(debtor.outstanding_total * Decimal('0.12'), Decimal('250.00')).quantize(Decimal('0.01'))

    def _call_outcome_for_status(self, status):
        if status == 'promise_to_pay':
            return CallLog.Outcome.PROMISE_TO_PAY
        if status in {'paying', 'closed'}:
            return CallLog.Outcome.PAID
        if status == 'contacted':
            return CallLog.Outcome.NO_ANSWER
        return CallLog.Outcome.REFUSED

    def _full_name(self, package_index, debtor_index):
        first_name = FIRST_NAMES[(package_index + debtor_index) % len(FIRST_NAMES)]
        last_name = LAST_NAMES[(package_index * 3 + debtor_index) % len(LAST_NAMES)]
        return f'{first_name} {last_name}'
