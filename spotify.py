import urllib.request
import re
import json

def get_spotify_track_info(url):
    """
    รับลิงก์ Spotify แล้วเจาะหน้าเว็บดึงชื่อเพลง
    คืนค่าเป็น สตริง (ถ้าเป็นเพลงเดียว) หรือ ลิสต์ (ถ้าเป็นเพลย์ลิสต์/อัลบั้ม)
    """
    try:
        # เคล็ดลับวิชา แอบใช้หน้าต่าง Embed ของ Spotify เพื่อหลบการบล็อกรัน JavaScript
        if "spotify.com" in url and "/embed/" not in url:
            url = url.replace("spotify.com/", "spotify.com/embed/")
            # ตัด query string ขยะทิ้ง (เช่น ?si=...)
            url = url.split('?')[0]
            
        req = urllib.request.Request(
            url, 
            data=None, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
            # เจาะรหัสลับ JSON ที่ฝังอยู่ในหน้า Embed นำมาแปลงร่าง
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
            if match:
                data = json.loads(match.group(1))
                entity = data.get('props', {}).get('pageProps', {}).get('state', {}).get('data', {}).get('entity', {})
                
                # ตรวจสอบว่าเป็นเพลงเดียว (Track) หรือไม่
                if entity.get('type') == 'track':
                    name = entity.get('title', '')
                    artist = entity.get('subtitle', '')
                    return f"{name} {artist}"
                
                # ตรวจสอบว่าเป็น Playlist หรือ Album หรือไม่
                elif entity.get('type') in ['playlist', 'album']:
                    track_list = entity.get('trackList', [])
                    results = []
                    # ดึงเพลงออกมา (จำกัดสูงสุด 50 เพลงตามหน้า Embed ทั่วไป)
                    for t in track_list:
                        name = t.get('title', '')
                        artist = t.get('subtitle', '')
                        results.append(f"{name} {artist}")
                    return results

            # ถ้าสกัด JSON ไม่ติดจริงๆ ให้ใช้สคริปต์สำรองดึงจาก Meta Tag (รองรับแต่ Track)
            og_title = re.search(r'<meta property="og:title" content="(.*?)"', html)
            og_desc = re.search(r'<meta property="og:description" content="(.*?)"', html)
            
            if og_title and og_desc:
                song_name = og_title.group(1)
                artist_name = og_desc.group(1).replace('Song · ', '').split(' · ')[0]
                return f"{song_name} {artist_name}"
                
    except Exception as e:
        print(f"[Spotify Module] Error scraping link {url}: {e}")
        
    return None
