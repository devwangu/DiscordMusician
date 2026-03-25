import urllib.request
import re

def get_spotify_track_info(url):
    """
    รับลิงก์ Spotify (Track) แล้วเจาะหน้าเว็บดึงชื่อเพลงและศิลปินออกมา 
    คืนค่าเป็นสตริงคำค้นหา เช่น 'Song Title Artist Name' เพื่อให้ YouTube ค้นหาต่อ
    """
    try:
        # ใส่ Header ปลอมตัวเป็นคอมพิวเตอร์คนจริงๆ (Chrome) ไม่ใช่บอท เพื่อกัน Spotify บล็อก
        req = urllib.request.Request(
            url, 
            data=None, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            
            # พยายามดึงจาก og:title และ og:description ที่ฝังอยู่ใน โค้ด HTML
            og_title = re.search(r'<meta property="og:title" content="(.*?)"', html)
            og_desc = re.search(r'<meta property="og:description" content="(.*?)"', html)
            
            if og_title and og_desc:
                song_name = og_title.group(1)
                # คำอธิบายของ Spotify จะเป็นแบบนี้: "Song · Artist Name · 2024"
                artist_name = og_desc.group(1).replace('Song · ', '').split(' · ')[0]
                return f"{song_name} {artist_name}"
            
            # ถ้าหาจาก OG Meta ไม่เจอ ให้ลองดึงจากจุดอื่น (Title ของ Tab Browser)
            title_match = re.search(r'<title>(.*?)</title>', html)
            if title_match:
                clean_title = title_match.group(1).split(' - song and lyrics by ')[0]
                clean_title = clean_title.split(' | Spotify')[0]
                return clean_title
                
    except Exception as e:
        print(f"[Spotify Module] Error scraping link {url}: {e}")
        
    return None
