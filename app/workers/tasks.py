
"""Background tasks for EnergyMax."""

from celery import shared_task


@shared_task(
    name="energymax.health_check",
    ignore_result=False,
)
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "energymax-celery",
    }
