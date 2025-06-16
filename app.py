from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime

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
            return redirect('/diario')

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

    def executar(self):
        self.app.run(debug=True)


# ------------------------
# Execução do programa
# ------------------------
if __name__ == '__main__':
    app = DiarioApp()
    app.executar()