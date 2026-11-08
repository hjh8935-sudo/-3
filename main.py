import os
import datetime
import pytz
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# 기본 !help 명령어를 제거하여 custom !도움말 사용
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

KST = pytz.timezone('Asia/Seoul')
NOTIFY_TIME = datetime.time(hour=20, minute=0, tzinfo=KST)

attendance_data = {
    "title": "",
    "participants": set(),
    "absentees": set()
}

# ==========================================
# 출석체크 버튼 UI
# ==========================================
class AttendanceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="참석 ⚔️", style=discord.ButtonStyle.green, custom_id="attend_yes")
    async def attend_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user.display_name
        attendance_data["participants"].add(user)
        attendance_data["absentees"].discard(user)
        await interaction.response.send_message(f"✅ {user}님, **참석**으로 등록되었습니다.", ephemeral=True)

    @discord.ui.button(label="불참 ❌", style=discord.ButtonStyle.red, custom_id="attend_no")
    async def attend_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user.display_name
        attendance_data["absentees"].add(user)
        attendance_data["participants"].discard(user)
        await interaction.response.send_message(f"❌ {user}님, **불참**으로 등록되었습니다.", ephemeral=True)

    @discord.ui.button(label="현황 확인 📊", style=discord.ButtonStyle.secondary, custom_id="attend_status")
    async def attend_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        part_list = ", ".join(attendance_data["participants"]) if attendance_data["participants"] else "없음"
        abs_list = ", ".join(attendance_data["absentees"]) if attendance_data["absentees"] else "없음"
        
        embed = discord.Embed(
            title=f"📊 [{attendance_data['title']}] 출석 현황",
            color=discord.Color.orange()
        )
        embed.add_field(name=f"참석 ({len(attendance_data['participants'])}명)", value=part_list, inline=False)
        embed.add_field(name=f"불참 ({len(attendance_data['absentees'])}명)", value=abs_list, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ==========================================
# 봇 시작 & 금/토 20시 자동 출석 알림 루프
# ==========================================
@bot.event
async def on_ready():
    print(f"👹 [도깨비의 세계] '타이거즈' 문파 봇 실행 시작: {bot.user.name}")
    await bot.change_presence(activity=discord.Game(name="!도움말 로 명령어 확인"))
    
    if not auto_attendance_scheduler.is_running():
        auto_attendance_scheduler.start()

@tasks.loop(time=NOTIFY_TIME)
async def auto_attendance_scheduler():
    now = datetime.datetime.now(KST)
    weekday = now.weekday()  # 4: 금요일, 5: 토요일

    if weekday not in [4, 5]:
        return

    target_channel_name = "출석체크"
    
    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name=target_channel_name)
        if not channel:
            continue

        if weekday == 4:
            title = "🔥 [금요일] 신기 쟁탈전"
            desc = "금요일 20시 정기 컨텐츠 **신기 쟁탈전** 출석체크입니다!\n문파원분들은 아래 버튼을 눌러 참석 여부를 선택해 주세요."
        elif weekday == 5:
            title = "🌀 [토요일] 미혹의 정원"
            desc = "토요일 20시 정기 컨텐츠 **미혹의 정원** 출석체크입니다!\n문파원분들은 아래 버튼을 눌러 참석 여부를 선택해 주세요."

        attendance_data["title"] = title
        attendance_data["participants"].clear()
        attendance_data["absentees"].clear()

        role = discord.utils.get(guild.roles, name="문파원")
        mention_str = role.mention if role else "@everyone"

        embed = discord.Embed(title=f"🐯 타이거즈 문파 - {title}", description=desc, color=discord.Color.purple())
        await channel.send(content=f"🔔 {mention_str} 오늘 컨텐츠에 참여해주세요!", embed=embed, view=AttendanceView())


