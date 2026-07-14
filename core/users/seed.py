import logging
from core.users.models import User  # Example import

logger = logging.getLogger(__name__)

def seed_data():
    """
    Idempotent function to seed data for the core.users domain.
    """
    logger.info("Seeding core.users...")
    
    # Example logic (Must be idempotent!)
    # user, created = User.objects.get_or_create(
    #     email="admin@aethyrtech.com",
    #     defaults={"is_staff": True, "is_superuser": True}
    # )
    # if created:
    #     user.set_password("adminpass123")
    #     user.save()
    
    logger.info("Finished seeding core.users.")
