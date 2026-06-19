import discord
from discord.ext import commands, tasks
from discord.ui import View, Select, Button
import datetime
import json
import os

# Configuração dos Intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- CONFIGURAÇÕES DO SEU SERVIDOR ---
# Substitua pelo ID real do seu cargo de administrador/dono
ID_CARGO_DONO = 123456789012345678  

NOME_CATEGORIA_TICKETS = "Tickets VIP"
NOME_CATEGORIA_COBRANCAS = "Cobranças VIP"

# Arquivo para salvar as datas das assinaturas
ARQUIVO_BANCO = "assinaturas.json"

def carregar_dados():
    if not os.path.exists(ARQUIVO_BANCO) or os.stat(ARQUIVO_BANCO).st_size == 0:
        return {}
    with open(ARQUIVO_BANCO, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def salvar_dados(dados):
    with open(ARQUIVO_BANCO, "w") as f:
        json.dump(dados, f, indent=4)

# --- BOTÃO DENTRO DO TICKET DE COMPRA ---
class BotaoConfirmarPagamento(View):
    def __init__(self, plano_escolhido):
        super().__init__(timeout=None)
        self.plano_escolhido = plano_escolhido

    @discord.ui.button(label="Receber Cargo", style=discord.ButtonStyle.success, custom_id="receber_cargo_btn")
    async def receber_cargo(self, interaction: discord.Interaction, button: discord.Button):
        cargo_dono = interaction.guild.get_role(ID_CARGO_DONO)
        
        if cargo_dono:
            await interaction.response.send_message(
                "✅ Notificação enviada! Aguarde o Dono confirmar o pagamento para liberar seu cargo.", 
                ephemeral=True
            )
            await interaction.channel.send(
                f"📢 {cargo_dono.mention}, o usuário {interaction.user.mention} informou que realizou o pagamento e está aguardando o cargo!"
            )
            
            dados = carregar_dados()
            dados[str(interaction.user.id)] = {
                "username": interaction.user.name,
                "plano": self.plano_escolhido,
                "data_inicio": datetime.date.today().isoformat(),
                "notificado": False
            }
            salvar_dados(dados)
            
        else:
            await interaction.response.send_message("❌ Erro: Cargo 'Dono' não encontrado.", ephemeral=True)

# --- MENU DE SELEÇÃO DOS VIPS ---
class MenuVIP(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="VIP Prata", description="Selecione para assinar o VIP Prata", emoji="🥈"),
            discord.SelectOption(label="VIP Ouro", description="Selecione para assinar o VIP Ouro", emoji="🥇"),
            discord.SelectOption(label="VIP Diamante", description="Selecione para assinar o VIP Diamante", emoji="💎"),
        ]
        super().__init__(placeholder="Escolha seu plano VIP aqui...", min_values=1, max_values=1, custom_id="menu_vip_select", options=options)

    async def callback(self, interaction: discord.Interaction):
        plano_escolhido = self.values[0]
        guild = interaction.guild
        membro = interaction.user
        cargo_dono = guild.get_role(ID_CARGO_DONO)

        if not cargo_dono:
            await interaction.response.send_message("❌ O cargo Dono não foi encontrado.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            membro: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            cargo_dono: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        categoria = discord.utils.get(guild.categories, name=NOME_CATEGORIA_TICKETS)
        nome_canal = f"ticket-{plano_escolhido.lower().replace(' ', '-')}-{membro.name}"
        ticket_channel = await guild.create_text_channel(name=nome_canal, overwrites=overwrites, category=categoria)

        await interaction.response.send_message(f"✅ Seu ticket foi aberto em {ticket_channel.mention}!", ephemeral=True)

        embed_ticket = discord.Embed(
            title=f"🎫 Ticket de Compra - {plano_escolhido}",
            description=(
                f"Olá {membro.mention}, obrigado pelo interesse no **{plano_escolhido}**!\n\n"
                "ℹ️ **Como proceder:**\n"
                "1. Envie o comprovante de pagamento neste chat.\n"
                "2. Assim que enviar, clique no botão **Receber Cargo** abaixo.\n\n"
                "Chave Pix do canal: `suachavepix@aqui.com`"
            ),
            color=discord.Color.blue()
        )

        await ticket_channel.send(
            content=f"{membro.mention} | {cargo_dono.mention}", 
            embed=embed_ticket, 
            view=BotaoConfirmarPagamento(plano_escolhido)
        )

class PainelVIPView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MenuVIP())

# --- COMANDO PARA GERAR O PAINEL NO DISCORD ---
@bot.command()
@commands.has_permissions(administrator=True)
async def enviar_painel(ctx):
    embed = discord.Embed(
        title="🎬 ASSINATURAS VIP",
        description=(
            "🥈 **VIP Prata**\n• Cargo e cor exclusiva, chat secreto e mídias.\n\n"
            "🥇 **VIP Ouro**\n• Todos anteriores + Spoilers, jogue com a gente e votos.\n\n"
            "💎 **VIP Diamante**\n• Todos anteriores + Nome nos vídeos, call privada e sorteios!"
        ),
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed, view=PainelVIPView())
    await ctx.message.delete()

# --- SISTEMA QUE VERIFICA SE PASSOU 1 MÊS (RODA A CADA 24H) ---
@tasks.loop(hours=24)
async def verificar_vencimentos():
    await bot.wait_until_ready()
    if not bot.guilds:
        return
    guild = bot.guilds[0] 
    
    cargo_dono = guild.get_role(ID_CARGO_DONO)
    if not cargo_dono:
        return

    dados = carregar_dados()
    hoje = datetime.date.today()
    alterado = False

    for user_id, info in list(dados.items()):
        if info["notificado"]:
            continue

        data_inicio = datetime.date.fromisoformat(info["data_inicio"])
        diferenca_dias = (hoje - data_inicio).days

        if diferenca_dias >= 30:
            membro = guild.get_member(int(user_id))
            if membro:
                categoria = discord.utils.get(guild.categories, name=NOME_CATEGORIA_COBRANCAS)
                if not categoria:
                    categoria = await guild.create_category(NOME_CATEGORIA_COBRANCAS)

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    membro: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    cargo_dono: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }

                canal_cobranca = await guild.create_text_channel(
                    name=f"renovacao-{membro.name}", 
                    overwrites=overwrites, 
                    category=categoria
                )

                embed_cobranca = discord.Embed(
                    title="⏰ Renove sua assinatura VIP!",
                    description=(
                        f"Olá {membro.mention}, sua assinatura do **{info['plano']}** completou 1 mês hoje!\n\n"
                        "Realize o pagamento e envie o comprovante neste canal para manter seus benefícios."
                    ),
                    color=discord.Color.red()
                )
                
                await canal_cobranca.send(
                    content=f"{membro.mention} | {cargo_dono.mention}", 
                    embed=embed_cobranca,
                    view=BotaoConfirmarPagamento(info['plano'])
                )
                
                info["notificado"] = True
                alterado = True

    if alterado:
        salvar_dados(dados)

@bot.event
async def on_ready():
    bot.add_view(PainelVIPView())
    bot.add_view(BotaoConfirmarPagamento("VIP")) 
    
    if not verificar_vencimentos.is_running():
        verificar_vencimentos.start()
        
    print(f"Bot online como {bot.user.name}!")

# Coloque seu token verdadeiro entre as aspas na linha abaixo
bot.run("SEU_TOKEN_AQUI")
