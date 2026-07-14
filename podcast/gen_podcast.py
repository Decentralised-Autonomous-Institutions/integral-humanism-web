#!/usr/bin/env python3
"""Generate Integral Humanism podcast episodes via ElevenLabs TTS.

Auth: reads ELEVENLABS_API_KEY env var, else ~/.elevenlabs_key file.
Usage:
  python3 gen_podcast.py                 # all 8 episodes (4 EN + 4 HI)
  python3 gen_podcast.py ep1_en ep2_hi   # specific ones
  python3 gen_podcast.py --list-voices
  python3 gen_podcast.py --voice-en George --voice-hi Brian ep1_en
"""
import json, os, sys, subprocess, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, 'scripts')
AUDIO = os.path.join(HERE, 'audio')
TMP = os.path.join(HERE, '.chunks')
os.makedirs(AUDIO, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

API = 'https://api.elevenlabs.io/v1'
MODEL = 'eleven_multilingual_v2'
MAX_CHUNK = 3800
EPS = ['ep1_en', 'ep2_en', 'ep3_en', 'ep4_en', 'ep1_hi', 'ep2_hi', 'ep3_hi', 'ep4_hi']
TITLE = {'ep1': 'Ep1-Whither-Bharat', 'ep2': 'Ep2-The-Integral-Human',
         'ep3': 'Ep3-Society-Chiti-Dharma', 'ep4': 'Ep4-Dharma-State-Economy'}

def key():
    k = os.environ.get('ELEVENLABS_API_KEY')
    if not k:
        p = os.path.expanduser('~/.elevenlabs_key')
        if os.path.exists(p):
            k = open(p).read().strip()
    if not k:
        sys.exit('No API key. Run:  echo "YOUR_KEY" > ~/.elevenlabs_key\n'
                 'or export ELEVENLABS_API_KEY=...')
    return k

def api(path, payload=None, raw=False):
    req = urllib.request.Request(API + path,
        data=json.dumps(payload).encode() if payload else None,
        headers={'xi-api-key': key(), 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read() if raw else json.loads(r.read())

def voices():
    return api('/voices')['voices']

def pick_voice(name, fallback_idx=0):
    vs = voices()
    for v in vs:
        if v['name'].lower() == name.lower():
            return v['voice_id'], v['name']
    for v in vs:
        if v['name'].lower().startswith(name.lower()):
            return v['voice_id'], v['name']
    print(f'! voice "{name}" not found; using "{vs[fallback_idx]["name"]}"')
    return vs[fallback_idx]['voice_id'], vs[fallback_idx]['name']

def chunks_of(text):
    paras = [p.strip() for p in text.split('\n\n') if p.strip()]
    # also treat single newlines as paragraph breaks if giant
    out, cur = [], ''
    for p in paras:
        p = ' '.join(p.split())
        if len(cur) + len(p) + 2 <= MAX_CHUNK:
            cur = (cur + '\n\n' + p) if cur else p
        else:
            if cur: out.append(cur)
            while len(p) > MAX_CHUNK:          # single huge paragraph
                cut = p.rfind('. ', 0, MAX_CHUNK)
                if cut < MAX_CHUNK // 2: cut = MAX_CHUNK
                out.append(p[:cut + 1].strip()); p = p[cut + 1:].strip()
            cur = p
    if cur: out.append(cur)
    return out

def tts(text, voice_id, prev, nxt, out_path):
    payload = {
        'text': text,
        'model_id': MODEL,
        'voice_settings': {'stability': 0.5, 'similarity_boost': 0.75,
                           'style': 0.15, 'use_speaker_boost': True},
    }
    if prev: payload['previous_text'] = prev[-500:]
    if nxt:  payload['next_text'] = nxt[:500]
    import urllib.error
    for attempt in range(8):
        try:
            audio = api(f'/text-to-speech/{voice_id}?output_format=mp3_44100_128',
                        payload, raw=True)
            open(out_path, 'wb').write(audio)
            return
        except urllib.error.HTTPError as e:
            body = ''
            try: body = e.read().decode()[:300]
            except Exception: pass
            wait = min(20 * (attempt + 1), 120)
            print(f'  retry {attempt+1}: HTTP {e.code} {body} (waiting {wait}s)', flush=True)
            time.sleep(wait)
        except Exception as e:
            wait = 15 * (attempt + 1)
            print(f'  retry {attempt+1} after error: {e} (waiting {wait}s)', flush=True)
            time.sleep(wait)
    raise RuntimeError('TTS failed after retries')

def build(ep, voice_id, vname):
    src = os.path.join(SCRIPTS, ep + '.txt')
    text = open(src).read()
    parts = chunks_of(text)
    lang = 'EN' if ep.endswith('_en') else 'HI'
    final = os.path.join(AUDIO, f'Integral-Humanism-{TITLE[ep[:3]]}-{lang}.mp3')
    print(f'{ep}: {len(text)} chars -> {len(parts)} chunks -> {os.path.basename(final)} [voice {vname}]')
    files = []
    for i, part in enumerate(parts):
        cp = os.path.join(TMP, f'{ep}_{i:02d}.mp3')
        if not (os.path.exists(cp) and os.path.getsize(cp) > 1000):
            prev = parts[i-1] if i > 0 else ''
            nxt = parts[i+1] if i+1 < len(parts) else ''
            print(f"  chunk {i+1}/{len(parts)} ({len(part)} chars)", flush=True)
            tts(part, voice_id, prev, nxt, cp)
        files.append(cp)
    lst = os.path.join(TMP, ep + '.txt')
    open(lst, 'w').write('\n'.join(f"file '{f}'" for f in files))
    subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', lst,
                    '-c:a', 'libmp3lame', '-b:a', '128k', final],
                   check=True, capture_output=True)
    dur = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries',
                          'format=duration', '-of', 'csv=p=0', final],
                         capture_output=True, text=True).stdout.strip()
    print(f'  done: {final} ({float(dur)/60:.1f} min)')

if __name__ == '__main__':
    args = [a for a in sys.argv[1:]]
    if '--list-voices' in args:
        for v in voices():
            print(f"{v['voice_id']}  {v['name']}  {v.get('labels',{})}")
        sys.exit(0)
    ven = vhi = None
    if '--voice-en' in args: ven = args[args.index('--voice-en')+1]
    if '--voice-hi' in args: vhi = args[args.index('--voice-hi')+1]
    eps = [a for a in args if a in EPS] or EPS
    id_en, name_en = pick_voice(ven or 'George')
    id_hi, name_hi = pick_voice(vhi or 'Brian')
    total = sum(len(open(os.path.join(SCRIPTS, e + '.txt')).read()) for e in eps)
    print(f'Generating {len(eps)} episodes, ~{total} characters total.')
    for ep in eps:
        build(ep, id_en if ep.endswith('_en') else id_hi,
              name_en if ep.endswith('_en') else name_hi)
    print('All done ->', AUDIO)
