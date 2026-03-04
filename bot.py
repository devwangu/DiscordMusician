import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import threading
import sys
import os
import json
import queue as py_queue
import subprocess
import customtkinter as ctk

# ==============================================================================
# ส่วนที่ 1: การตั้งค่าและฟังก์ชันของบอท (จาก musicbot.py)
# ==============================================================================

# การตั้งค่าสำหรับ yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0', 
}

# การตั้งค่าให้ออกเฉพาะเสียงสำหรับ ffmpeg
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# สร้างตัวแปรดึงข้อมูลสำหรับแค่ค้นหาหรือเช็คเพลย์ลิสต์แบบเร็ว (extract_flat)
ytdl_flat_options = {
    'extract_flat': True, # เปลี่ยนเป็น True เพื่อให้มันไม่พยายามโหลดข้อมูลลึกๆ ของวิดีโอ
    'playlist_items': '1-50', # ให้โหลดแค่ 1-50 เพลงแรกจากเว็บเลย จะได้ไม่เสียเวลาโหลดมาทั้งหมด 
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0', 
}
ytdl_flat = youtube_dl.YoutubeDL(ytdl_flat_options)

# ----------------- ตัวแปรระบบคิวเพลง ----------------- #
music_queues = {}
current_song = {}
disconnect_timers = {}

# เปิดใช้งาน Intents (จำเป็นต้องติ๊กในเว็บ Discord Developer สำหรับบางตัว)
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    description='บอทเปิดเพลงง่ายๆ (แบบไม่ใช้ Class)',
    intents=intents,
)

# ----------------- ระบบตัดการเชื่อมต่ออัตโนมัติ ----------------- #
def start_disconnect_timer(ctx, guild_id):
    if guild_id in disconnect_timers:
        disconnect_timers[guild_id].cancel()
    
    async def timer():
        print(f"[Timer] ⏳ เริ่มจับเวลา 5 นาทีสำหรับห้อง {guild_id}...")
        try:
            await asyncio.sleep(300)
            if current_song.get(guild_id) is None and ctx.voice_client and ctx.voice_client.is_connected():
                print(f"[Disconnect] 🔌 ออกจากห้อง {guild_id} เนื่องจากไม่ได้ใช้งานเกิน 5 นาที")
                await ctx.voice_client.disconnect()
                get_queue(guild_id).clear()
                bot.loop.create_task(ctx.send("👋 ออกจากห้องเสียงอัตโนมัติ เนื่องจากไม่มีการใช้งานเกิน 5 นาที"))
        except asyncio.CancelledError:
            pass
            
    disconnect_timers[guild_id] = bot.loop.create_task(timer())

def cancel_disconnect_timer(guild_id):
    if guild_id in disconnect_timers:
        disconnect_timers[guild_id].cancel()
        del disconnect_timers[guild_id]
        print(f"[Timer] ❌ ยกเลิกจับเวลาสำหรับห้อง {guild_id}")

# ----------------ฟังก์ชันต่างๆ ของระบบคิว ------------------- #
def get_queue(guild_id):
    if guild_id not in music_queues:
        music_queues[guild_id] = []
    return music_queues[guild_id]

def play_next(ctx):
    queue_list = get_queue(ctx.guild.id)
    if len(queue_list) > 0:
        cancel_disconnect_timer(ctx.guild.id)
        song = queue_list.pop(0)
        current_song[ctx.guild.id] = song
        print(f"[Queue] ⏩ ดึงเพลงถัดไปจากคิว: {song['title']} (เหลือในคิว: {len(queue_list)})")
        # ให้มันไปดึง URL สตรีมช้าๆ ใน Background Task จะได้ไม่ค้างและไม่หมดอายุตอนรอคิว
        bot.loop.create_task(prepare_and_play(ctx, song))
    else:
        current_song[ctx.guild.id] = None
        print(f"[Queue] 📭 คิวเพลงว่างเปล่าในห้อง {ctx.guild.id}")
        start_disconnect_timer(ctx, ctx.guild.id)

