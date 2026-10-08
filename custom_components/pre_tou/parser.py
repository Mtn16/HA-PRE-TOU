"""Parser and calculations for PRE TOU distribution schedules."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
import io
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


def parse_time_cell(val: str) -> str | None:
    """Parse time string or Excel float fraction of day into HH:MM:SS."""
    val = val.strip()
    if not val:
        return None

    # Check for Excel fraction of day (e.g. 0.59375 -> 14:15:00)
    try:
        fval = float(val)
        total_seconds = round(fval * 86400)
        h = (total_seconds // 3600) % 24
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    except ValueError:
        pass

    parts = val.split(":")
    if len(parts) == 3:
        try:
            return f"{int(parts[0]):02d}:{int(parts[1]):02d}:{int(parts[2]):02d}"
        except ValueError:
            return None
    elif len(parts) == 2:
        try:
            return f"{int(parts[0]):02d}:{int(parts[1]):02d}:00"
        except ValueError:
            return None

    return None


def time_str_to_seconds(t_str: str) -> int:
    """Convert HH:MM:SS to seconds from midnight."""
    parts = list(map(int, t_str.split(":")))
    return parts[0] * 3600 + parts[1] * 60 + (parts[2] if len(parts) > 2 else 0)


def seconds_to_time_str(sec: int) -> str:
    """Convert seconds from midnight to HH:MM:SS."""
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def get_easter_sunday(year: int) -> date:
    """Calculate Easter Sunday for a given year using Anonymous Gregorian algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def is_czech_holiday(d: date) -> bool:
    """Check if the given date is a Czech public holiday (státní svátek)."""
    # Fixed-date Czech public holidays
    fixed_holidays = {
        (1, 1),   # Nový rok, Den obnovy samostatného českého státu
        (5, 1),   # Svátek práce
        (5, 8),   # Den vítězství
        (7, 5),   # Den slovanských věrozvěstů Cyrila a Metoděje
        (7, 6),   # Den upálení mistra Jana Husa
        (9, 28),  # Den české státnosti
        (10, 28), # Den vzniku samostatného československého státu
        (11, 17), # Den boje za svobodu a demokracii
        (12, 24), # Štědrý den
        (12, 25), # 1. svátek vánoční
        (12, 26), # 2. svátek vánoční
    }
    if (d.month, d.day) in fixed_holidays:
        return True

    # Movable Easter holidays
    easter = get_easter_sunday(d.year)
    good_friday = easter - timedelta(days=2)
    easter_monday = easter + timedelta(days=1)
    if d == good_friday or d == easter_monday:
        return True

    return False


@dataclass
class ScheduleInterval:
    """An interval when a state is active (Zap / NT)."""

    start_sec: int
    end_sec: int

    @property
    def start_str(self) -> str:
        return seconds_to_time_str(self.start_sec)

    @property
    def end_str(self) -> str:
        return seconds_to_time_str(self.end_sec)

    def to_dict(self) -> dict[str, str]:
        return {
            "start": self.start_str,
            "end": self.end_str,
        }


@dataclass
class DaySchedule:
    """Schedule for all day categories."""

    mon_thu: list[ScheduleInterval] = field(default_factory=list)
    fri: list[ScheduleInterval] = field(default_factory=list)
    sat: list[ScheduleInterval] = field(default_factory=list)
    sun: list[ScheduleInterval] = field(default_factory=list)
    holiday: list[ScheduleInterval] = field(default_factory=list)

    def get_intervals_for_date(self, d: date) -> tuple[list[ScheduleInterval], str]:
        """Get intervals and day type for a specific calendar date."""
        if is_czech_holiday(d):
            # If holiday schedule has intervals, use it. If not (e.g. TD61), use weekday/weekend rule.
            if self.holiday:
                return self.holiday, "Svátek"
            # Fallback for TD61: on Friday use Fri, on weekend use Sat/Sun, else Mon-Thu
            wd = d.weekday()
            if wd == 4:
                return self.fri, "Pátek (Svátek)"
            elif wd == 5:
                return self.sat, "Sobota (Svátek)"
            elif wd == 6:
                return self.sun, "Neděle (Svátek)"
            else:
                return self.mon_thu, "Pracovní den (Svátek)"

        wd = d.weekday()
        if wd in (0, 1, 2, 3):
            return self.mon_thu, "Pondělí - Čtvrtek"
        elif wd == 4:
            return self.fri, "Pátek"
        elif wd == 5:
            return self.sat, "Sobota"
        elif wd == 6:
            return self.sun, "Neděle"
        return self.mon_thu, "Pondělí - Čtvrtek"


