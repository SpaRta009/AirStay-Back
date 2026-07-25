# ============================================================
# NOUVEAU FICHIER : credits_utils.py (à côté de models.py)
# ============================================================
from django.db import transaction
from django.db.models import Sum
from datetime import date
from .models import CreditBatch, CreditTransaction

CREDIT_COST_CREATE = 1
CREDIT_COST_EDIT = 1


class InsufficientCreditsError(Exception):
    pass


def expire_old_batches(user):
    """À appeler avant toute lecture/consommation : purge les lots expirés."""
    expired = CreditBatch.objects.filter(user=user, remaining__gt=0, expires_at__lte=date.today())
    for batch in expired:
        if batch.remaining > 0:
            CreditTransaction.objects.create(
                user=user, action='expired', amount=-batch.remaining
            )
        batch.remaining = 0
        batch.save(update_fields=['remaining'])


def get_balance(user):
    expire_old_batches(user)
    return CreditBatch.objects.filter(user=user, expires_at__gt=date.today()) \
        .aggregate(total=Sum('remaining'))['total'] or 0


@transaction.atomic
def consume_credits(user, amount, action, property_obj=None):
    """
    Débite `amount` crédits en FIFO sur les lots non expirés.
    Lève InsufficientCreditsError si le solde est insuffisant.
    """
    expire_old_batches(user)
    batches = CreditBatch.objects.select_for_update().filter(
        user=user, remaining__gt=0, expires_at__gt=date.today()
    ).order_by('purchased_at')

    total_available = sum(b.remaining for b in batches)
    if total_available < amount:
        raise InsufficientCreditsError(
            f"Solde insuffisant : {total_available} crédit(s) disponible(s), {amount} requis."
        )

    to_deduct = amount
    for batch in batches:
        if to_deduct <= 0:
            break
        take = min(batch.remaining, to_deduct)
        batch.remaining -= take
        batch.save(update_fields=['remaining'])
        to_deduct -= take

    CreditTransaction.objects.create(
        user=user, action=action, amount=-amount, property=property_obj
    )


def add_credit_batch(user, amount, subscription=None):
    batch = CreditBatch.objects.create(
        user=user, subscription=subscription, amount=amount, remaining=amount
    )
    CreditTransaction.objects.create(user=user, action='purchase', amount=amount)
    return batch