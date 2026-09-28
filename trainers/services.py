from finance.models import TrainerWallet


def promote_trainer(trainer):
    """
    Ensure a trainer has the correct role and wallet.
    """
    if trainer.user and trainer.user.role != "trainer":
        trainer.user.role = "trainer"
        trainer.user.save(update_fields=["role"])

    TrainerWallet.objects.get_or_create(trainer=trainer)
    return trainer
