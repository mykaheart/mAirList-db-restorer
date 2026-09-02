import requests
import time
import utils

MB_MIN_INTERVAL = 1.05
DISCOGS_MIN_INTERVAL = 1.0
_last_mb_request = 0.0
_last_discogs_request = 0.0
LABEL_CODE_CACHE = {}

def _wait(min_interval, last_time):
    elapsed = time.time() - last_time
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    return time.time()

def mb_get(url, params, timeout=5):
    global _last_mb_request
    _last_mb_request = _wait(MB_MIN_INTERVAL, _last_mb_request)
    res = requests.get(url, headers=utils.HEADERS, params=params, timeout=timeout)
    _last_mb_request = time.time()
    return res

def discogs_get(url, params, timeout=5):
    global _last_discogs_request
    _last_discogs_request = _wait(DISCOGS_MIN_INTERVAL, _last_discogs_request)
    res = requests.get(url, headers=utils.HEADERS, params=params, timeout=timeout)
    _last_discogs_request = time.time()
    return res

def fetch_label_code_from_musicbrainz(label_name):
    if not label_name: return ""
    clean_label = label_name.split('/')[0].strip()
    if clean_label in LABEL_CODE_CACHE: return LABEL_CODE_CACHE[clean_label]
    try:
        res = mb_get("https://musicbrainz.org/ws/2/label/", {'query': f'label:"{clean_label}"', 'fmt': 'json', 'limit': 3})
        if res.status_code == 200:
            for l in res.json().get('labels', []):
                code = l.get('label-code')
                if code:
                    flc = f"LC{str(code).zfill(5)}"
                    LABEL_CODE_CACHE[clean_label] = flc
                    return flc
    except Exception: pass
    return ""

def fetch_label_code_from_discogs_release(release_id):
    if not release_id: return ""
    try:
        res = discogs_get(f"https://api.discogs.com/releases/{release_id}", {'key': utils.DISCOGS_KEY, 'secret': utils.DISCOGS_SECRET})
        if res.status_code == 200:
            for l in res.json().get('labels', []):
                lc = utils.extract_label_code_from_string(l.get('catno', '')) or utils.extract_label_code_from_string(l.get('name', ''))
                if lc: return lc
    except Exception: pass
    return ""

def suggest_artist_spelling(artist):
    if not artist: return None
    main_artist = artist.split('feat.')[0].strip() if 'feat.' in artist else artist
    
    if main_artist.lower() in utils.ARTIST_FIXES:
        res_art = utils.ARTIST_FIXES[main_artist.lower()]
        if 'feat.' in artist: return f"{res_art} feat.{artist.split('feat.')[1]}"
        return res_art
        
    try:
        res = mb_get("https://musicbrainz.org/ws/2/artist/", {'query': main_artist, 'fmt': 'json', 'limit': 5})
        if res.status_code == 200:
            for top_match in res.json().get('artists', []):
                score = int(top_match.get('score', 0))
                official_name = top_match.get('name', '')
                if score >= 90 and official_name and utils.string_similarity(main_artist, official_name) >= 0.7:
                    if official_name.lower() != main_artist.lower():
                        if 'feat.' in artist: return f"{official_name} feat.{artist.split('feat.')[1]}"
                        return official_name
    except Exception: pass
    return None

def suggest_title_spelling(artist, title, local_duration_sec=0):
    if not title or not artist: return None
    try:
        search_title = utils.get_pure_search_title(title)
        res = mb_get("https://musicbrainz.org/ws/2/recording/",
                      {'query': f'artist:"{artist}" AND recording:"{search_title}"', 'fmt': 'json', 'limit': 10})
        if res.status_code == 200:
            recordings = res.json().get('recordings', [])
            if not recordings: return None
            
            if local_duration_sec > 0:
                best_match = None
                smallest_diff = 9999
                for rec in recordings:
                    rec_len = rec.get('length')
                    if rec_len:
                        rec_sec = int(rec_len) / 1000.0
                        diff = abs(rec_sec - local_duration_sec)
                        if diff <= 18 and diff < smallest_diff:
                            smallest_diff = diff
                            best_match = rec.get('title')
                
                if best_match and best_match.lower() != title.lower():
                    return best_match

            official_title = recordings[0].get('title', '')
            if official_title and official_title.lower() != title.lower():
                return official_title
    except Exception: pass
    return None

