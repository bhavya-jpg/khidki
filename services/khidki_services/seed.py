"""The demo school. Fictional: no real school, teacher or child is represented anywhere."""

from __future__ import annotations

from dataclasses import dataclass, field

from khidki_core.schemas import RoomParams


@dataclass(frozen=True)
class RoomConfig:
    room_id: str
    name: str
    grade: int
    params: RoomParams
    sensitive_count: int = 0
    pe_period: int | None = None
    tier: int = 2  # 0: no sensor, 1: CO₂, 2: CO₂ + PM2.5
    frame_paint: str = "green"


@dataclass(frozen=True)
class SchoolConfig:
    school_id: str
    name: str
    lat: float
    lon: float
    nearest_station: str
    rooms: tuple[RoomConfig, ...] = field(default_factory=tuple)
    max_changes: int = 6

    def room(self, room_id: str) -> RoomConfig:
        for r in self.rooms:
            if r.room_id == room_id:
                return r
        raise KeyError(room_id)


DEMO_SCHOOL = SchoolConfig(
    school_id="dsv",
    name="Demo Sarvodaya Vidyalaya (fictional), East Delhi",
    lat=28.6469,
    lon=77.3152,
    nearest_station="Anand Vihar, Delhi - DPCC",
    rooms=(
        RoomConfig(
            "6B", "Class 6B", 6, RoomParams(students=44, has_purifier=False), sensitive_count=3, pe_period=6
        ),
        RoomConfig(
            "3A",
            "Class 3A",
            3,
            RoomParams(students=38, has_purifier=True),
            sensitive_count=1,
            pe_period=3,
            frame_paint="blue",
        ),
    ),
)
