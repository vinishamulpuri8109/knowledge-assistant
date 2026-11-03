"""SQLAlchemy engine/session setup and seed data for service records."""
from datetime import date
from functools import lru_cache

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine():
    settings = get_settings()
    return create_engine(f"sqlite:///{settings.sqlite_path}", connect_args={"check_same_thread": False})


def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db():
    """FastAPI dependency: one session per request."""
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


# Synthetic but realistic records. M-102 (an XYZ-200) has a recurring overheating history.
SEED_RECORDS = [
    ("SR-1001", "M-102", "XYZ-200", "Spindle motor overheating during long production runs", "E104",
     "Cooling fan intake clogged with metal dust; motor temperature reached 92°C", "Cleaned fan intake, replaced air filter", date(2025, 3, 14)),
    ("SR-1002", "M-101", "XYZ-200", "Unexpected stop with hydraulic pressure alarm", "E210",
     "Hydraulic pressure dropped below 45 bar due to a worn pump seal", "Replaced pump seal and topped up hydraulic fluid", date(2025, 4, 2)),
    ("SR-1003", "M-102", "XYZ-200", "Machine overheating and shutting down after 3 hours", "E104",
     "Coolant level low; coolant pump delivering 40% below rated flow", "Refilled coolant, replaced coolant pump impeller", date(2025, 6, 21)),
    ("SR-1004", "M-103", "ABC-100", "Conveyor belt misalignment causing product jams", "E302",
     "Belt tracking roller loose", "Realigned belt and torqued roller bolts to 25 Nm", date(2025, 7, 8)),
    ("SR-1005", "M-104", "XYZ-300", "Excessive vibration at high spindle speed", "E115",
     "Spindle bearing wear detected by vibration analysis", "Replaced front spindle bearings", date(2025, 7, 30)),
    ("SR-1006", "M-101", "XYZ-200", "Control panel display flickering", None,
     "Loose ribbon cable between HMI and controller", "Reseated and secured display cable", date(2025, 8, 12)),
    ("SR-1007", "M-105", "ABC-100", "Motor overheating on conveyor drive", "E104",
     "Gearbox lubricant degraded, increasing motor load", "Drained and replaced gearbox oil", date(2025, 9, 3)),
    ("SR-1008", "M-102", "XYZ-200", "Temperature sensor reading erratic values", "E107",
     "Thermocouple connector corroded", "Replaced spindle thermocouple and connector", date(2025, 9, 25)),
    ("SR-1009", "M-106", "XYZ-300", "Emergency stop triggered without operator input", "E001",
     "Faulty E-stop contact block", "Replaced E-stop contact block and tested safety circuit", date(2025, 10, 10)),
    ("SR-1010", "M-104", "XYZ-300", "Lubrication system low pressure warning", "E220",
     "Clogged lubrication line filter", "Replaced inline filter, purged lubrication lines", date(2025, 11, 5)),
    ("SR-1011", "M-103", "ABC-100", "Photoelectric sensor not detecting parts", "E305",
     "Sensor lens contaminated with oil mist", "Cleaned lens and adjusted sensitivity", date(2026, 1, 17)),
    ("SR-1012", "M-102", "XYZ-200", "Recurring E104 alarm after coolant service", "E104",
     "Coolant radiator fins blocked, reducing heat exchange", "Cleaned radiator fins; scheduled monthly radiator inspection", date(2026, 2, 9)),
]


def init_db() -> None:
    """Create tables and insert seed records if the table is empty."""
    from app import models  # noqa: F401  (registers models with Base)

    engine = get_engine()
    Base.metadata.create_all(engine)
    with get_sessionmaker()() as db:
        if db.scalar(select(func.count()).select_from(models.ServiceRecord)) == 0:
            db.add_all(
                models.ServiceRecord(
                    service_id=r[0], equipment_id=r[1], equipment_model=r[2], issue_description=r[3],
                    error_code=r[4], diagnosis=r[5], resolution=r[6], service_date=r[7],
                )
                for r in SEED_RECORDS
            )
            db.commit()
