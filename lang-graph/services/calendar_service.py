import logging
import os
import pickle
import re
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HOURS_RE = re.compile(r"^([A-Za-z]+)-([A-Za-z]+)\s+(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$")

_WEEKDAY_INDEX = {
    "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3,
    "Fri": 4, "Sat": 5, "Sun": 6,
}


def parse_business_hours(hours_str: str) -> Optional[Dict[str, object]]:
    """Parse strings like 'Mon-Sat 9:00-18:00' into {open_days, open_time, close_time}."""
    if not hours_str:
        return None
    match = _HOURS_RE.match(hours_str.strip())
    if not match:
        return None
    start_day, end_day, oh, om, ch, cm = match.groups()
    if start_day not in _WEEKDAY_INDEX or end_day not in _WEEKDAY_INDEX:
        return None
    start_idx = _WEEKDAY_INDEX[start_day]
    end_idx = _WEEKDAY_INDEX[end_day]
    if start_idx <= end_idx:
        open_days = set(range(start_idx, end_idx + 1))
    else:
        open_days = set(range(start_idx, 7)) | set(range(0, end_idx + 1))
    return {
        "open_days": open_days,
        "open_time": time(int(oh), int(om)),
        "close_time": time(int(ch), int(cm)),
    }


def is_valid_day(day_str: str, hours_str: str, tz: str = "UTC") -> Tuple[bool, str]:
    if not day_str or not _DAY_RE.match(day_str):
        return False, "Please use the format YYYY-MM-DD."
    try:
        day = datetime.strptime(day_str, "%Y-%m-%d").date()
    except ValueError:
        return False, "That doesn't look like a real date."
    today = datetime.now(ZoneInfo(tz)).date()
    if day < today:
        return False, "That date is in the past. Please pick a future date."
    parsed = parse_business_hours(hours_str)
    if parsed is None:
        return True, ""
    if day.weekday() not in parsed["open_days"]:
        return False, "We're closed that day. Please pick another."
    return True, ""


def _windows_overlap(a_start: datetime, a_end: datetime,
                     b_start: datetime, b_end: datetime) -> bool:
    return not (a_end <= b_start or a_start >= b_end)


class CalendarService:
    """Wraps Google Calendar API for slot discovery + transactional event create/delete."""

    SLOT_STEP_MINUTES = 30  # candidate start times every 30 min

    def __init__(self, calendar_id: str, credentials_path: str = "credentials.json",
                 token_path: str = "token.pickle"):
        self._calendar_id = calendar_id
        self._credentials_path = credentials_path
        self._token_path = token_path
        self._service = self._build_service()

    def _build_service(self):
        creds: Optional[Credentials] = None
        if os.path.exists(self._token_path):
            with open(self._token_path, "rb") as f:
                creds = pickle.load(f)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self._credentials_path, CALENDAR_SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(self._token_path, "wb") as f:
                pickle.dump(creds, f)

        return build("calendar", "v3", credentials=creds)

    # ---- event listing -----------------------------------------------------

    def _list_events_for_day(self, day: datetime, tz: ZoneInfo) -> List[Dict[str, datetime]]:
        day_start = datetime.combine(day.date(), time(0, 0)).replace(tzinfo=tz)
        day_end = day_start + timedelta(days=1)

        result = self._service.events().list(
            calendarId=self._calendar_id,
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events: List[Dict[str, datetime]] = []
        for ev in result.get("items", []):
            start = ev["start"].get("dateTime") or ev["start"].get("date")
            end = ev["end"].get("dateTime") or ev["end"].get("date")
            if not start or not end:
                continue
            events.append({
                "start": datetime.fromisoformat(start).astimezone(tz),
                "end": datetime.fromisoformat(end).astimezone(tz),
            })
        return events

    # ---- free-slot computation --------------------------------------------

    def get_free_slots(self, day_str: str, duration_min: int,
                       hours_str: str, tz: str = "UTC") -> List[Dict[str, str]]:
        """Return start times whose [start, start+duration) window is free."""
        parsed = parse_business_hours(hours_str)
        if parsed is None:
            return []

        zone = ZoneInfo(tz)
        day = datetime.strptime(day_str, "%Y-%m-%d")
        open_dt = datetime.combine(day.date(), parsed["open_time"]).replace(tzinfo=zone)
        close_dt = datetime.combine(day.date(), parsed["close_time"]).replace(tzinfo=zone)
        duration = timedelta(minutes=duration_min)

        events = self._list_events_for_day(day, zone)

        candidates: List[Dict[str, str]] = []
        candidate = open_dt
        step = timedelta(minutes=self.SLOT_STEP_MINUTES)
        now_zone = datetime.now(zone)

        while candidate + duration <= close_dt:
            if candidate < now_zone:
                candidate += step
                continue
            window_end = candidate + duration
            if not any(_windows_overlap(candidate, window_end, ev["start"], ev["end"])
                       for ev in events):
                candidates.append({
                    "start_iso": candidate.isoformat(),
                    "start_label": candidate.strftime("%H:%M"),
                    "end_label": window_end.strftime("%H:%M"),
                })
            candidate += step

        return candidates

    def is_slot_free(self, start_iso: str, duration_min: int, tz: str = "UTC") -> bool:
        zone = ZoneInfo(tz)
        start = datetime.fromisoformat(start_iso).astimezone(zone)
        end = start + timedelta(minutes=duration_min)
        events = self._list_events_for_day(start, zone)
        return not any(_windows_overlap(start, end, ev["start"], ev["end"]) for ev in events)

    # ---- mutating ops -----------------------------------------------------

    def create_event(self, start_iso: str, duration_min: int,
                     summary: str, description: str = "", tz: str = "UTC") -> str:
        zone = ZoneInfo(tz)
        start = datetime.fromisoformat(start_iso).astimezone(zone)
        end = start + timedelta(minutes=duration_min)
        body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start.isoformat(), "timeZone": tz},
            "end": {"dateTime": end.isoformat(), "timeZone": tz},
        }
        created = self._service.events().insert(
            calendarId=self._calendar_id, body=body
        ).execute()
        return created["id"]

    def delete_event(self, event_id: str) -> None:
        try:
            self._service.events().delete(
                calendarId=self._calendar_id, eventId=event_id
            ).execute()
        except Exception as e:  # pragma: no cover - best-effort cleanup
            logger.warning("Failed to delete calendar event %s: %s", event_id, e)