# ==========================================
# [신규 추가] !도움말 명령어
# ==========================================
@bot.command(name="도움말")
async def show_help(ctx):
    embed = discord.Embed(
        title="🐯 [타이거즈 문파] 봇 명령어 안내",
        description="도깨비의 세계 '타이거즈' 문파 전용 명령어 리스트입니다.",
        color=discord.Color.gold()
    )
    
    embed.add_field(
        name="👤 일반 문파원 명령어",
        value=(
            "• **`!인증`** : 신입 문파원에게 '문파원' 역할을 부여합니다.\n"
            "• **`!파티모집 <레이드명> <인원>`** : 파티 모집 글을 작성합니다.\n"
            "  *(예시: `!파티모집 동굴레이드 4`)*"
        ),
        inline=False
    )
    
    embed.add_field(
        name="👑 관리자 명령어 (역할 관리/메시지 관리 권한)",
        value=(
            "• **`!출석생성 금`** / **`!출석생성 토`** : 주간 컨텐츠 출석체크 카드를 즉시 생성합니다.\n"
            "• **`!역할부여 @유저 <역할명>`** : 지정 유저에게 역할을 부여합니다.\n"
            "  *(예시: `!역할부여 @홍길동 문파원`)*\n"
            "• **`!역할해제 @유저 <역할명>`** : 지정 유저의 역할을 제거합니다.\n"
            "  *(예시: `!역할해제 @홍길동 문파원`)*"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⏰ 자동 알림",
        value="• 매주 **금요일/토요일 20시 00분**에 `출석체크` 채널로 주간 컨텐츠 출석 알림이 자동으로 전송됩니다.",
        inline=False
    )
    
    embed.set_footer(text="타이거즈 문파 봇 | 문의: 문파 관리자")
    await ctx.send(embed=embed)


# ==========================================
# 요일 상관없이 수동으로 출석체크 생성하는 명령어
# ==========================================
@bot.command(name="출석생성")
@commands.has_permissions(manage_messages=True)
async def manual_attendance(ctx, day_type: str):
    if day_type == "금":
        title = "🔥 [금요일] 신기 쟁탈전"
        desc = "주간 컨텐츠 **신기 쟁탈전** 수동 출석체크입니다.\n문파원분들은 아래 버튼을 눌러 참석 여부를 선택해 주세요."
    elif day_type == "토":
        title = "🌀 [토요일] 미혹의 정원"
        desc = "주간 컨텐츠 **미혹의 정원** 수동 출석체크입니다.\n문파원분들은 아래 버튼을 눌러 참석 여부를 선택해 주세요."
    else:
        await ctx.send("⚠️ 잘못된 입력입니다. `!출석생성 금` 또는 `!출석생성 토` 형식으로 입력해주세요.")
        return

    attendance_data["title"] = title
    attendance_data["participants"].clear()
    attendance_data["absentees"].clear()

    role = discord.utils.get(ctx.guild.roles, name="문파원")
    mention_str = role.mention if role else "@everyone"

    embed = discord.Embed(title=f"🐯 타이거즈 문파 - {title}", description=desc, color=discord.Color.purple())
    await ctx.send(content=f"🔔 {mention_str} 수동 출석체크가 열렸습니다!", embed=embed, view=AttendanceView())


# ==========================================
# 1. 신입 환영 인사
# ==========================================
@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="가입-인증")
    if channel:
        embed = discord.Embed(
            title="🐯 [타이거즈] 문파에 오신 것을 환영합니다!",
            description=f"반갑습니다 {member.mention}님!\n`도깨비의 세계` 최강 문파 **타이거즈**의 일원이 되신 걸 축하드립니다.\n\n`!인증` 명령어를 입력하여 문파원 역할을 부여받으세요!",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)


