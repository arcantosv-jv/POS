"""Validaciones compartidas de importes y texto de operaciones."""
from decimal import Decimal, InvalidOperation


def money(value, field='Monto'):
    try:
        amount = Decimal(str(value))
        if (not amount.is_finite() or amount < 0 or amount > Decimal('99999999.99')
                or amount != amount.quantize(Decimal('0.01'))):
            raise ValueError()
        return amount
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f'{field}: ingresa un importe no negativo con máximo dos decimales')


def text_value(value, field, maximum=2000, required=False):
    if not isinstance(value, str) or len(value.strip()) > maximum:
        raise ValueError(f'{field}: texto inválido (máximo {maximum} caracteres)')
    value = value.strip()
    if required and not value:
        raise ValueError(f'{field} es obligatorio')
    return value