async def prepare_and_play(ctx, song):
    try:
        loop = bot.loop
        print(f"[Audio] ⏳ กำลังโหลด Stream URL ของเพลง: {song['title']}")
        # ฟังก์ชันดาวน์โหลด URL จริง (ถ้าเป็นลิงก์ Youtube)
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(song['url'], download=False))
        
        if 'entries' in data:
            data = data['entries'][0]
            
        stream_url = data['url']
        print(f"[Audio] ✅ โหลดสำเร็จ! เริ่มจำลองเสียงไปที่ Discord")
        
        # เตรียมเสียง
        audio_source = discord.FFmpegPCMAudio(stream_url, **ffmpeg_options)
        # สั่งเล่นและตั้งให้เมื่อจบไปเรียก play_next ตัวเอง
        ctx.voice_client.play(discord.PCMVolumeTransformer(audio_source, volume=0.5), after=lambda e: play_next(ctx))
        
        print(f"[Play] ▶️ กำลังเล่น: {song['title']}")
        await ctx.send(f'🎶 กำลังเล่น: **{song["title"]}**')
    except Exception as e:
        print(f"[Error] ❌ โหลดเสียงล้มเหลว: {e}")
        await ctx.send(f"❌ เกิดข้อผิดพลาดในการดึงเสียงของเพลง **{song['title']}**: {str(e)}")
        # ถ้าเพลงมีปัญหา ข้ามไปเพลงต่อไปเลย
        play_next(ctx)

# ฟังก์ชันดึงข้อมูลแบบรวดเร็ว (Flat Extraction) เหมาะสำหรับเพลย์ลิสต์
def get_audio_info(query):
    # ค้นหาว่าเป็นลิงก์หรือข้อความธรรมดา (ถ้าเป็นการค้นหาแบบข้อความให้ดึงมาแค่ 1 อัน ytsearch1:)
    search_query = query if query.startswith('http') else f"ytsearch1:{query}"
    data = ytdl_flat.extract_info(search_query, download=False)
    
    entries = []
    if 'entries' in data: # ถ้าเป็นเพลย์ลิสต์ หรือผลการค้นหา
        for entry in data['entries']:
            if entry:
                url = entry.get('url') or entry.get('webpage_url')
                if not url and entry.get('id'):
                    url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                if url:
                    entries.append({'url': url, 'title': entry.get('title', 'Unknown Title')})
    else:
        url = data.get('webpage_url') or data.get('url')
        if not url and data.get('id'):
            url = f"https://www.youtube.com/watch?v={data.get('id')}"
        if url:
             entries.append({'url': url, 'title': data.get('title', 'Unknown Title')})
        
    return entries


# ----------------- คำสั่งบอท (Commands) ----------------- #

@bot.event
async def on_ready():
    print('=================================')
    print(f'✅ บอทออนไลน์แล้ว! ชื่อ: {bot.user}')
    print(f'🆔 ID: {bot.user.id}')
    print('=================================')
    print('พร้อมรับคำสั่ง !play, !stop, !skip, !queue')


@bot.event
async def on_voice_state_update(member, before, after):
    # คืนค่ารอบการทำงานเมื่อบอทถูกเตะออกจากห้อง หรือดิสคอนเนคเอง
    if member.id == bot.user.id and before.channel and not after.channel:
        guild_id = member.guild.id
        print(f"[Voice] 🔌 บอทถูกตัดการเชื่อมต่อจากห้อง {guild_id}")
        if guild_id in music_queues:
            music_queues[guild_id].clear()
        current_song[guild_id] = None
        cancel_disconnect_timer(guild_id)

