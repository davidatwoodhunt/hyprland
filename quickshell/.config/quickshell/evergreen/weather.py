#!/usr/bin/env python3
"""NYC Open-Meteo feed, cached between requests and shell restarts (stdlib only)."""
import argparse
from datetime import datetime, timedelta
import json
import math
import os
from pathlib import Path
import signal
import tempfile
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ZONE = ZoneInfo('America/New_York')
REFRESH_SECONDS = 15 * 60
PARAMS = {
    'latitude': 40.7128, 'longitude': -74.0060,
    'timezone': 'America/New_York', 'temperature_unit': 'fahrenheit', 'wind_speed_unit': 'mph',
    'current': 'temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,is_day',
    'daily': 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
    'forecast_days': 4,
}
URL = 'https://api.open-meteo.com/v1/forecast?' + urlencode(PARAMS)
CACHE_KEY = 'nyc-imperial-v1'


def condition(code, is_day=True):
    if code == 0:
        return ('Clear', '☀' if is_day else '☾')
    if code in (1, 2):
        return ('Mostly clear' if code == 1 else 'Partly cloudy', '☁')
    if code == 3:
        return ('Overcast', '☁')
    if code in (45, 48):
        return ('Fog', '≋')
    if code in (51, 53, 55, 56, 57):
        return ('Drizzle' if code < 56 else 'Freezing drizzle', '☂')
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return ('Freezing rain' if code in (66, 67) else 'Rain', '☂')
    if code in (71, 73, 75, 77, 85, 86):
        return ('Snow', '❄')
    if code in (95, 96, 99):
        return ('Thunderstorm', 'ϟ')
    return ('Unknown conditions', '·')


def numeric(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Missing or invalid weather value')
    return value


def validate(raw):
    if raw.get('timezone') != 'America/New_York':
        raise ValueError('Unexpected forecast timezone')
    current, units = raw['current'], raw['current_units']
    daily, daily_units = raw['daily'], raw['daily_units']
    if any(units.get(k) != '°F' for k in ('temperature_2m', 'apparent_temperature')):
        raise ValueError('Expected Fahrenheit temperatures')
    if units.get('wind_speed_10m') not in ('mp/h', 'mph'):
        raise ValueError('Expected miles-per-hour wind speed')
    if units.get('relative_humidity_2m') != '%':
        raise ValueError('Expected humidity percentage')
    for key in ('temperature_2m_max', 'temperature_2m_min'):
        if daily_units.get(key) != '°F':
            raise ValueError('Expected Fahrenheit forecast')
    if daily_units.get('precipitation_probability_max') != '%':
        raise ValueError('Expected precipitation probability percentage')
    for key in ('temperature_2m', 'apparent_temperature', 'relative_humidity_2m', 'weather_code', 'wind_speed_10m', 'is_day'):
        numeric(current[key])
    datetime.fromisoformat(current['time'])
    dates = daily['time']
    if len(dates) < 4 or dates != sorted(set(dates)):
        raise ValueError('Expected four ordered forecast dates')
    for day in dates:
        datetime.fromisoformat(day)
    for key in ('weather_code', 'temperature_2m_max', 'temperature_2m_min', 'precipitation_probability_max'):
        if len(daily[key]) != len(dates):
            raise ValueError('Inconsistent forecast arrays')
        for value in daily[key]:
            numeric(value)
    if not 0 <= current['relative_humidity_2m'] <= 100 or any(not 0 <= v <= 100 for v in daily['precipitation_probability_max']):
        raise ValueError('Percentage out of range')
    return raw


def fetch():
    request = Request(URL, headers={'User-Agent': 'EvergreenDesktopWeather/1.0', 'Accept': 'application/json'})
    with urlopen(request, timeout=15) as response:
        return validate(json.load(response))


def load_cache(path):
    try:
        state = json.loads(path.read_text())
        if state.get('key') != CACHE_KEY:
            return {}
        if state.get('response'):
            validate(state['response'])
            numeric(state['updated'])
        numeric(state['attempted'])
        return state
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def save_cache(path, state):
    # Atomic replacement leaves the last complete response intact after interruption.
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            json.dump(state, output, allow_nan=False)
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def view(state, now=None):
    now = now or datetime.now(ZONE)
    today = now.astimezone(ZONE).date()
    updated = state.get('updated')
    result = {
        'available': bool(state.get('response')), 'offline': bool(state.get('offline', False)),
        'stale': bool(updated and now.timestamp() - updated > REFRESH_SECONDS * 2),
        'updated': datetime.fromtimestamp(updated, ZONE).strftime('%b %d · %I:%M %p %Z') if updated else '',
        'refreshSeconds': REFRESH_SECONDS, 'today': None, 'forecast': [],
    }
    if not result['available']:
        return result
    raw = state['response']
    c = raw['current']
    label, icon = condition(c['weather_code'], bool(c['is_day']))
    result['current'] = {'temperature': c['temperature_2m'], 'feels': c['apparent_temperature'],
                         'wind': c['wind_speed_10m'], 'humidity': c['relative_humidity_2m'],
                         'condition': label, 'icon': icon}
    daily = raw['daily']
    by_date = {}
    for i, date in enumerate(daily['time']):
        parsed = datetime.fromisoformat(date).date()
        label, icon = condition(daily['weather_code'][i])
        by_date[parsed] = {'date': date, 'day': parsed.strftime('%a'), 'label': parsed.strftime('%b %d'),
                           'high': daily['temperature_2m_max'][i], 'low': daily['temperature_2m_min'][i],
                           'precipitation': daily['precipitation_probability_max'][i], 'condition': label, 'icon': icon}
    result['today'] = by_date.get(today)
    # Today's range is shown separately; the three forecast cards are the next days.
    for offset in range(1, 4):
        day = today + timedelta(days=offset)
        result['forecast'].append(by_date.get(day, {'date': day.isoformat(), 'day': day.strftime('%a'),
                                                   'label': day.strftime('%b %d'), 'icon': '·', 'condition': 'Unavailable'}))
    return result


def refresh(state, path, fetcher=fetch, now=None):
    real_time = now is None
    now = time.time() if real_time else now
    if 0 <= now - state.get('attempted', 0) < REFRESH_SECONDS:
        return state
    next_state = dict(state, key=CACHE_KEY, attempted=now)
    try:
        response = fetcher()
        validate(response)
        next_state.update(response=response, updated=time.time() if real_time else now, offline=False)
    except (OSError, ValueError, KeyError, TypeError):
        next_state['offline'] = True
    try:
        save_cache(path, next_state)
    except OSError:
        # Read-only/full cache storage must not discard usable data in memory.
        pass
    return next_state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--offline', action='store_true', help='Read cached data only; make no network request')
    parser.add_argument('--cache', type=Path, default=Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'evergreen-weather/nyc.json')
    args = parser.parse_args()
    state = load_cache(args.cache)
    if args.offline:
        print(json.dumps(view(dict(state, offline=True)), allow_nan=False), flush=True)
        return
    # Show a cached result immediately, without waiting for DNS or TLS.
    if not args.once and state.get('response'):
        print(json.dumps(view(state), allow_nan=False), flush=True)
    while True:
        state = refresh(state, args.cache)
        print(json.dumps(view(state), allow_nan=False), flush=True)
        if args.once:
            return
        delay = max(1, min(REFRESH_SECONDS, state.get('attempted', time.time()) + REFRESH_SECONDS - time.time()))
        time.sleep(delay)


if __name__ == '__main__':
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()