@dataclass
class TouItem:
    """Representation of a complete PRE TOU configuration."""

    tou_id: str
    pre_name: str
    tariff_reg: str
    rele1_reg: str
    rele2_reg: str
    usage: str
    tariff_schedule: DaySchedule = field(default_factory=DaySchedule)
    rele1_schedule: DaySchedule = field(default_factory=DaySchedule)
    rele2_schedule: DaySchedule = field(default_factory=DaySchedule)
    rele2_note: str = ""

    @property
    def display_name(self) -> str:
        label = self.tou_id
        if self.pre_name:
            label += f" - {self.pre_name}"
        if self.usage:
            label += f" ({self.usage})"
        return label


def parse_schedule_row(row: list[str], header: list[str]) -> list[ScheduleInterval]:
    """Parse a single schedule row into a list of ScheduleInterval."""
    events: list[tuple[int, str]] = []

    for col_idx in range(12, len(row)):
        if col_idx >= len(header):
            break
        col_type = header[col_idx].strip()
        cell_val = row[col_idx].strip()
        if not cell_val:
            continue
        t_str = parse_time_cell(cell_val)
        if t_str:
            sec = time_to_seconds(t_str)
            events.append((sec, col_type))

    if not events:
        return []

    # Sort events by time
    events.sort(key=lambda x: x[0])

    # Convert 00:00:00 that comes after another time to 86400 (end of day)
    cleaned_events: list[tuple[int, str]] = []
    for idx, (sec, c_type) in enumerate(events):
        if sec == 0 and idx > 0:
            cleaned_events.append((86400, c_type))
        else:
            cleaned_events.append((sec, c_type))

    intervals: list[ScheduleInterval] = []
    current_state = "Vyp"
    current_start = 0

    for sec, c_type in cleaned_events:
        if sec == 0:
            current_state = c_type
            current_start = 0
        else:
            if c_type != current_state:
                if current_state == "Zap":
                    intervals.append(ScheduleInterval(current_start, sec))
                current_state = c_type
                current_start = sec

    if current_state == "Zap" and current_start < 86400:
        intervals.append(ScheduleInterval(current_start, 86400))

    return intervals


def time_to_seconds(t_str: str) -> int:
    return time_str_to_seconds(t_str)


