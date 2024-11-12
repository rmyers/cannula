from ..core.database import User as DBUser
from ._generated import PersonaType, UserType, AdminType


class User(UserType):
    """User instance"""

    @classmethod
    def from_db(cls, db_user: DBUser) -> "User":
        """Constructor for creating user from db object"""
        return cls(
            id=db_user.id,
            name=db_user.name,
            email=db_user.email,
        )


class Admin(AdminType):
    """Admin instance"""

    @classmethod
    def from_db(cls, db_user: DBUser) -> "Admin":
        """Constructor for creating admin from db object"""
        return cls(
            id=db_user.id,
            name=db_user.name,
            email=db_user.email,
        )


def persona(db_user: DBUser) -> PersonaType:
    # Check the `is_admin` field and return the correct Persona
    if db_user.is_admin:
        return Admin.from_db(db_user)
    return User.from_db(db_user)
