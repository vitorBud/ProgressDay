from flask import Flask, render_template, request, redirect, send_file
import sqlite3
from datetime import datetime
from io import BytesIO
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
import tempfile

# ----------------------------
# Classe para acessar o banco
# ----------------------------
class RegistroDAO:
    def __init__(self, db_path='database.db'):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS registros (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data TEXT,
                    atividades TEXT,
                    aprendizado TEXT,
                    emocao TEXT
                )
            """)

    def inserir_registro(self, data, atividades, aprendizado, emocao):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO registros (data, atividades, aprendizado, emocao)
                VALUES (?, ?, ?, ?)
            """, (data, atividades, aprendizado, emocao))

    def listar_registros(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, data, atividades, aprendizado, emocao
                FROM registros
                ORDER BY id DESC
            """)
            return cursor.fetchall()

    def buscar_por_id(self, id):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, data, atividades, aprendizado, emocao
                FROM registros
                WHERE id = ?
            """, (id,))
            return cursor.fetchone()

    def atualizar_registro(self, id, atividades, aprendizado, emocao):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE registros
                SET atividades = ?, aprendizado = ?, emocao = ?
                WHERE id = ?
            """, (atividades, aprendizado, emocao, id))

    def excluir_registro(self, id):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM registros WHERE id = ?", (id,))

    def contar_emocoes(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT emocao, COUNT(*)
                FROM registros
                GROUP BY emocao
            """)
            dados = {"Feliz": 0, "Neutro": 0, "Triste": 0}
            for emocao, count in cursor.fetchall():
                if emocao in dados:
                    dados[emocao] = count
            return dados

    def listar_emocoes_com_datas(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT data, emocao FROM registros ORDER BY data")
            return cursor.fetchall()

# --------------------------
# Classe principal da aplicação
# --------------------------
class DiarioApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.dao = RegistroDAO()
        self.configurar_rotas()

    def configurar_rotas(self):
        @self.app.route('/')
        def index():
            return render_template('home.html')  # Página inicial agora é a home

        @self.app.route('/home')
        def home():
            return render_template('home.html')

        @self.app.route('/diario')
        def diario():
            emocoes = self.dao.contar_emocoes()
            return render_template('diario.html', **emocoes)


        @self.app.route('/registrar', methods=['POST'])
        def registrar():
            data = datetime.now().strftime("%d/%m/%Y")
            atividades = request.form['atividades']
            aprendizado = request.form['aprendizado']
            emocao = request.form['emocao']
            self.dao.inserir_registro(data, atividades, aprendizado, emocao)
            return redirect('/registros')

        @self.app.route('/registros')
        def ver_registros():
            registros = self.dao.listar_registros()
            return render_template('registros.html', registros=registros)

        @self.app.route('/editar/<int:id>', methods=['GET', 'POST'])
        def editar(id):
            if request.method == 'POST':
                atividades = request.form['atividades']
                aprendizado = request.form['aprendizado']
                emocao = request.form['emocao']
                self.dao.atualizar_registro(id, atividades, aprendizado, emocao)
                return redirect('/registros')
            else:
                registro = self.dao.buscar_por_id(id)
                if not registro:
                    return "Registro não encontrado", 404
                return render_template('editar.html', registro=registro)

        @self.app.route('/excluir/<int:id>', methods=['POST'])
        def excluir(id):
            self.dao.excluir_registro(id)
            return redirect('/registros')

        @self.app.route('/relatorio')
        def relatorio():
            registros = self.dao.listar_registros()
            emocoes_por_data = self.dao.listar_emocoes_com_datas()
            
            datas = []
            valores = []
            contagem = {"Triste": 1, "Neutro": 2, "Feliz": 3}
            media = 0

            for data, emocao in emocoes_por_data:
                valor = contagem.get(emocao, 0)
                datas.append(data)
                valores.append(valor)
                media += valor

            media_final = media / len(valores) if valores else 0
            if media_final > 2.3:
                analise = "Você está passando por dias positivos!"
            elif media_final < 1.7:
                analise = "Talvez esteja enfrentando desafios emocionais."
            else:
                analise = "Seu humor está estável."

            dados_linha = {"datas": datas, "valores": valores}
            return render_template('relatorio.html', dados_linha=dados_linha, analise=analise)

        @self.app.route('/baixar_pdf')
        def baixar_pdf():
            registros = self.dao.listar_registros()
            emocoes_por_data = self.dao.listar_emocoes_com_datas()

            # Criar figura do gráfico
            fig = Figure(figsize=(6, 2.5))
            ax = fig.subplots()
            contagem = {"Triste": 1, "Neutro": 2, "Feliz": 3}
            datas = [d for d, _ in emocoes_por_data]
            valores = [contagem.get(e, 0) for _, e in emocoes_por_data]
            ax.plot(datas, valores, marker='o', color='blue')
            ax.set_ylim(0, 4)
            ax.set_yticks([1, 2, 3])
            ax.set_yticklabels(['Triste', 'Neutro', 'Feliz'])
            ax.set_title('Evolução das Emoções')
            ax.tick_params(axis='x', rotation=45)

            # Salvar gráfico como imagem
            buf = BytesIO()
            fig.savefig(buf, format='png')
            buf.seek(0)

            # Criar PDF
            output = BytesIO()
            c = canvas.Canvas(output, pagesize=A4)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, 800, "Relatório de Emoções - ProgressDay")
            c.setFont("Helvetica", 10)

            y = 760
            for r in registros:
                texto = f"{r[1]} - {r[2]} | {r[3]} | Emoção: {r[4]}"
                c.drawString(50, y, texto)
                y -= 15
                if y < 100:
                    c.showPage()
                    y = 800

            # Inserir o gráfico no PDF
            c.showPage()
            c.drawImage(ImageReader(buf), 50, 400, width=500, height=250)
            c.save()
            output.seek(0)

            return send_file(output, as_attachment=True, download_name="relatorio_emocoes.pdf", mimetype='application/pdf')

    def executar(self):
        self.app.run(debug=True)

# ------------------------
# Execução do programa
# ------------------------
if __name__ == '__main__':
    app = DiarioApp()
    app.executar()