@bot.command(name='play', help='เล่นเพลง (YouTube, SoundCloud, Twitch)')
async def play(ctx, *, query):
    if not ctx.author.voice:
        return await ctx.send("❌ คุณต้องอยู่ในห้องเสียงก่อนนะ!")

    channel = ctx.author.voice.channel
    permissions = channel.permissions_for(ctx.me)
    if not permissions.connect or not permissions.speak:
        print(f"[Permission] ❌ บอทไม่มีสิทธิ์เข้าห้อง {channel.name}")
        return await ctx.send("❌ บอทไม่มีสิทธิ์ Connect/Speak ในห้องนี้")
    
    # ถ้ายังไม่ได้เชื่อมต่อก็เข้าไป ถ้าอยู่ห้องอื่นก็ย้ายตาม
    if not ctx.voice_client:
        print(f"[Connect] 🔌 กำลังเข้าห้องเสียง: {channel.name}")
        await channel.connect()
    elif ctx.voice_client.channel != channel:
        print(f"[Connect] 🔀 ย้ายไปห้องเสียง: {channel.name}")
        await ctx.voice_client.move_to(channel)

    async with ctx.typing():
        try:
            print(f"[Search] 🔍 ค้นหาเพลงจากคำค้น/ลิงก์: {query}")
            # ใช้ event loop เพื่อไม่ให้บอทค้างตอนค้นหาเพลง
            loop = asyncio.get_event_loop()
            songs = await loop.run_in_executor(None, get_audio_info, query)
            
            if not songs:
                print(f"[Search] ❌ ไม่พบเพลง!")
                await ctx.send("❌ ไม่พบข้อมูลเพลงจากคำค้นหาหรือลิงก์นี้")
                return

            # จำกัดเพลงจากเพลย์ลิสต์ไม่เกิน 50 เพลง เพื่อป้องกันคิวล้น
            if len(songs) > 50:
                print(f"[Search] ⚠️ เพลย์ลิสต์ยาวเกินไป โหลดแค่ 50 เพลง")
                songs = songs[:50]
                await ctx.send("📢 **เพิ่มเพลย์ลิสต์ลงคิวแล้ว!** (ดึงมาสูงสุด 50 เพลงน้า 🎵)")

            queue_list = get_queue(ctx.guild.id)
            queue_list.extend(songs)
            print(f"[Queue] 📥 เพิ่ม {len(songs)} เพลงเข้าคิว (รวมเป็น {len(queue_list)} เพลง)")
            
            # เช็คว่าบอทกำลังติดคิวเล่นเพลง หรือกำลังโหลดเตรียมตัวเล่นอยู่หรือไม่
            is_active = ctx.voice_client.is_playing() or ctx.voice_client.is_paused() or current_song.get(ctx.guild.id) is not None
            
            # ถ้าบอทไม่ได้กำลังเล่นอะไรอยู่ ก็สั่งเล่นเลย
            if not is_active:
                print(f"[Play] ▶️ คิวว่างเปล่า ส่งเพลงเข้าเครื่องเล่นทันที")
                play_next(ctx)
                if len(songs) == 1:
                    await ctx.send(f'⏳ กำลังเตรียมเล่น: **{songs[0]["title"]}**')
                else:
                    await ctx.send(f'⏳ เพิ่ม **{len(songs)}** เพลงลงคิว และกำลังเตรียมเล่นเพลงแรก...')
            else:
                print(f"[Queue] ⏳ บอทกำลังยุ่ง ยืนเข้าคิวตามปกติ")
                if len(songs) == 1:
                    await ctx.send(f'✅ เพิ่มลงในคิว: **{songs[0]["title"]}**')
                else:
                    await ctx.send(f'✅ เพิ่ม **{len(songs)}** เพลงจากเพลย์ลิสต์ลงในคิวแล้ว!')
                
        except Exception as e:
            print(f"[Error] ❌ เกิดข้อผิดพลาดในคำสั่ง play: {e}")
            await ctx.send(f"❌ เกิดข้อผิดพลาดในการโหลดข้อมูล: {str(e)}")

@bot.command(name='stop', help='หยุดเพลงและออกจากห้อง')
async def stop(ctx):
    print(f"[Command] 🛑 ผู้ใช้สั่ง Stop ในห้อง {ctx.guild.id}")
    if ctx.voice_client:
        queue_list = get_queue(ctx.guild.id)
        queue_list.clear()
        current_song[ctx.guild.id] = None
        cancel_disconnect_timer(ctx.guild.id)
        await ctx.voice_client.disconnect()
        print(f"[Disconnect] 🔌 บอทถูกบังคับออกจากห้อง {ctx.guild.id}")
        await ctx.send("👋 หยุดเพลงและออกจากห้องแล้วนะ")
    else:
        await ctx.send("❌ บอทยังไม่ได้อยู่ในห้องเสียงเลย")

@bot.command(name='skip', help='ข้ามเพลง')
async def skip(ctx):
    print(f"[Command] ⏭️ ผู้ใช้สั่ง Skip ในห้อง {ctx.guild.id}")
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop() # การ stop จะไปกระตุ้น callback "after" ให้ข้ามไปเล่นคิวถัดไปอัตโนมัติ
        print(f"[Skip] ข้ามเพลงและเตรียมดึงเพลงถัดไปจากคิว (ถ้ามี)...")
        await ctx.send("⏭️ ข้ามเพลงแล้ว!")
    else:
        await ctx.send("❌ ตอนนี้ไม่ได้เล่นเพลงอะไรอยู่นะ")

