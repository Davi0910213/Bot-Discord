import discord
from discord.ext import commands, tasks
from discord.ui import View, Select, Button
import datetime
import json
import os
import threading
from flask import Flask, render_template_string, request, redirect, url_for

# =======================================================
# 🔐 CONFIGURAÇÃO DE SEGURANÇA (SEU TOKEN AQUI)
# Se o site ou o arquivo JSON derem erro, o bot usará este:
TOKEN_REDE_DE_SEGURANCA = "SEU_TOKEN_REAL_AQUI"
# =======================================================

# --- SISTEMA DE ARQUIVOS (JSON) ---
ARQUIVO_CONFIG = "config.json"
ARQUIVO_BANCO = "assinaturas.json"

def carregar_config():
    if not os.path.exists(ARQUIVO_CONFIG):
        return {
            "TOKEN": TOKEN_REDE_DE_SEGURANCA, "ID_CARGO_DONO": 0, "NOME_CATEGORIA_TICKETS": "Tickets VIP",
            "NOME_CATEGORIA_COBRANCAS": "Cobranças VIP", "CHAVE_PIX": "",
            "PRECO_PRATA": "R$ 0,00", "PRECO_OURO": "R$ 0,00", "PRECO_DIAMANTE": "R$ 0,00"
        }
    with open(ARQUIVO_CONFIG, "r", encoding="utf-8") as f:
        try:
            dados = json.load(f)
            # Se o Token no arquivo estiver vazio, usa a rede de segurança
            if not dados.get("TOKEN") or dados["TOKEN"] == "SEU_TOKEN_AQUI":
                dados["TOKEN"] = TOKEN_REDE_DE_SEGURANCA
            return dados
        except Exception:
            return {
                "TOKEN": TOKEN_REDE_DE_SEGURANCA, "ID_CARGO_DONO": 0, "NOME_CATEGORIA_TICKETS": "Tickets VIP",
                "NOME_CATEGORIA_COBRANCAS": "Cobranças VIP", "CHAVE_PIX": "",
                "PRECO_PRATA": "R$ 0,00", "PRECO_OURO": "R$ 0,00", "PRECO_DIAMANTE": "R$ 0,00"
            }

