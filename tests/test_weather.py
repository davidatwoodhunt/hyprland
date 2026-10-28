"""Offline checks for the weather cache, failure handling and NYC date boundaries."""
import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

MODULE = Path(__file__).resolve().parents[1] / 'quickshell/.config/quickshell/evergreen/weather.py'
spec = importlib.util.spec_from_file_location('weather', MODULE)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def response():
    return {
        'timezone': 'America/New_York',
        'current': {'temperature_2m': 68.0, 'apparent_temperature': 66.2,
                    'relative_humidity_2m': 70, 'weather_code': 0, 'wind_speed_10m': 6.2,
                    'is_day': 1, 'time': '2026-10-27T20:00'},
        'current_units': {'temperature_2m': '°F', 'apparent_temperature': '°F',
                          'relative_humidity_2m': '%', 'wind_speed_10m': 'mp/h'},
        'daily': {'time': ['2026-10-27', '2026-10-28', '2026-10-29', '2026-10-30'],
                  'weather_code': [0, 3, 61, 71], 'temperature_2m_max': [70, 68, 66, 60],
                  'temperature_2m_min': [50, 49, 48, 40], 'precipitation_probability_max': [10, 20, 80, 70]},
        'daily_units': {'temperature_2m_max': '°F', 'temperature_2m_min': '°F', 'precipitation_probability_max': '%'},
    }


class WeatherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name) / 'nyc.json'

    def test_success_is_cached_and_preserves_units(self):
        fetch = Mock(return_value=response())
        state = w.refresh({}, self.cache, fetch, now=10000)
        self.assertEqual(w.load_cache(self.cache), state)
        self.assertEqual(state['response']['current']['temperature_2m'], 68)
        self.assertFalse(state['offline'])
        self.assertEqual(w.PARAMS['temperature_unit'], 'fahrenheit')
        self.assertEqual(w.PARAMS['wind_speed_unit'], 'mph')
        self.assertEqual(w.PARAMS['timezone'], 'America/New_York')
        self.assertEqual(w.REFRESH_SECONDS, 900)

    def test_reloads_and_redraws_do_not_refetch_before_900_seconds(self):
        fetch = Mock(return_value=response())
        w.refresh({}, self.cache, fetch, now=10000)
        for now in (10001, 10100, 10899):
            w.refresh(w.load_cache(self.cache), self.cache, fetch, now=now)
        self.assertEqual(fetch.call_count, 1)
        w.refresh(w.load_cache(self.cache), self.cache, fetch, now=10900)
        self.assertEqual(fetch.call_count, 2)

    def test_network_failure_keeps_last_success_and_backs_off(self):
        state = w.refresh({}, self.cache, lambda: response(), now=10000)
        failed = Mock(side_effect=OSError('Network unreachable'))
        state = w.refresh(state, self.cache, failed, now=10900)
        self.assertTrue(state['offline'])
        self.assertEqual(state['updated'], 10000)
        self.assertEqual(state['response'], response())
        self.assertTrue(w.view(state)['available'])
        w.refresh(w.load_cache(self.cache), self.cache, failed, now=10901)
        self.assertEqual(failed.call_count, 1)

    def test_cold_start_offline_is_explicit(self):
        state = w.refresh({}, self.cache, Mock(side_effect=OSError('offline')), now=10000)
        self.assertFalse(w.view(state)['available'])
        self.assertTrue(w.view(state)['offline'])
        self.assertEqual(w.view(state)['updated'], '')

    def test_bad_units_or_json_never_replace_good_cache(self):
        state = w.refresh({}, self.cache, lambda: response(), now=10000)
        bad = copy.deepcopy(response())
        bad['current_units']['temperature_2m'] = '°C'
        state = w.refresh(state, self.cache, lambda: bad, now=10900)
        self.assertTrue(state['offline'])
        self.assertEqual(state['updated'], 10000)
        self.assertEqual(state['response'], response())
        state = w.refresh(state, self.cache, Mock(side_effect=json.JSONDecodeError('bad', 'x', 0)), now=11800)
        self.assertEqual(state['response'], response())
        self.cache.write_text('{broken')
        self.assertEqual(w.load_cache(self.cache), {})

    def test_dates_use_nyc_even_after_utc_midnight(self):
        state = {'response': response(), 'updated': 10000}
        view = w.view(state, datetime(2026, 10, 28, 0, 30, tzinfo=timezone.utc))
        self.assertEqual(view['today']['date'], '2026-10-27')
        self.assertEqual([d['date'] for d in view['forecast']], ['2026-10-28', '2026-10-29', '2026-10-30'])

    def test_old_forecast_is_not_relabeled_as_today(self):
        view = w.view({'response': response(), 'updated': 10000}, datetime(2026, 11, 3, 12, tzinfo=w.ZONE))
        self.assertIsNone(view['today'])
        self.assertTrue(view['stale'])
        self.assertTrue(all('high' not in day for day in view['forecast']))

    def test_update_timestamp_observes_dst(self):
        for utc_hour, suffix in ((5, 'EDT'), (6, 'EST')):
            timestamp = datetime(2026, 11, 1, utc_hour, 30, tzinfo=timezone.utc).timestamp()
            self.assertTrue(w.view({'updated': timestamp})['updated'].endswith(suffix))


if __name__ == '__main__':
    unittest.main()