# ==========================================
# 2. 문파원 셀프 인증 및 역할 부여
# ==========================================
@bot.command(name="인증")
async def register_member(ctx):
    role_name = "문파원"
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if role:
        if role in ctx.author.roles:
            await ctx.send(f"⚠️ {ctx.author.mention}님은 이미 **{role_name}** 역할이 있습니다.")
        else:
            await ctx.author.add_roles(role)
            await ctx.send(f"✅ {ctx.author.mention}님에게 **{role_name}** 역할이 부여되었습니다! 환영합니다 🐯")
    else:
        await ctx.send(f"❌ 서버에 `{role_name}` 역할이 존재하지 않습니다.")


# ==========================================
# 3. 관리자 전용 역할 부여/해제
# ==========================================
@bot.command(name="역할부여")
@commands.has_permissions(manage_roles=True)
async def give_role(ctx, member: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"❌ 서버에 `{role_name}` 역할이 존재하지 않습니다.")
        return

    if role in member.roles:
        await ctx.send(f"⚠️ {member.mention}님은 이미 **{role_name}** 역할을 가지고 있습니다.")
    else:
        await member.add_roles(role)
        await ctx.send(f"✅ {member.mention}님에게 **{role_name}** 역할을 부여했습니다.")

@bot.command(name="역할해제")
@commands.has_permissions(manage_roles=True)
async def remove_role(ctx, member: discord.Member, *, role_name: str):
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"❌ 서버에 `{role_name}` 역할이 존재하지 않습니다.")
        return

    if role not in member.roles:
        await ctx.send(f"⚠️ {member.mention}님은 **{role_name}** 역할이 없습니다.")
    else:
        await member.remove_roles(role)
        await ctx.send(f"🗑️ {member.mention}님의 **{role_name}** 역할을 해제했습니다.")


# ==========================================
# 4. 레이드 파티 모집
# ==========================================
class PartyRaidView(discord.ui.View):
    def __init__(self, raid_name: str, max_count: int, leader: str):
        super().__init__(timeout=None)
        self.raid_name = raid_name
        self.max_count = max_count
        self.leader = leader
        self.members = [leader]

    def update_embed(self):
        status = "🟢 모집 중" if len(self.members) < self.max_count else "🔴 모집 완료"
        embed = discord.Embed(
            title=f"⚔️ [타이거즈] {self.raid_name} 파티 모집 ({len(self.members)}/{self.max_count})",
            description=f"**상태:** {status}\n**파티장:** {self.leader}",
            color=discord.Color.blue() if len(self.members) < self.max_count else discord.Color.red()
        )
        member_list_str = "\n".join([f"{idx+1}. {m}" for idx, m in enumerate(self.members)])
        embed.add_field(name="현재 참가자 목록", value=member_list_str, inline=False)
        return embed

    @discord.ui.button(label="참가 신청", style=discord.ButtonStyle.success)
    async def join_party(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user.display_name
        if user in self.members:
            await interaction.response.send_message("이미 파티에 참가 중입니다.", ephemeral=True)
            return
        if len(self.members) >= self.max_count:
            await interaction.response.send_message("파티가 이미 가득 찼습니다.", ephemeral=True)
            return
        self.members.append(user)
        await interaction.message.edit(embed=self.update_embed(), view=self)
        await interaction.response.send_message(f"⚔️ {self.raid_name} 파티에 참가 신청되었습니다!", ephemeral=True)

    @discord.ui.button(label="참가 취소", style=discord.ButtonStyle.danger)
    async def leave_party(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user.display_name
        if user not in self.members:
            await interaction.response.send_message("파티 목록에 없습니다.", ephemeral=True)
            return
        self.members.remove(user)
        await interaction.message.edit(embed=self.update_embed(), view=self)
        await interaction.response.send_message(f"취소되었습니다.", ephemeral=True)

@bot.command(name="파티모집")
async def create_raid(ctx, raid_name: str = "레이드", capacity: int = 4):
    view = PartyRaidView(raid_name, capacity, ctx.author.display_name)
    await ctx.send(embed=view.update_embed(), view=view)

if __name__ == "__main__":
    bot.run(TOKEN)