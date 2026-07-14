#!/usr/bin/env python3
"""Generate Integral Humanism podcast episodes via Smallest.ai (lightning-v3.1).

Auth: SMALLEST_API_KEY env var, else ~/.smallest_key.
Usage:
  python3 gen_smallest.py                       # all 8 episodes
  python3 gen_smallest.py ep1_en ep3_hi         # specific ones
  python3 gen_smallest.py --voice-en blofeld --voice-hi kartik ep1_en
API returns raw PCM s16le 24kHz mono; chunks are byte-concatenated then
encoded once to MP3 with homebrew ffmpeg.
"""
import json, os, sys, subprocess, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, 'scripts')
AUDIO = os.path.join(HERE, 'audio')
TMP = os.path.join(HERE, '.schunks')
os.makedirs(AUDIO, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

API = 'https://waves-api.smallest.ai/api/v1/lightning-v3.1/get_speech'
FFMPEG = '/opt/homebrew/bin/ffmpeg'
SR = 24000
MAX_CHUNK = 3600
EPS = ['ep1_en', 'ep2_en', 'ep3_en', 'ep4_en', 'ep1_hi', 'ep2_hi', 'ep3_hi', 'ep4_hi']
TITLE = {'ep1': 'Ep1-Whither-Bharat', 'ep2': 'Ep2-The-Integral-Human',
         'ep3': 'Ep3-Society-Chiti-Dharma', 'ep4': 'Ep4-Dharma-State-Economy'}
VOICE_EN, VOICE_HI = 'kartik', 'kartik'

def key():
    k = os.environ.get('SMALLEST_API_KEY')
    if not k:
        p = os.path.expanduser('~/.smallest_key')
        if os.path.exists(p): k = open(p).read().strip()
    if not k: sys.exit('No key: echo KEY > ~/.smallest_key')
    return k

def chunks_of(text):
    paras = [' '.join(p.split()) for p in text.split('\n\n') if p.strip()]
    out, cur = [], ''
    for p in paras:
        if len(cur) + len(p) + 2 <= MAX_CHUNK:
            cur = (cur + '\n\n' + p) if cur else p
        else:
            if cur: out.append(cur)
            while len(p) > MAX_CHUNK:
                cut = p.rfind('. ', 0, MAX_CHUNK)
                if cut < MAX_CHUNK // 2: cut = MAX_CHUNK
                out.append(p[:cut + 1].strip()); p = p[cut + 1:].strip()
            cur = p
    if cur: out.append(cur)
    return out

def tts(text, voice, out_path):
    payload = {'text': text, 'voice_id': voice, 'sample_rate': SR, 'speed': 1.0}
    for attempt in range(8):
        try:
            req = urllib.request.Request(API, data=json.dumps(payload).encode(),
                headers={'Authorization': 'Bearer ' + key(),
                         'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=300) as r:
                pcm = r.read()
            if len(pcm) < 2000:
                raise RuntimeError('suspiciously small response: %r' % pcm[:200])
            open(out_path, 'wb').write(pcm)
            return
        except urllib.error.HTTPError as e:
            body = ''
            try: body = e.read().decode()[:300]
            except Exception: pass
            wait = min(15 * (attempt + 1), 90)
            print(f'  retry {attempt+1}: HTTP {e.code} {body} ({wait}s)', flush=True)
            time.sleep(wait)
        except Exception as e:
            wait = 10 * (attempt + 1)
            print(f'  retry {attempt+1}: {e} ({wait}s)', flush=True)
            time.sleep(wait)
    raise RuntimeError('TTS failed after retries')

def build(ep, voice):
    text = open(os.path.join(SCRIPTS, ep + '.txt')).read()
    parts = chunks_of(text)
    lang = 'EN' if ep.endswith('_en') else 'HI'
    final = os.path.join(AUDIO, f'Integral-Humanism-{TITLE[ep[:3]]}-{lang}.mp3')
    print(f'{ep}: {len(text)} chars -> {len(parts)} chunks [{voice}]', flush=True)
    pcm_all = b''
    for i, part in enumerate(parts):
        cp = os.path.join(TMP, f'{ep}_{i:02d}.pcm')
        if not (os.path.exists(cp) and os.path.getsize(cp) > 2000):
            print(f'  chunk {i+1}/{len(parts)} ({len(part)} chars)', flush=True)
            tts(part, voice, cp)
        pcm_all += open(cp, 'rb').read()
        pcm_all += b'\x00' * int(SR * 2 * 0.45)   # 450ms pause between chunks
    raw = os.path.join(TMP, ep + '.pcm')
    open(raw, 'wb').write(pcm_all)
    subprocess.run([FFMPEG, '-y', '-v', 'error', '-f', 's16le', '-ar', str(SR),
                    '-ac', '1', '-i', raw, '-c:a', 'libmp3lame', '-b:a', '128k',
                    final], check=True)
    os.remove(raw)
    print(f'  done: {final} ({len(pcm_all)/(SR*2)/60:.1f} min)', flush=True)

if __name__ == '__main__':
    args = sys.argv[1:]
    ven, vhi = VOICE_EN, VOICE_HI
    if '--voice-en' in args: ven = args[args.index('--voice-en') + 1]
    if '--voice-hi' in args: vhi = args[args.index('--voice-hi') + 1]
    eps = [a for a in args if a in EPS] or EPS
    total = sum(len(open(os.path.join(SCRIPTS, e + '.txt')).read()) for e in eps)
    print(f'Generating {len(eps)} episodes via Smallest.ai (~{total} chars).', flush=True)
    for ep in eps:
        build(ep, ven if ep.endswith('_en') else vhi)
    print('All done ->', AUDIO, flush=True)
