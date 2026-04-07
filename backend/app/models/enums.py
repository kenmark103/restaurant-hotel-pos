from enum import StrEnum


class UserType(StrEnum):
    STAFF = "staff"
    CUSTOMER = "customer"


class AuthProvider(StrEnum):
    LOCAL = "local"
    GOOGLE = "google"


class Role(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    CASHIER = "cashier"
    SERVER = "server"
    KITCHEN = "kitchen"


class StaffStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"