def salvar_config(dados):
    with open(ARQUIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def carregar_dados():
    if not os.path.exists(ARQUIVO_BANCO) or os.stat(ARQUIVO_BANCO).st_size == 0:
        return {}
    with open(ARQUIVO_BANCO, "r", encoding="utf-8") as f:
        try: return json.load(f)
        except json.JSONDecodeError: return {}

def salvar_dados(dados):
    with open(ARQUIVO_BANCO, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# --- INICIALIZAÇÃO DO FLASK (SITE DE CONFIGURAÇÃO) ---
app = Flask(__name__)

TEMPLATE_SITE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel de Controle - Bot VIP</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #23272a; color: #ffffff; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background-color: #2f3136; padding: 30px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        h2 { color: #5865F2; text-align: center; margin-bottom: 25px; }
        label { display: block; margin-top: 15px; color: #b9bbbe; font-weight: bold; }
        input[type="text"], input[type="number"] { width: 100%; padding: 10px; margin-top: 5px; background-color: #202225; border: 1px solid #000; border-radius: 4px; color: #fff; box-sizing: border-box; }
        input:focus { border-color: #5865F2; outline: none; }
        .btn { display: block; width: 100%; background-color: #5865F2; color: white; padding: 12px; margin-top: 25px; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; font-weight: bold; }
        .btn:hover { background-color: #4752c4; }
        .alert { background-color: #43b581; color: white; padding: 10px; border-radius: 4px; text-align: center; margin-bottom: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h2>⚙️ Configurações do Bot VIP</h2>
        {% if salvo %}
            <div class="alert">✅ Configurações salvas com sucesso! Reinicie o bot para aplicar mudanças de Token.</div>
        {% endif %}
        <form method="POST">
            <label>Token do Bot:</label>
            <input type="text" name="token" value="{{ config.TOKEN }}" placeholder="Insira o Token do Bot">

            <label>ID do Cargo Dono/Staff:</label>
            <input type="number" name="id_cargo" value="{{ config.ID_CARGO_DONO }}">

            <label>Chave PIX para Recebimento:</label>
            <input type="text" name="chave_pix" value="{{ config.CHAVE_PIX }}">

            <label>Nome da Categoria de Tickets:</label>
            <input type="text" name="cat_tickets" value="{{ config.NOME_CATEGORIA_TICKETS }}">

            <label>Nome da Categoria de Cobranças:</label>
            <input type="text" name="cat_cobrancas" value="{{ config.NOME_CATEGORIA_COBRANCAS }}">

            <label>Preço VIP Prata:</label>
            <input type="text" name="p_prata" value="{{ config.PRECO_PRATA }}">

            <label>Preço VIP Ouro:</label>
            <input type="text" name="p_ouro" value="{{ config.PRECO_OURO }}">

            <label>Preço VIP Diamante:</label>
            <input type="text" name="p_diamante" value="{{ config.PRECO_DIAMANTE }}">

            <button type="submit" class="btn">Salvar Alterações</button>
        </form>
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    config = carregar_config()
    salvo = False
    if request.method == "POST":
        config["TOKEN"] = request.form.get("token")
        config["ID_CARGO_DONO"] = int(request.form.get("id_cargo") or 0)
        config["CHAVE_PIX"] = request.form.get("chave_pix")
        config["NOME_CATEGORIA_TICKETS"] = request.form.get("cat_tickets")
        config["NOME_CATEGORIA_COBRANCAS"] = request.form.get("cat_cobrancas")
        config["PRECO_PRATA"] = request.form.get("p_prata")
        config["PRECO_OURO"] = request.form.get("p_ouro")
        config["PRECO_DIAMANTE"] = request.form.get("p_diamante")
        salvar_config(config)
        salvo = True
    return render_template_string(TEMPLATE_SITE, config=config, salvo=salvo)

def rodar_site():
    app.run(host="0.0.0.0", port=5000)

# --- INICIALIZAÇÃO DO BOT DO DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

class BotaoConfirmarPagamento(View):
    def __init__(self, plano_escolhido):
        super().__init__(timeout=None)
        self.plano_escolhido = plano_escolhido

    @discord.ui.button(label="Receber Cargo", style=discord.ButtonStyle.success, custom_id="receber_cargo_btn")
    async def receber_cargo(self, interaction: discord.Interaction, button: discord.Button):
        config = carregar_config()
        cargo_dono = interaction.guild.get_role(config["ID_CARGO_DONO"])
        if cargo_dono:
            await interaction.response.send_message("✅ Notificação enviada! Aguarde o Dono confirmar o pagamento para liberar seu cargo.", ephemeral=True)
            await interaction.channel.send(f"📢 {cargo_dono.mention}, o usuário {interaction.user.mention} informou que realizou o pagamento e está aguardando o cargo!")
            dados = carregar_dados()
            dados[str(interaction.user.id)] = {
                "username": interaction.user.name,
                "plano": self.plano_escolhido,
                "data_inicio": datetime.date.today().isoformat(),
                "notificado": False
            }
            salvar_dados(dados)
        else:
            await interaction.response.send_message("❌ Erro: Cargo de suporte configurado no site não foi encontrado.", ephemeral=True)

class MenuVIP(Select):
    def __init__(self):
        config = carregar_config()
        options = [
            discord.SelectOption(label="VIP Prata", description=f"Valor: {config['PRECO_PRATA']}", emoji="🥈"),
            discord.SelectOption(label="VIP Ouro", description=f"Valor: {config['PRECO_OURO']}", emoji="🥇"),
            discord.SelectOption(label="VIP Diamante", description=f"Valor: {config['PRECO_DIAMANTE']}", emoji="💎"),
        ]
        super().__init__(placeholder="Escolha seu plano VIP aqui...", min_values=1, max_values=1, custom_id="menu_vip_select", options=options)

    async def callback(self, interaction: discord.Interaction):
        config = carregar_config()
        plano_escolhido = self.values[0]
        guild = interaction.guild
        membro = interaction.user
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            membro: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)
        }
        
        categoria = discord.utils.get(guild.categories, name=config["NOME_CATEGORIA_TICKETS"])
        nome_canal = f"ticket-{plano_escolhido.lower().replace(' ', '-')}-{membro.name}"
        ticket_channel = await guild.create_text_channel(name=nome_canal, overwrites=overwrites, category=categoria)
        await interaction.response.send_message(f"✅ Seu ticket foi aberto em {ticket_channel.mention}!", ephemeral=True)
        
        embed_ticket = discord.Embed(
            title=f"🎫 Ticket de Compra - {plano_escolhido}",
            description=f"Olá {membro.mention}, obrigado pelo interesse no **{plano_escolhido}**!\n\nℹ️ **Como proceder:**\n1. Envie o comprovante de pagamento neste chat.\n2. Assim que enviar, clique no botão **Receber Cargo** abaixo.\n\nChave Pix para pagamento: `{config['CHAVE_PIX']}`",
            color=discord.Color.blue()
        )
        await ticket_channel.send(content=f"{membro.mention}", embed=embed_ticket, view=BotaoConfirmarPagamento(plano_escolhido))

class PainelVIPView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(MenuVIP())

# --- COMANDOS DO BOT DO DISCORD ---

@bot.command()
@commands.has_permissions(administrator=True)
async def enviar_painel(ctx):
    config = carregar_config()
    embed = discord.Embed(
        title="🎬 ASSINATURAS VIP",
        description=f"🥈 **VIP Prata** ({config['PRECO_PRATA']})\n• Cargo e cor exclusiva, chat secreto e mídias.\n\n🥇 **VIP Ouro** ({config['PRECO_OURO']})\n• Todos anteriores + Spoilers, mídias e votos.\n\n💎 **VIP Diamante** ({config['PRECO_DIAMANTE']})\n• Todos anteriores + Nome nos vídeos, call privada e sorteios!",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed, view=PainelVIPView())
    await ctx.message.delete()

@bot.command()
@commands.has_permissions(administrator=True)
async def config_info(ctx):
    config = carregar_config()
    embed = discord.Embed(title="⚙️ Configurações Atuais do Bot", color=discord.Color.blue())
    embed.add_field(name="Chave PIX", value=f"`{config['CHAVE_PIX']}`", inline=False)
    embed.add_field(name="ID do Cargo Dono", value=f"`{config['ID_CARGO_DONO']}`", inline=True)
    embed.add_field(name="Valores VIP", value=f"Prata: {config['PRECO_PRATA']}\nOuro: {config['PRECO_OURO']}\nDiamante: {config['PRECO_DIAMANTE']}", inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def set_pix(ctx, nova_chave: str):
    config = carregar_config()
    config["CHAVE_PIX"] = nova_chave
    salvar_config(config)
    await ctx.send(f"✅ Chave PIX updated para: `{nova_chave}`")

# --- MONITORAMENTO AUTOMÁTICO DE VENCIMENTOS ---
@tasks.loop(hours=24)
async def verificar_vencimentos():
    await bot.wait_until_ready()
    if not bot.guilds: return
    guild = bot.guilds[0]
    config = carregar_config()
    dados = carregar_dados()
    hoje = datetime.date.today()
    alterado = False
    
    for user_id, info in list(dados.items()):
        if info["notificado"]: continue
        data_inicio = datetime.date.fromisoformat(info["data_inicio"])
        if (hoje - data_inicio).days >= 30:
            membro = guild.get_member(int(user_id))
            if membro:
                categoria = discord.utils.get(guild.categories, name=config["NOME_CATEGORIA_COBRANCAS"])
                if not categoria: categoria = await guild.create_category(config["NOME_CATEGORIA_COBRANCAS"])
                
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    membro: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                canal_cobranca = await guild.create_text_channel(name=f"renovacao-{membro.name}", overwrites=overwrites, category=categoria)
                embed_cobranca = discord.Embed(
                    title="⏰ Renove sua assinatura VIP!",
                    description=f"Olá {membro.mention}, sua assinatura do **{info['plano']}** completou 1 mês hoje!\n\nRealize o pagamento e envie o comprovante neste canal.",
                    color=discord.Color.red()
                )
                await canal_cobranca.send(content=f"{membro.mention}", embed=embed_cobranca, view=BotaoConfirmarPagamento(info['plano']))
                info["notificado"] = True
                alterado = True
    if alterado: salvar_dados(dados)

@bot.event
async def on_ready():
    bot.add_view(PainelVIPView())
    bot.add_view(BotaoConfirmarPagamento("VIP"))
    if not verificar_vencimentos.is_running(): verificar_vencimentos.start()
    print(f"Bot online como {bot.user.name}!")

# --- EXECUÇÃO EM PARALELO (SITE + BOT UNIFICADOS) ---
def iniciar_tudo():
    t = threading.Thread(target=rodar_site)
    t.daemon = True
    t.start()
    
    config_inicial = carregar_config()
    token_final = config_inicial.get("TOKEN") or TOKEN_REDE_DE_SEGURANCA
    
    if token_final and token_final != "SEU_TOKEN_REAL_AQUI" and token_final != "SEU_TOKEN_AQUI":
        try:
            bot.run(token_final)
        except Exception as e:
            print(f"❌ Erro ao iniciar o bot: {e}")
    else:
        print("⚠️ Token não configurado nem na variável nem no config.json. Acesse o painel web para configurar.")
        import time
        while True:
            time.sleep(1)

if __name__ == "__main__":
    iniciar_tudo()
