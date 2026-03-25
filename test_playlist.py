import urllib.request

url = "https://open.spotify.com/playlist/4FS21KrGRmK1Au15BUQX4T"
req = urllib.request.Request(
    url, 
    headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html'
    }
)

try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        with open("playlist.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("✅ HTML saved to playlist.html")
        print("Total length:", len(html))
except Exception as e:
    print("Error:", e)
