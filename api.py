import requests
import threading
import time
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
import utils

MB_MIN_INTERVAL = 1.05
DISCOGS_MIN_INTERVAL = 1.0
ACOUSTICBRAINZ_MIN_INTERVAL = 1.05
API_MAX_ATTEMPTS = 3
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

_last_mb_request = 0.0
_last_discogs_request = 0.0
_last_acousticbrainz_request = 0.0
_mb_lock = threading.Lock()
_discogs_lock = threading.Lock()
_acousticbrainz_lock = threading.Lock()
LABEL_CODE_CACHE = {}


class APIRequestError(RuntimeError):
    """Raised after a remote API request failed permanently for this attempt."""

    def __init__(self, message, service='', kind='api', status_code=None, retry_after=None):
        super().__init__(message)
        self.service = service
        self.kind = kind
        self.status_code = status_code
        self.retry_after = retry_after


def _wait(min_interval, last_time):
    elapsed = time.monotonic() - last_time
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    return time.monotonic()


def _log_api_error(context, exc=None, status_code=None):
    details = context
    if status_code is not None:
        details += f" (HTTP {status_code})"
    if exc is not None:
        details += f": {exc}"
    utils.log_change("API_ERROR", details)


def _response_retry_after(response):
    """Return a server-advertised retry delay in seconds, if present."""
    if response is None:
        return None

    raw = response.headers.get('Retry-After')
    if raw:
        try:
            return max(0.0, float(raw))
        except (TypeError, ValueError):
            try:
                target = parsedate_to_datetime(raw)
                if target.tzinfo is None:
                    target = target.replace(tzinfo=timezone.utc)
                return max(0.0, (target - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass

    raw = response.headers.get('X-RateLimit-Reset-In')
    if raw:
        try:
            return max(0.0, float(raw))
        except (TypeError, ValueError):
            pass
    return None


def _retry_delay(response, attempt):
    server_delay = _response_retry_after(response)
    if server_delay is not None:
        return server_delay
    return min(8.0, 1.5 * attempt)


def _respect_acousticbrainz_rate_headers(response):
    """Honor AcousticBrainz' dynamic rate-limit window when headers are present."""
    try:
        remaining = int(response.headers.get('X-RateLimit-Remaining', ''))
        reset_in = float(response.headers.get('X-RateLimit-Reset-In', ''))
    except (TypeError, ValueError):
        return
    if remaining <= 0 and reset_in > 0:
        time.sleep(reset_in + 0.05)


def _request_with_retry(service, url, params, timeout, min_interval, lock, last_request_name):
    global _last_mb_request, _last_discogs_request, _last_acousticbrainz_request

    last_error = None
    for attempt in range(1, API_MAX_ATTEMPTS + 1):
        with lock:
            if last_request_name == 'mb':
                _last_mb_request = _wait(min_interval, _last_mb_request)
            elif last_request_name == 'discogs':
                _last_discogs_request = _wait(min_interval, _last_discogs_request)
            else:
                _last_acousticbrainz_request = _wait(min_interval, _last_acousticbrainz_request)

        response = None
        try:
            response = requests.get(url, headers=utils.HEADERS, params=params, timeout=timeout)
        except requests.RequestException as exc:
            last_error = exc
            _log_api_error(f"{service} request failed (attempt {attempt}/{API_MAX_ATTEMPTS})", exc=exc)
            if attempt < API_MAX_ATTEMPTS:
                time.sleep(_retry_delay(None, attempt))
                continue
            raise APIRequestError(
                f"{service}: Netzwerkfehler nach {API_MAX_ATTEMPTS} Versuchen: {exc}",
                service=service, kind='network'
            ) from exc
        except Exception as exc:
            _log_api_error(f"{service} unexpected request error", exc=exc)
            raise APIRequestError(
                f"{service}: unerwarteter Request-Fehler: {exc}",
                service=service, kind='unexpected'
            ) from exc

        if response.status_code < 400:
            if service == 'AcousticBrainz':
                _respect_acousticbrainz_rate_headers(response)
            return response

        _log_api_error(
            f"{service} request returned an error (attempt {attempt}/{API_MAX_ATTEMPTS})",
            status_code=response.status_code
        )

        if response.status_code in RETRY_STATUS_CODES and attempt < API_MAX_ATTEMPTS:
            time.sleep(_retry_delay(response, attempt))
            continue

        if response.status_code in RETRY_STATUS_CODES:
            kind = 'rate_limit' if response.status_code == 429 else 'server'
            raise APIRequestError(
                f"{service}: HTTP {response.status_code} nach {API_MAX_ATTEMPTS} Versuchen",
                service=service, kind=kind, status_code=response.status_code,
                retry_after=_response_retry_after(response)
            )

        # 4xx errors such as bad credentials or malformed requests are not transient.
        raise APIRequestError(
            f"{service}: HTTP {response.status_code}",
            service=service, kind='http', status_code=response.status_code
        )

    raise APIRequestError(
        f"{service}: Anfrage fehlgeschlagen: {last_error or 'unbekannter Fehler'}",
        service=service, kind='api'
    )


def mb_get(url, params, timeout=5):
    return _request_with_retry(
        'MusicBrainz', url, params, timeout,
        MB_MIN_INTERVAL, _mb_lock, 'mb'
    )


def discogs_get(url, params, timeout=5):
    return _request_with_retry(
        'Discogs', url, params, timeout,
        DISCOGS_MIN_INTERVAL, _discogs_lock, 'discogs'
    )


def acousticbrainz_get(url, params=None, timeout=8):
    return _request_with_retry(
        'AcousticBrainz', url, params or {}, timeout,
        ACOUSTICBRAINZ_MIN_INTERVAL, _acousticbrainz_lock, 'acousticbrainz'
    )


def fetch_label_code_from_musicbrainz(label_name):
    """Optional lookup: a failure here must not invalidate an otherwise good track match."""
    if not label_name:
        return ""
    clean_label = label_name.split('/')[0].strip()
    if clean_label in LABEL_CODE_CACHE:
        return LABEL_CODE_CACHE[clean_label]
    try:
        res = mb_get(
            "https://musicbrainz.org/ws/2/label/",
            {'query': f'label:"{clean_label}"', 'fmt': 'json', 'limit': 3}
        )
        for label in res.json().get('labels', []):
            code = label.get('label-code')
            if code:
                formatted = f"LC{str(code).zfill(5)}"
                LABEL_CODE_CACHE[clean_label] = formatted
                return formatted
    except Exception as exc:
        _log_api_error(f"Optional MusicBrainz label lookup failed for '{clean_label}'", exc=exc)
        # Do not cache technical failures; a later track/run should be able to retry.
        return ""

    # A successful lookup without a code can safely be cached.
    LABEL_CODE_CACHE[clean_label] = ""
    return ""


def fetch_label_code_from_discogs_release(release_id):
    """Optional lookup: missing label codes do not make the primary metadata match invalid."""
    if not release_id:
        return ""
    try:
        res = discogs_get(
            f"https://api.discogs.com/releases/{release_id}",
            {'key': utils.DISCOGS_KEY, 'secret': utils.DISCOGS_SECRET}
        )
        for label in res.json().get('labels', []):
            code = (
                utils.extract_label_code_from_string(label.get('catno', ''))
                or utils.extract_label_code_from_string(label.get('name', ''))
            )
            if code:
                return code
    except Exception as exc:
        _log_api_error(f"Optional Discogs release lookup failed for ID {release_id}", exc=exc)
    return ""


def resolve_discogs_release_id(entity_id, entity_type):
    """Return a real Discogs release ID. Master IDs are resolved via main_release."""
    if not entity_id:
        return ""
    if str(entity_type).lower() != 'master':
        return str(entity_id)
    try:
        res = discogs_get(
            f"https://api.discogs.com/masters/{entity_id}",
            {'key': utils.DISCOGS_KEY, 'secret': utils.DISCOGS_SECRET}
        )
        main_release = res.json().get('main_release')
        return str(main_release) if main_release else ""
    except Exception as exc:
        # Resolution is helpful for label-code details but not essential for the
        # Discogs search result itself, so keep the primary result usable.
        _log_api_error(f"Optional Discogs master lookup failed for ID {entity_id}", exc=exc)
        return ""


def suggest_artist_spelling(artist):
    if not artist:
        return None
    main_artist = artist.split('feat.')[0].strip() if 'feat.' in artist else artist

    if main_artist.lower() in utils.ARTIST_FIXES:
        result_artist = utils.ARTIST_FIXES[main_artist.lower()]
        if 'feat.' in artist:
            return f"{result_artist} feat.{artist.split('feat.')[1]}"
        return result_artist

    try:
        res = mb_get(
            "https://musicbrainz.org/ws/2/artist/",
            {'query': main_artist, 'fmt': 'json', 'limit': 5}
        )
        for top_match in res.json().get('artists', []):
            score = int(top_match.get('score', 0))
            official_name = top_match.get('name', '')
            if score >= 90 and official_name and utils.string_similarity(main_artist, official_name) >= 0.7:
                if official_name.lower() != main_artist.lower():
                    if 'feat.' in artist:
                        return f"{official_name} feat.{artist.split('feat.')[1]}"
                    return official_name
    except Exception as exc:
        _log_api_error(f"Artist spelling lookup failed for '{main_artist}'", exc=exc)
        raise
    return None


def suggest_title_spelling(artist, title, local_duration_sec=0):
    if not title or not artist:
        return None
    try:
        search_title = utils.get_pure_search_title(title)
        res = mb_get(
            "https://musicbrainz.org/ws/2/recording/",
            {'query': f'artist:"{artist}" AND recording:"{search_title}"', 'fmt': 'json', 'limit': 10}
        )
        recordings = res.json().get('recordings', [])
        if not recordings:
            return None

        if local_duration_sec > 0:
            best_match = None
            smallest_diff = 9999
            for rec in recordings:
                rec_len = rec.get('length')
                score = int(rec.get('score', 0))
                if rec_len and score >= 70:
                    rec_sec = int(rec_len) / 1000.0
                    diff = abs(rec_sec - local_duration_sec)
                    if diff <= 18 and diff < smallest_diff:
                        smallest_diff = diff
                        best_match = rec.get('title')

            if best_match and best_match.lower() != title.lower():
                return best_match

        official_title = recordings[0].get('title', '')
        if int(recordings[0].get('score', 0)) >= 85 and official_title and official_title.lower() != title.lower():
            return official_title
    except Exception as exc:
        _log_api_error(f"Title spelling lookup failed for '{artist} - {title}'", exc=exc)
        raise
    return None


def fetch_musicbrainz_details(artist, title, target_year=None, target_album=None, local_duration_sec=0):
    years, isrc, orig_album, fallback_album = [], None, None, None
    best_score = 0
    duration_match = False
    try:
        query = f'artist:"{artist}" AND recording:"{utils.get_pure_search_title(title)}"'
        if target_album:
            query += f' AND release:"{target_album}"'
        if target_year:
            query += f' AND date:{target_year}'

        res = mb_get(
            "https://musicbrainz.org/ws/2/recording/",
            {'query': query, 'fmt': 'json', 'limit': 10, 'inc': 'isrcs+releases'}
        )
        recordings = res.json().get('recordings', [])
        if recordings:
            best_score = max(int(rec.get('score', 0)) for rec in recordings)

        if local_duration_sec > 0:
            for rec in recordings:
                rec_len = rec.get('length')
                score = int(rec.get('score', 0))
                if rec_len and score >= 70:
                    diff = abs(int(rec_len) / 1000.0 - local_duration_sec)
                    if diff <= 18:
                        duration_match = True
                        break

        relevant = []
        threshold = max(best_score - 15, 50)
        for rec in recordings:
            score = int(rec.get('score', 0))
            rec_len = rec.get('length')
            close_duration = False
            if local_duration_sec > 0 and rec_len and score >= 70:
                close_duration = abs(int(rec_len) / 1000.0 - local_duration_sec) <= 18
            if score >= threshold or close_duration:
                relevant.append(rec)

        for rec in relevant:
            if not isrc and rec.get('isrcs'):
                isrc = rec.get('isrcs')[0]
            if rec.get('first-release-date', '')[:4]:
                years.append(rec.get('first-release-date')[:4])
            for rel in sorted(
                rec.get('releases', []),
                key=lambda x: x.get('date', '9999') if x.get('date') else '9999'
            ):
                if rel.get('date', '')[:4]:
                    years.append(rel.get('date')[:4])
                rel_title = rel.get('title', '')
                if rel_title and not utils.contains_non_latin(rel_title):
                    if not fallback_album:
                        fallback_album = rel_title
                    if not orig_album and utils.is_valid_album(rel_title):
                        orig_album = rel_title
    except Exception as exc:
        _log_api_error(f"MusicBrainz detail lookup failed for '{artist} - {title}'", exc=exc)
        raise

    if local_duration_sec > 0:
        confidence = "hoch" if best_score >= 90 and duration_match else ("mittel" if best_score >= 75 or duration_match else "niedrig")
    else:
        confidence = "hoch" if best_score >= 95 else ("mittel" if best_score >= 80 else "niedrig")

    year = utils.filter_valid_years(years)

    # MusicBrainz does not provide a reliable recording-language value here.
    # The empty fifth return value intentionally keeps manual language review intact.
    return year, confidence, isrc, (orig_album or fallback_album or ""), ""



def _clean_isrc(value):
    import re
    clean = re.sub(r'[^A-Za-z0-9]', '', str(value or '')).upper()
    return clean if len(clean) == 12 else ''


def _artist_credit_text(recording):
    parts = []
    for credit in recording.get('artist-credit', []) or []:
        name = credit.get('name') or (credit.get('artist') or {}).get('name') or ''
        if name:
            parts.append(name)
        joinphrase = credit.get('joinphrase') or ''
        if joinphrase:
            parts.append(joinphrase)
    return ''.join(parts).strip()


def _normalize_match_text(value):
    import re
    text = str(value or '').casefold()
    text = re.sub(r'[´`‘’]', "'", text)
    text = re.sub(r'\b(featuring|feat\.?|ft\.?)\b', ' feat ', text)
    text = re.sub(r'[^a-z0-9à-öø-ÿ]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def _similarity(a, b):
    return utils.string_similarity(_normalize_match_text(a), _normalize_match_text(b))


def _safe_recording_candidate(recording, artist, title, local_duration_sec=0, via_isrc=False):
    rec_title = recording.get('title', '')
    rec_artist = _artist_credit_text(recording)
    title_sim = _similarity(title, rec_title)
    artist_sim = _similarity(artist, rec_artist) if rec_artist else 0.0
    rec_len = recording.get('length')
    duration_diff = None
    if rec_len and local_duration_sec and float(local_duration_sec) > 0:
        try:
            duration_diff = abs(float(rec_len) / 1000.0 - float(local_duration_sec))
        except (TypeError, ValueError):
            duration_diff = None

    if via_isrc:
        if title_sim < 0.72 or artist_sim < 0.60:
            return None
        if duration_diff is not None and duration_diff > 30:
            return None
        search_score = 100
    else:
        try:
            search_score = int(recording.get('score', 0))
        except (TypeError, ValueError):
            search_score = 0
        if search_score < 90 or title_sim < 0.88 or artist_sim < 0.78:
            return None
        if local_duration_sec and float(local_duration_sec) > 0:
            if duration_diff is None or duration_diff > 18:
                return None
        elif search_score < 95 or title_sim < 0.95 or artist_sim < 0.88:
            return None

    return {
        'mbid': str(recording.get('id', '')).strip(),
        'title': rec_title,
        'artist': rec_artist,
        'score': search_score,
        'title_similarity': title_sim,
        'artist_similarity': artist_sim,
        'duration_diff': duration_diff,
        'matched_by': 'ISRC' if via_isrc else 'Artist/Title',
    }


def find_musicbrainz_recording_for_bpm(artist, title, isrc='', local_duration_sec=0):
    """Return a conservative MusicBrainz recording match for BPM lookup, or None.

    ISRC lookup is preferred. Without ISRC, title/artist, MusicBrainz score and
    duration must all agree closely. This function never guesses between versions.
    """
    artist = str(artist or '').strip()
    title = str(title or '').strip()
    if not artist or not title:
        return None

    clean_isrc = _clean_isrc(isrc)
    recordings = []
    via_isrc = False
    if clean_isrc:
        try:
            # Use recording search rather than /isrc/<code>: an unknown but
            # syntactically valid ISRC then yields an empty result instead of a
            # 404, allowing a safe Artist/Title fallback.
            res = mb_get(
                "https://musicbrainz.org/ws/2/recording/",
                {'query': f'isrc:{clean_isrc}', 'fmt': 'json', 'limit': 10}
            )
            recordings = res.json().get('recordings', []) or []
            via_isrc = bool(recordings)
        except APIRequestError:
            raise
        except Exception as exc:
            _log_api_error(f"MusicBrainz ISRC lookup failed for '{clean_isrc}'", exc=exc)

    if not recordings:
        safe_artist = artist.replace('\\', '\\\\').replace('"', '\\"')
        safe_title = title.replace('\\', '\\\\').replace('"', '\\"')
        res = mb_get(
            "https://musicbrainz.org/ws/2/recording/",
            {'query': f'artist:"{safe_artist}" AND recording:"{safe_title}"', 'fmt': 'json', 'limit': 10}
        )
        recordings = res.json().get('recordings', []) or []
        via_isrc = False

    candidates = []
    for rec in recordings:
        match = _safe_recording_candidate(rec, artist, title, local_duration_sec, via_isrc=via_isrc)
        if match and match['mbid']:
            candidates.append(match)

    if not candidates:
        return None

    def sort_key(match):
        diff = match['duration_diff'] if match['duration_diff'] is not None else 9999.0
        return (
            1 if match['matched_by'] == 'ISRC' else 0,
            match['score'],
            match['title_similarity'] + match['artist_similarity'],
            -diff,
        )

    candidates.sort(key=sort_key, reverse=True)
    best = candidates[0]

    # If two non-ISRC candidates are virtually tied but point at different
    # recordings, refuse to guess.
    if not via_isrc and len(candidates) > 1:
        second = candidates[1]
        if (
            best['score'] - second['score'] <= 2
            and abs((best['duration_diff'] or 0) - (second['duration_diff'] or 0)) <= 2
            and abs((best['title_similarity'] + best['artist_similarity']) - (second['title_similarity'] + second['artist_similarity'])) <= 0.03
        ):
            return None
    return best


def _cluster_bpm_values(values, tolerance=2.5):
    clean = []
    for value in values:
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if 30 <= value <= 300:
            clean.append(value)
    values = sorted(clean)
    clusters = []
    for value in values:
        placed = False
        for cluster in clusters:
            center = sum(cluster) / len(cluster)
            if abs(value - center) <= tolerance:
                cluster.append(value)
                placed = True
                break
        if not placed:
            clusters.append([value])
    clusters.sort(key=lambda c: (len(c), -((max(c)-min(c)) if len(c)>1 else 0)), reverse=True)
    return clusters


def select_acousticbrainz_bpm(values):
    """Choose a conservative BPM consensus from AcousticBrainz submissions.

    A single valid submission is accepted. With multiple submissions, at least
    two must agree within 2.5 BPM; otherwise the recording is treated as ambiguous.
    """
    clusters = _cluster_bpm_values(values)
    if not clusters:
        return None
    if sum(len(c) for c in clusters) == 1:
        value = clusters[0][0]
        return {'bpm': int(value + 0.5), 'agree': 1, 'total': 1}
    best = clusters[0]
    total = sum(len(c) for c in clusters)
    if len(best) < 2:
        return None
    # For 3+ submissions, require a real majority to avoid 86/172-style
    # half/double-time ambiguity.
    if total >= 3 and len(best) <= total / 2:
        return None
    median = sorted(best)[len(best)//2] if len(best) % 2 else sum(sorted(best)[len(best)//2-1:len(best)//2+1]) / 2
    return {'bpm': int(median + 0.5), 'agree': len(best), 'total': total}


def fetch_acousticbrainz_bpms(recording_mbids, max_submissions=3, include_status=False):
    """Fetch BPM-only low-level data for MusicBrainz recording IDs.

    By default returns {mbid: {'bpm', 'agree', 'total'}} for recordings with a
    safe BPM consensus. With include_status=True it returns (result, status),
    where status classifies missing data, ambiguous analyses and per-chunk API
    failures without aborting the entire maintenance scan.
    """
    mbids = []
    for mbid in recording_mbids:
        text = str(mbid or '').strip().lower()
        if text and text not in mbids:
            mbids.append(text)
    if not mbids:
        return ({}, {}) if include_status else {}

    status = {mbid: {'status': 'pending'} for mbid in mbids}
    counts = {}
    failed_mbids = set()

    for start in range(0, len(mbids), 25):
        chunk = mbids[start:start+25]
        try:
            res = acousticbrainz_get(
                'https://acousticbrainz.org/api/v1/count',
                {'recording_ids': ';'.join(chunk)}
            )
            data = res.json()
        except APIRequestError as exc:
            for mbid in chunk:
                failed_mbids.add(mbid)
                status[mbid] = {
                    'status': 'api_error',
                    'kind': getattr(exc, 'kind', 'api'),
                    'http_status': getattr(exc, 'status_code', None),
                    'message': str(exc),
                }
            continue
        except Exception as exc:
            for mbid in chunk:
                failed_mbids.add(mbid)
                status[mbid] = {
                    'status': 'api_error', 'kind': 'unexpected',
                    'http_status': None, 'message': str(exc),
                }
            continue

        for mbid in chunk:
            try:
                counts[mbid] = max(0, int((data.get(mbid) or {}).get('count', 0)))
            except (TypeError, ValueError):
                counts[mbid] = 0
            if counts[mbid] <= 0:
                status[mbid] = {'status': 'no_data'}

    requested = []
    for mbid in mbids:
        if mbid in failed_mbids:
            continue
        count = counts.get(mbid, 0)
        if count <= 0:
            continue
        if count <= max_submissions:
            offsets = list(range(count))
        elif max_submissions >= 3:
            offsets = sorted({0, count // 2, count - 1})[:max_submissions]
        else:
            offsets = list(range(max_submissions))
        for offset in offsets:
            requested.append(f'{mbid}:{offset}')

    values = {mbid: [] for mbid in mbids}
    for start in range(0, len(requested), 25):
        chunk = requested[start:start+25]
        chunk_mbids = {token.split(':', 1)[0] for token in chunk}
        try:
            res = acousticbrainz_get(
                'https://acousticbrainz.org/api/v1/low-level',
                {
                    'recording_ids': ';'.join(chunk),
                    'features': 'rhythm.bpm',
                }
            )
            data = res.json()
        except APIRequestError as exc:
            for mbid in chunk_mbids:
                failed_mbids.add(mbid)
                status[mbid] = {
                    'status': 'api_error',
                    'kind': getattr(exc, 'kind', 'api'),
                    'http_status': getattr(exc, 'status_code', None),
                    'message': str(exc),
                }
            continue
        except Exception as exc:
            for mbid in chunk_mbids:
                failed_mbids.add(mbid)
                status[mbid] = {
                    'status': 'api_error', 'kind': 'unexpected',
                    'http_status': None, 'message': str(exc),
                }
            continue

        for key, offsets in data.items():
            if key == 'mbid_mapping' or key not in values or not isinstance(offsets, dict):
                continue
            for document in offsets.values():
                if not isinstance(document, dict):
                    continue
                bpm = (document.get('rhythm') or {}).get('bpm')
                try:
                    bpm = float(bpm)
                except (TypeError, ValueError):
                    continue
                if 30 <= bpm <= 300:
                    values[key].append(bpm)

    result = {}
    for mbid in mbids:
        if mbid in failed_mbids:
            continue
        count = counts.get(mbid, 0)
        if count <= 0:
            continue
        bpm_values = values.get(mbid, [])
        if not bpm_values:
            status[mbid] = {'status': 'no_bpm', 'submissions': count}
            continue
        selected = select_acousticbrainz_bpm(bpm_values)
        if selected:
            result[mbid] = selected
            status[mbid] = {
                'status': 'ok',
                'agree': selected['agree'],
                'total': selected['total'],
                'submissions': count,
            }
        else:
            status[mbid] = {
                'status': 'ambiguous',
                'sampled': len(bpm_values),
                'submissions': count,
            }

    return (result, status) if include_status else result

def fetch_discogs_details(artist, title, target_year=None, target_album=None):
    years, mapped_genre, discogs_id, styles_list = [], None, "", []
    label, label_code, orig_album, fallback_album = "", "", "", ""
    confidence = "niedrig"
    try:
        pure_title = utils.get_pure_search_title(title)

        params = {
            'artist': artist, 'track': pure_title, 'type': 'master',
            'key': utils.DISCOGS_KEY, 'secret': utils.DISCOGS_SECRET, 'per_page': 15
        }
        if target_album:
            params['release_title'] = target_album
        if target_year:
            params['year'] = target_year

        search_mode = 'master'
        res = discogs_get("https://api.discogs.com/database/search", params, timeout=8)
        results = res.json().get('results', [])

        if not results:
            search_mode = 'structured'
            params_fb = {
                'artist': artist, 'track': pure_title,
                'key': utils.DISCOGS_KEY, 'secret': utils.DISCOGS_SECRET, 'per_page': 15
            }
            if target_album:
                params_fb['release_title'] = target_album
            if target_year:
                params_fb['year'] = target_year
            res = discogs_get("https://api.discogs.com/database/search", params_fb, timeout=8)
            results = res.json().get('results', [])

        if not results:
            search_mode = 'free'
            res_fb = discogs_get(
                "https://api.discogs.com/database/search",
                {
                    'q': f"{artist} {pure_title}", 'key': utils.DISCOGS_KEY,
                    'secret': utils.DISCOGS_SECRET, 'per_page': 15
                },
                timeout=8
            )
            results = res_fb.json().get('results', [])

        if results:
            # Keep Discogs relevance order for the selected result. Years are collected
            # separately and filtered later instead of sorting the result list by year.
            search_list = results
            for result in search_list:
                if str(result.get('year', '')).isdigit() and int(result.get('year')) > 1900:
                    years.append(str(result.get('year')))
                rel_title = result.get('title', '').split(' - ', 1)[1] if ' - ' in result.get('title', '') else result.get('title', '')
                if rel_title and not utils.contains_non_latin(rel_title):
                    if not fallback_album:
                        fallback_album = rel_title
                    if not orig_album and utils.is_valid_album(rel_title):
                        orig_album = rel_title

            best = search_list[0]
            entity_id = str(best.get('id', ''))
            entity_type = str(best.get('type', 'release')).lower()
            release_id = resolve_discogs_release_id(entity_id, entity_type)
            discogs_id = release_id if entity_type == 'master' and release_id else entity_id

            styles_list = best.get('style', [])
            mapped_genre = utils.map_to_allowed_genre(best.get('genre', []), styles_list)
            labels = best.get('label', [])
            label = labels[0] if labels else ""
            label_code = (
                utils.extract_label_code_from_string(label)
                or utils.extract_label_code_from_string(best.get('catno', ''))
            )

            if not label_code and label:
                label_code = fetch_label_code_from_musicbrainz(label)
            if not label_code and release_id:
                label_code = fetch_label_code_from_discogs_release(release_id)

            result_title = best.get('title', '')
            result_artist = result_title.split(' - ', 1)[0] if ' - ' in result_title else ''
            artist_similarity = utils.string_similarity(artist, result_artist) if result_artist else 0.0

            if search_mode != 'free' and artist_similarity >= 0.9:
                confidence = "hoch"
            elif search_mode != 'free' and artist_similarity >= 0.7:
                confidence = "mittel"
            elif search_mode == 'free' and artist_similarity >= 0.8:
                confidence = "mittel"

            # A targeted live re-fetch gets an extra confidence boost when its
            # user-supplied year/album is also reflected by the selected result.
            best_year = str(best.get('year', ''))
            best_album = result_title.split(' - ', 1)[1] if ' - ' in result_title else result_title
            targeted_match = False
            if target_year and best_year == str(target_year):
                targeted_match = True
            if target_album and utils.string_similarity(target_album, best_album) >= 0.8:
                targeted_match = True
            if targeted_match and confidence == "mittel":
                confidence = "hoch"
    except Exception as exc:
        _log_api_error(f"Discogs detail lookup failed for '{artist} - {title}'", exc=exc)
        raise

    return {
        'years': years,
        'genre': mapped_genre,
        'discogs_id': discogs_id,
        'style': ", ".join(styles_list) if styles_list else "",
        'label': label,
        'label_code': label_code,
        'album': orig_album or fallback_album or "",
        'confidence': confidence,
    }