@bot.command(name='queue', help='ดูรายชื่อเพลงในคิว')
async def queue(ctx):
    print(f"[Command] 📜 ผู้ใช้ขอดู Queue ในห้อง {ctx.guild.id}")
    queue_list = get_queue(ctx.guild.id)
    current = current_song.get(ctx.guild.id)
    
    if not queue_list and not current:
        return await ctx.send("📭 คิวเพลงว่างเปล่า")
        
    msg = ""
    if current:
        msg += f"🔊 **กำลังเล่น:** {current['title']}\n\n"
        
    if not queue_list:
        msg += "📭 ไม่มีเพลงในคิวถัดไป"
    else:
        # จำกัดการแสดงผลแค่ 10 เพลงแรก เพื่อไม่ให้ตัวอักษรเกินโควต้า 2000 ตัวอักษรของ Discord จนบั๊ก
        show_limit = 10
        q_list = "\n".join([f"{i+1}. {song['title']}" for i, song in enumerate(queue_list[:show_limit])])
        msg += f"📜 **Queue:**\n{q_list}"
        
        # แจ้งว่ามีอีกกี่เพลงที่ซ่อนอยู่
        if len(queue_list) > show_limit:
            msg += f"\n\n*(...and {len(queue_list) - show_limit} more)*"
            
    print(f"[Queue] แสดงคิว {len(queue_list)} เพลงให้ผู้ใช้")
    await ctx.send(msg)

# ตัวแปรจัดการให้บอทเริ่มและหยุดอย่างนุ่มนวล
_stop_event = None

# ฟังก์ชันสำหรับให้ GUI เรียกใช้งาน
def run_bot(token):
    global _stop_event
    _stop_event = threading.Event() # สร้างธงไว้รับคำสั่งปิดจาก GUI
    
    async def wait_for_stop():
        # รอจนกว่าสัญญาณหยุดจะถูกดึง
        while not _stop_event.is_set():
            await asyncio.sleep(0.5)
        # พอโดนเซ็ตปุ๊บ (กด Stop) เริ่มกระบวนการปิดบอท
        print("กำลังปิดการเชื่อมต่อ Discord และเคลียร์บอท...")
        await bot.close()
        print("ปิดบอทสมบูรณ์แล้ว!")

    async def main():
        async with bot:
            # ลุยเช็คธงหยุดควบคู่ไปกับตัวบอทหลัก
            bot.loop.create_task(wait_for_stop())
            try:
                await bot.start(token)
            except Exception as e:
                if isinstance(e, discord.errors.LoginFailure):
                    print("❌ Token ไม่ถูกต้อง! กรุณาตรวจสอบ Token อีกครั้ง")
                else:
                    print(f"❌ เกิดข้อผิดพลาดในการรันบอท: {e}")

    # ใช้ asyncio.run เพื่อจัดการ Event Loop แบบสมบูรณ์ ป้องกันหลุดการเชื่อมต่อ (Heartbeat)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

def request_stop_bot():
    if _stop_event:
        _stop_event.set()

# ==============================================================================
# ส่วนที่ 2: หน้าต่างโปรแกรม GUI (จาก gui.py)
# ==============================================================================

# ตั้งค่าธีมพื้นฐาน
ctk.set_appearance_mode("Dark")  
ctk.set_default_color_theme("blue")  

class MusicBotGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ตั้งค่าหน้าต่าง
        self.title("Discord Music Bot Launcher")
        self.geometry("550x450")
        self.resizable(False, False)

        # เปลี่ยนไอคอนของโปรแกรม (ถ้ามีไฟล์ icon.ico)
        if os.path.exists("icon.ico"):
            try:
                self.iconbitmap("icon.ico")
                
                # เปลี่ยนไอคอนที่ Taskbar (เฉพาะ Windows) แยกระบบออกจาก Python ปกติ
                import ctypes
                myappid = 'veloxgg.musicbot.launcher.v1'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception:
                pass

        # ตัวแปรสถานะ
        self.bot_thread = None
        self.is_running = False
        self.log_queue = py_queue.Queue()

        # สร้าง UI
        self.create_widgets()

        # โหลด Token เก่าถ้ามี
        self.load_token()

        # เริ่มต้น Loop อ่าน Log
        self.after(100, self.update_logs)

    def load_token(self):
        token_file = "config.json"
        if os.path.exists(token_file):
            try:
                with open(token_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "token" in data:
                        self.token_entry.insert(0, data["token"])
            except Exception as e:
                pass

    def save_token(self, token):
        token_file = "config.json"
        try:
            with open(token_file, "w", encoding="utf-8") as f:
                json.dump({"token": token}, f)
        except Exception as e:
            pass

    def create_widgets(self):
        # หัวข้อ
        self.title_label = ctk.CTkLabel(self, text="Discord Music Bot", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=(20, 10))

        # ช่องกรอก Token
        self.token_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.token_frame.pack(fill="x", padx=30, pady=10)

        self.token_label = ctk.CTkLabel(self.token_frame, text="Bot Token:", font=ctk.CTkFont(size=14))
        self.token_label.pack(side="left", padx=(0, 10))

        self.token_entry = ctk.CTkEntry(self.token_frame, placeholder_text="วาง Token บอทของคุณที่นี่...", width=300, show="*")
        self.token_entry.pack(side="left", fill="x", expand=True)

        # ปุ่ม Start / Stop
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.pack(fill="x", padx=30, pady=(10, 20))

        self.start_btn = ctk.CTkButton(self.button_frame, text="▶ Start Bot", fg_color="green", hover_color="darkgreen", command=self.start_bot)
        self.start_btn.pack(side="left", expand=True, padx=(0, 10))

        self.stop_btn = ctk.CTkButton(self.button_frame, text="⏹ Stop Bot", fg_color="red", hover_color="darkred", state="disabled", command=self.stop_bot)
        self.stop_btn.pack(side="right", expand=True, padx=(10, 0))

        # ปุ่มตัวเลือก (อัพเดท yt-dlp)
        self.update_btn = ctk.CTkButton(self, text="🔄 Update YouTube DL (แก้บั๊กเปิดเพลงไม่ได้)", 
                                        fg_color="transparent", border_width=1,text_color="gray", command=self.update_ytdlp)
        self.update_btn.pack(pady=(0, 10))

        # กล่องแสดง Log
        self.log_label = ctk.CTkLabel(self, text="Console Logs:", font=ctk.CTkFont(size=12, weight="bold"))
        self.log_label.pack(padx=30, anchor="w")

        self.log_box = ctk.CTkTextbox(self, width=500, height=150, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_box.pack(padx=30, pady=(0, 20))
        self.log_box.insert("0.0", "ระบบพร้อมทำงาน รอคำสั่ง Start...\n")
        self.log_box.configure(state="disabled")

        # Redirect ระบบ Print ให้มาลงที่ log_queue แทน
        self.redirect_stdout()

    def write_log(self, text):
        self.log_queue.put(text)

    def redirect_stdout(self):
        class StdoutRedirector:
            def __init__(self, text_widget, queue_ref):
                self.queue = queue_ref
            def write(self, string):
                if string.strip():
                    self.queue.put(string)
            def flush(self):
                pass
        sys.stdout = StdoutRedirector(self.log_box, self.log_queue)
        sys.stderr = StdoutRedirector(self.log_box, self.log_queue)

    def update_logs(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"{msg}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(100, self.update_logs) # วนลูปเช็คใหม่ทุกๆ 0.1 วินาที

    def update_ytdlp(self):
        self.write_log("กำลังดาวน์โหลดแพทช์อัปเดต YouTube DL ล่าสุด รอสักครู่...")
        self.update_btn.configure(state="disabled")
        
        def run_update():
            try:
                # คำสั่งลงเวอร์ชัน Github Master Branch
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-U", "https://github.com/yt-dlp/yt-dlp/archive/master.zip"],
                    check=True, capture_output=True, text=True
                )
                self.write_log("✅ อัปเดต YouTube DL สำเร็จแล้ว!")
            except Exception as e:
                self.write_log(f"❌ เกิดข้อผิดพลาดในการอัปเดต: {e}")
            finally:
                self.update_btn.configure(state="normal")
                
        threading.Thread(target=run_update, daemon=True).start()

    def start_bot(self):
        token = self.token_entry.get().strip()
        if not token:
            self.write_log("❌ กรุณาใส่ Bot Token ก่อนเริ่มการทำงาน!")
            return

        # บันทึก Token เก็บไว้
        self.save_token(token)

        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.token_entry.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        self.write_log("กำลังเริ่มทำงานของบอท...")

        # รันบอทใน Thread ใหม่ไม่ให้หน้าต่าง GUI ค้าง
        def bot_runner():
            try:
                run_bot(token)
            except Exception as e:
                self.write_log(f"Bot Thread Error: {e}")
                self.on_bot_stopped()

        self.bot_thread = threading.Thread(target=bot_runner, daemon=True)
        self.bot_thread.start()

    def on_bot_stopped(self):
        self.is_running = False
        self.start_btn.configure(state="normal")
        self.token_entry.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def stop_bot(self):
        self.write_log("กำลังส่งสัญญาณให้บอทออกจากระบบอย่างนุ่มนวล...")
        request_stop_bot()
        self.on_bot_stopped()
        self.write_log("✅ บอทหยุดทำงานแล้ว!")

if __name__ == "__main__":
    app = MusicBotGUI()
    app.mainloop()