class PreTouDatabase:
    """Database containing parsed PRE TOU entries."""

    def __init__(self) -> None:
        self.items: dict[str, TouItem] = {}

    @classmethod
    def from_csv_string(cls, content: str) -> PreTouDatabase:
        """Parse database from CSV string content."""
        db = cls()
        reader = list(csv.reader(io.StringIO(content)))
        if not reader:
            return db

        # 1. Parse overview table
        overview: dict[str, dict[str, str]] = {}
        i = 0
        while i < len(reader):
            row = reader[i]
            if len(row) >= 5 and row[0].strip() == "ID TOU" and "Registry" not in row:
                i += 1
                while i < len(reader):
                    r = reader[i]
                    if not r or not any(c.strip() for c in r):
                        i += 1
                        continue
                    if len(r) >= 5 and r[0].strip() == "ID TOU":
                        break
                    tid = r[0].strip()
                    if tid:
                        overview[tid] = {
                            "tou_id": tid,
                            "pre_name": r[1].strip() if len(r) > 1 else "",
                            "tariff_reg": r[2].strip() if len(r) > 2 else "",
                            "rele1_reg": r[3].strip() if len(r) > 3 else "",
                            "rele2_reg": r[4].strip() if len(r) > 4 else "",
                            "usage": r[5].strip() if len(r) > 5 else "",
                        }
                    i += 1
            else:
                i += 1

        # 2. Parse detail blocks
        block_starts = [
            idx for idx, r in enumerate(reader)
            if len(r) > 11 and r[0].strip() == "ID TOU" and "Registry" in r
        ]
        block_starts.append(len(reader))

        detail_blocks: dict[str, TouItem] = {}

        for b_idx in range(len(block_starts) - 1):
            start = block_starts[b_idx]
            end = block_starts[b_idx + 1]
            header = reader[start]
            tou_row = reader[start + 1]
            tid = tou_row[0].strip()
            pre_name = tou_row[1].strip()
            tariff_reg = tou_row[11].strip()

            # Separate subsections into Tariff, Relé 1, Relé 2
            # Every block contains 3 subsections with 5 day rows each
            sub_sections: list[list[list[str]]] = []
            current_sub_rows: list[list[str]] = []

            for r_idx in range(start + 2, end):
                r = reader[r_idx]
                if not any(c.strip() for c in r):
                    continue
                # Subsection header check
                col11 = r[11].strip() if len(r) > 11 else ""
                has_rele_marker = (
                    "Relé 1" in col11
                    or "Relé 2" in col11
                    or any("Relé" in c for c in r)
                    or (col11 and col11 in ("261", "262", "263", "586", "7") and len(current_sub_rows) == 5)
                )

                if has_rele_marker:
                    if current_sub_rows:
                        sub_sections.append(current_sub_rows)
                        current_sub_rows = []
                elif len(r) > 2 and r[2].strip() and len(r) > 11 and r[11].strip() and not any(r[c].strip() for c in range(3, 11)):
                    # Intermediate header row with ID and register description (e.g. 28, 488, - existuje...)
                    # Just capture note if present
                    pass
                else:
                    current_sub_rows.append(r)

            if current_sub_rows:
                sub_sections.append(current_sub_rows)

            def make_schedule(rows_list: list[list[str]]) -> DaySchedule:
                sched = DaySchedule()
                if len(rows_list) >= 1:
                    sched.mon_thu = parse_schedule_row(rows_list[0], header)
                if len(rows_list) >= 2:
                    sched.fri = parse_schedule_row(rows_list[1], header)
                if len(rows_list) >= 3:
                    sched.sat = parse_schedule_row(rows_list[2], header)
                if len(rows_list) >= 4:
                    sched.sun = parse_schedule_row(rows_list[3], header)
                if len(rows_list) >= 5:
                    sched.holiday = parse_schedule_row(rows_list[4], header)
                return sched

            tariff_sched = make_schedule(sub_sections[0]) if len(sub_sections) > 0 else DaySchedule()
            rele1_sched = make_schedule(sub_sections[1]) if len(sub_sections) > 1 else DaySchedule()
            rele2_sched = make_schedule(sub_sections[2]) if len(sub_sections) > 2 else DaySchedule()

            rele2_note = ""
            for r_idx in range(start, end):
                line_str = ",".join(reader[r_idx])
                if "Relé 2" in line_str or "vynechat" in line_str:
                    if "vynechat u TOU pro 1F" in line_str:
                        rele2_note = "1F_omit"
                    elif "pouze u 3F" in line_str:
                        rele2_note = "3F_only"

            item = TouItem(
                tou_id=tid,
                pre_name=pre_name,
                tariff_reg=tariff_reg,
                rele1_reg="",
                rele2_reg="",
                usage="",
                tariff_schedule=tariff_sched,
                rele1_schedule=rele1_sched,
                rele2_schedule=rele2_sched,
                rele2_note=rele2_note,
            )
            detail_blocks[tid] = item

        # 3. Combine overview with detail blocks
        # For items that match directly
        for tid, o_info in overview.items():
            matched_item: TouItem | None = None
            if tid in detail_blocks:
                matched_item = detail_blocks[tid]
            else:
                # Match by pre_name
                for det in detail_blocks.values():
                    if det.pre_name and det.pre_name == o_info["pre_name"]:
                        matched_item = det
                        break
                # Match by tariff register
                if not matched_item:
                    for det in detail_blocks.values():
                        if det.tariff_reg and det.tariff_reg == o_info["tariff_reg"]:
                            matched_item = det
                            break

            if matched_item:
                db.items[tid] = TouItem(
                    tou_id=tid,
                    pre_name=o_info["pre_name"] or matched_item.pre_name,
                    tariff_reg=o_info["tariff_reg"] or matched_item.tariff_reg,
                    rele1_reg=o_info["rele1_reg"],
                    rele2_reg=o_info["rele2_reg"],
                    usage=o_info["usage"],
                    tariff_schedule=matched_item.tariff_schedule,
                    rele1_schedule=matched_item.rele1_schedule,
                    rele2_schedule=matched_item.rele2_schedule,
                    rele2_note=matched_item.rele2_note,
                )

        # Also add any detail blocks that were not in the overview table
        for tid, det in detail_blocks.items():
            if tid not in db.items:
                db.items[tid] = det

        return db

    @classmethod
    def from_csv_file(cls, path: str) -> PreTouDatabase:
        """Load database from CSV file path."""
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            return cls.from_csv_string(f.read())

    def get(self, tou_id: str) -> TouItem | None:
        """Get TouItem by ID."""
        return self.items.get(tou_id)

    def list_options(self) -> list[tuple[str, str]]:
        """List options for UI dropdown."""
        return [(tid, item.display_name) for tid, item in sorted(self.items.items())]