def fetch_musicbrainz_details(artist, title, target_year=None, target_album=None, local_duration_sec=0):
    years, isrc, orig_album, fallback_album = [], None, None, None
    best_score = 0
    try:
        query = f'artist:"{artist}" AND recording:"{utils.get_pure_search_title(title)}"'
        if target_album: query += f' AND release:"{target_album}"'
        if target_year: query += f' AND date:{target_year}'

        res = mb_get("https://musicbrainz.org/ws/2/recording/",
                      {'query': query, 'fmt': 'json', 'limit': 10, 'inc': 'isrcs+releases'})
        if res.status_code == 200:
            recordings = res.json().get('recordings', [])
            
            if local_duration_sec > 0 and recordings:
                for rec in recordings:
                    rec_len = rec.get('length')
                    if rec_len:
                        diff = abs(int(rec_len)/1000.0 - local_duration_sec)
                        if diff <= 18:
                            best_score = max(best_score, 95)
            
            if recordings and best_score == 0:
                best_score = int(recordings[0].get('score', 0))
                
            relevant = [r for r in recordings if int(r.get('score', 0)) >= max(best_score - 15, 50) or (local_duration_sec > 0 and r.get('length') and abs(int(r.get('length',0))/1000.0 - local_duration_sec) <= 18)]
            
            for rec in relevant:
                if not isrc and rec.get('isrcs'): isrc = rec.get('isrcs')[0]
                if rec.get('first-release-date', '')[:4]: years.append(rec.get('first-release-date')[:4])
                for rel in sorted(rec.get('releases', []), key=lambda x: x.get('date', '9999') if x.get('date') else '9999'):
                    if rel.get('date', '')[:4]: years.append(rel.get('date')[:4])
                    rel_title = rel.get('title', '')
                    if rel_title and not utils.contains_non_latin(rel_title):
                        if not fallback_album: fallback_album = rel_title
                        if not orig_album and utils.is_valid_album(rel_title): orig_album = rel_title
    except Exception: pass

    confidence = "hoch" if best_score >= 90 else ("mittel" if best_score >= 70 else "niedrig")
    year = utils.filter_valid_years(years)
    
    # NEU: Das leere Feld für die Sprache als 5. Parameter angehängt!
    return year, confidence, isrc, (orig_album or fallback_album or ""), ""

def fetch_discogs_details(artist, title, target_year=None, target_album=None):
    years, mapped_genre, discogs_id, styles_list = [], None, "", []
    label, label_code, orig_album, fallback_album = "", "", "", ""
    confidence = "niedrig"
    try:
        pure_title = utils.get_pure_search_title(title)
        
        # NEU: Master Release in der primären Suche priorisieren
        params = {'artist': artist, 'track': pure_title, 'type': 'master', 'key': utils.DISCOGS_KEY, 'secret': utils.DISCOGS_SECRET, 'per_page': 15}
        
        if target_album: params['release_title'] = target_album
        if target_year: params['year'] = target_year

        res = discogs_get("https://api.discogs.com/database/search", params, timeout=8)
        results = res.json().get('results', []) if res.status_code == 200 else []

        # Fallback 1: Falls Ziel-Album/Jahr nicht gefunden wurde ODER es kein Master-Release gibt
        if not results:
            params_fb = {'artist': artist, 'track': pure_title, 'key': utils.DISCOGS_KEY, 'secret': utils.DISCOGS_SECRET, 'per_page': 15}
            res = discogs_get("https://api.discogs.com/database/search", params_fb, timeout=8)
            results = res.json().get('results', []) if res.status_code == 200 else []

        # Fallback 2: Grobe Freitext-Suche (falls Felder durcheinander sind)
        if not results:
            res_fb = discogs_get("https://api.discogs.com/database/search",
                                 {'q': f"{artist} {pure_title}", 'key': utils.DISCOGS_KEY, 'secret': utils.DISCOGS_SECRET, 'per_page': 15}, timeout=8)
            results = res_fb.json().get('results', []) if res_fb.status_code == 200 else []

        if results:
            search_list = sorted([r for r in results if str(r.get('year', '')).isdigit()], key=lambda x: int(x.get('year'))) or results
            for r in search_list:
                if str(r.get('year', '')).isdigit() and int(r.get('year')) > 1900:
                    years.append(str(r.get('year')))
                rel_title = r.get('title', '').split(' - ', 1)[1] if ' - ' in r.get('title', '') else r.get('title', '')
                if rel_title and not utils.contains_non_latin(rel_title):
                    if not fallback_album: fallback_album = rel_title
                    if not orig_album and utils.is_valid_album(rel_title): orig_album = rel_title
            
            best = search_list[0]
            discogs_id = str(best.get('id', ''))
            styles_list = best.get('style', [])
            mapped_genre = utils.map_to_allowed_genre(best.get('genre', []), styles_list)
            labels = best.get('label', [])
            label = labels[0] if labels else ""
            label_code = utils.extract_label_code_from_string(label) or utils.extract_label_code_from_string(best.get('catno', ''))
            
            if not label_code and label: label_code = fetch_label_code_from_musicbrainz(label)
            if not label_code and discogs_id: label_code = fetch_label_code_from_discogs_release(discogs_id)
            
            best_title = best.get('title', '').lower()
            sim_score = utils.string_similarity(pure_title, best_title)
            if pure_title.lower() in best_title or sim_score >= 0.8:
                confidence = "hoch"
            elif results and sim_score >= 0.5:
                confidence = "mittel"
    except Exception: pass
    return {
        'years': years, 'genre': mapped_genre, 'discogs_id': discogs_id,
        'style': ", ".join(styles_list) if styles_list else "", 'label': label,
        'label_code': label_code, 'album': orig_album or fallback_album or "",
        'confidence': confidence,
    }