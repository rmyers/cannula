from cannula.contrib.orm import DBMixin

from ..core.database import User as DBUser
from ._generated import PersonaType, UserTypeBase, AdminTypeBase


class User(UserTypeBase, DBMixin[DBUser]):
    """User instance"""


class Admin(AdminTypeBase, DBMixin[DBUser]):
    """Admin instance"""


def persona(db_user: DBUser) -> PersonaType:
    # Check the `is_admin` field and return the correct Persona
    if db_user.is_admin:
        return Admin.from_db(db_user)
    return User.from_db(db_user)