def calculate_schedule_state(
    schedule: DaySchedule,
    now_dt: datetime,
    days_ahead: int = 8,
) -> dict[str, Any]:
    """Calculate current active state, next switch ON time, and next switch OFF time.

    Used for Tariff (where active = NT, inactive = VT) or Relays (active = ON, inactive = OFF).
    """
    raw_timeline: list[tuple[datetime, bool]] = []
    start_date = now_dt.date()

    for day_offset in range(days_ahead):
        curr_d = start_date + timedelta(days=day_offset)
        intervals, _ = schedule.get_intervals_for_date(curr_d)
        d_midnight = datetime.combine(curr_d, time(0, 0, 0), tzinfo=now_dt.tzinfo)

        # Check if day starts active at 00:00:00
        starts_active = any(iv.start_sec == 0 for iv in intervals)
        raw_timeline.append((d_midnight, starts_active))

        for iv in intervals:
            if iv.start_sec > 0:
                raw_timeline.append(
                    (d_midnight + timedelta(seconds=iv.start_sec), True)
                )
            if iv.end_sec < 86400:
                raw_timeline.append(
                    (d_midnight + timedelta(seconds=iv.end_sec), False)
                )

    # Clean transitions (remove consecutive identical states)
    clean_timeline: list[tuple[datetime, bool]] = []
    for dt_val, state in raw_timeline:
        if not clean_timeline or clean_timeline[-1][1] != state:
            clean_timeline.append((dt_val, state))

    # Current state at now_dt
    is_active = False
    for dt_val, state in clean_timeline:
        if dt_val <= now_dt:
            is_active = state
        else:
            break

    # Next start (transition to True)
    next_start: datetime | None = None
    for dt_val, state in clean_timeline:
        if dt_val > now_dt and state is True:
            next_start = dt_val
            break

    # Next end (transition to False)
    next_end: datetime | None = None
    for dt_val, state in clean_timeline:
        if dt_val > now_dt and state is False:
            next_end = dt_val
            break

    # Closest upcoming transition
    next_transition: datetime | None = None
    for dt_val, _ in clean_timeline:
        if dt_val > now_dt:
            next_transition = dt_val
            break

    today_intervals, day_type = schedule.get_intervals_for_date(start_date)
    tomorrow_intervals, _ = schedule.get_intervals_for_date(
        start_date + timedelta(days=1)
    )

    return {
        "is_active": is_active,
        "next_start": next_start,
        "next_end": next_end,
        "next_transition": next_transition,
        "today_intervals": [iv.to_dict() for iv in today_intervals],
        "tomorrow_intervals": [iv.to_dict() for iv in tomorrow_intervals],
        "is_holiday": is_czech_holiday(start_date),
        "day_type": day_type,
    }
