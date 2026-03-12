import csv
import io
from decimal import Decimal, InvalidOperation


REQUIRED_COLUMNS = {
    'external_id',
    'full_name',
    'days_past_due',
    'outstanding_principal',
    'outstanding_total',
}

OPTIONAL_COLUMNS = {
    'national_id',
    'phone_number',
    'email',
    'region',
    'status',
    'risk_band',
}

ALLOWED_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS
ALLOWED_RISK_BANDS = {'low', 'medium', 'high'}


class ImportValidationError(Exception):
    pass


def parse_uploaded_file(uploaded_file):
    file_name = uploaded_file.name.lower()

    if file_name.endswith('.csv'):
        content = uploaded_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        return rows, 'csv'

    raise ImportValidationError('Unsupported file format. Please upload CSV.')


def _to_decimal(value, field_name, row_number):
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise ImportValidationError(f'Row {row_number}: Invalid decimal value in {field_name}.')


def _to_int(value, field_name, row_number):
    try:
        parsed = int(str(value).strip())
        if parsed < 0:
            raise ValueError
        return parsed
    except (ValueError, TypeError):
        raise ImportValidationError(f'Row {row_number}: Invalid integer value in {field_name}.')


def validate_rows(raw_rows):
    if not raw_rows:
        raise ImportValidationError('The uploaded file is empty.')

    columns = {column.strip() for column in raw_rows[0].keys() if column}
    missing_columns = sorted(REQUIRED_COLUMNS - columns)
    if missing_columns:
        raise ImportValidationError(
            f'Missing required columns: {", ".join(missing_columns)}'
        )

    unknown_columns = sorted(columns - ALLOWED_COLUMNS)
    if unknown_columns:
        raise ImportValidationError(
            f'Unexpected columns: {", ".join(unknown_columns)}'
        )

    cleaned_rows = []
    row_errors = []
    seen_external_ids = set()

    for index, row in enumerate(raw_rows, start=2):
        try:
            external_id = str(row.get('external_id', '')).strip()
            full_name = str(row.get('full_name', '')).strip()

            if not external_id:
                raise ImportValidationError(f'Row {index}: external_id is required.')
            if not full_name:
                raise ImportValidationError(f'Row {index}: full_name is required.')
            if external_id in seen_external_ids:
                raise ImportValidationError(f'Row {index}: duplicate external_id in file.')

            seen_external_ids.add(external_id)

            risk_band = str(row.get('risk_band', 'medium')).strip().lower() or 'medium'
            if risk_band not in ALLOWED_RISK_BANDS:
                raise ImportValidationError(f'Row {index}: invalid risk_band value.')

            cleaned_rows.append(
                {
                    'external_id': external_id,
                    'full_name': full_name,
                    'national_id': str(row.get('national_id', '')).strip(),
                    'phone_number': str(row.get('phone_number', '')).strip(),
                    'email': str(row.get('email', '')).strip(),
                    'region': str(row.get('region', '')).strip(),
                    'status': str(row.get('status', 'new')).strip() or 'new',
                    'days_past_due': _to_int(row.get('days_past_due', 0), 'days_past_due', index),
                    'outstanding_principal': _to_decimal(
                        row.get('outstanding_principal', 0),
                        'outstanding_principal',
                        index,
                    ),
                    'outstanding_total': _to_decimal(
                        row.get('outstanding_total', 0),
                        'outstanding_total',
                        index,
                    ),
                    'risk_band': risk_band,
                }
            )
        except ImportValidationError as exc:
            row_errors.append(str(exc))

    return cleaned_rows, row_errors

