from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from openai import OpenAI

# Configurações
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///teste9.db'

db = SQLAlchemy(app)

client = OpenAI(api_key='')  # Coloque aqui a sua chave


# ChatGPT
class ChatGPTService:
    __instance = None

    def __new__(cls):  # Instancia única
        if ChatGPTService.__instance is None:
            ChatGPTService.__instance = super().__new__(cls)
        return ChatGPTService.__instance

    @staticmethod
    def sugerir_descricao(prompt):
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "text"},
            messages=[
                {"role": "system", "content": "Aja como um chefe"},
                {"role": "user", "content": 'De uma breve sugestão de descrição do projeto, nome:  ' + prompt}
            ]
        )
        return response.choices[0].message.content


# Models
class Usuario(db.Model):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(50), nullable=False, unique=True)
    senha = db.Column(db.String(50), nullable=False)

    def __init__(self, nome, email, senha):
        self.nome = nome
        self.email = email
        self.senha = senha


class Projeto(db.Model):
    __tablename__ = 'projeto'
    id = db.Column(db.Integer, primary_key=True)
    nome_projeto = db.Column(db.String(80), nullable=False)
    descricao_projeto = db.Column(db.String())
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    usuario = db.relationship('Usuario', backref=db.backref('projetos', lazy=True))
    tarefas = db.relationship('Tarefa', backref='projeto_rel', cascade="all, delete-orphan", lazy=True)

    def __init__(self, nome_projeto, usuario_id, descricao_projeto=None):
        self.nome_projeto = nome_projeto
        self.usuario_id = usuario_id
        self.descricao_projeto = descricao_projeto

    def set_descricao_projeto(self, descricao_projeto):
        self.descricao_projeto = descricao_projeto
        db.session.commit()


class Tarefa(db.Model):
    __tablename__ = 'tarefa'
    id = db.Column(db.Integer, primary_key=True)
    nome_tarefa = db.Column(db.String(80), nullable=False)
    status = db.Column(db.String(30), nullable=False, default='incompleta')
    data_criacao = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now())
    data_entrega = db.Column(db.DateTime)

    projeto_id = db.Column(db.Integer, db.ForeignKey('projeto.id'), nullable=False)
    projeto = db.relationship('Projeto', backref=db.backref('projeto_rel', lazy=True))

    def __init__(self, nome_tarefa, projeto_id, status='incompleta', data_entrega=None):
        self.nome_tarefa = nome_tarefa
        self.projeto_id = projeto_id
        self.status = status
        self.data_criacao = datetime.now(timezone.utc)
        self.data_entrega = data_entrega

    def set_status_tarefa(self, status_tarefa):
        self.status = status_tarefa

    def set_data_entrega(self, data_entrega):
        self.data_entrega = data_entrega


class ControleUsuario:
    @staticmethod
    def verificar_email_nome(email, nome):
        verificar_email = Usuario.query.filter_by(email=email).first()
        verificar_usuario = Usuario.query.filter_by(nome=nome).first()
        if verificar_email or verificar_usuario:
            flash('Este nome ou email já está cadastrado', 'warning')
            return False
        return True

    @staticmethod
    def cadastrar_usuario(nome, email, senha):
        usuario = Usuario(nome, email, senha)
        db.session.add(usuario)
        db.session.commit()
        flash('Sua conta foi criada com sucesso!', 'success')
        return usuario

    @staticmethod
    def logar_usuario(email, senha):
        usuario = Usuario.query.filter_by(email=email, senha=senha).first()
        if usuario:
            session['usuario_id'] = usuario.id
            session['usuario_nome'] = usuario.nome
            flash(f'Seja Bem-Vindo(a) {usuario.nome}!', 'success')
            return True
        else:
            flash('Algo deu errado. Verifique se o email ou senha estão corretos', 'warning')
            return False

    @staticmethod
    def deslogar_usuario():
        session.pop('usuario_id', None)
        flash('Você se desconectou com sucesso!', 'success')


class ControleProjeto:
    @staticmethod
    def criar_projeto(nome_projeto, usuario_id):
        projeto_existente = Projeto.query.filter_by(nome_projeto=nome_projeto, usuario_id=usuario_id).first()
        if projeto_existente:
            flash('Já existe um projeto com esse nome.', 'warning')
            return None
        novo_projeto = Projeto(nome_projeto, usuario_id)
        db.session.add(novo_projeto)
        db.session.commit()
        flash('Projeto criado com sucesso!', 'success')
        return novo_projeto

    @staticmethod
    def alterar_projeto(projeto_id, novo_nome_projeto, nova_descricao_projeto):
        projeto = Projeto.query.get(projeto_id)
        if projeto:
            projeto.nome_projeto = novo_nome_projeto
            projeto.descricao_projeto = nova_descricao_projeto
            db.session.commit()
            flash('Projeto alterado com sucesso!', 'success')
            return projeto
        flash('Projeto não encontrado.', 'danger')
        return None

    @staticmethod
    def excluir_projeto(projeto_id):
        projeto = Projeto.query.get(projeto_id)
        if projeto:
            db.session.delete(projeto)
            db.session.commit()
            flash('Projeto excluído com sucesso!', 'success')
            return True
        flash('Projeto não encontrado.', 'danger')
        return False


class ControleTarefa:
    @staticmethod
    def criar_tarefa(nome_tarefa, projeto_id):
        nova_tarefa = Tarefa(nome_tarefa, projeto_id)
        db.session.add(nova_tarefa)
        db.session.commit()
        flash('Tarefa criada com sucesso!', 'success')
        return nova_tarefa

    @staticmethod
    def alterar_tarefa(tarefa_id, novo_nome_tarefa, novo_status, nova_data_entrega):
        tarefa = Tarefa.query.get(tarefa_id)
        if tarefa:
            tarefa.nome_tarefa = novo_nome_tarefa

            if novo_status:
                tarefa.status = novo_status

            if nova_data_entrega:
                try:
                    tarefa.data_entrega = datetime.strptime(nova_data_entrega, '%Y-%m-%d')
                except ValueError:
                    flash('Formato de data inválido. Use o formato AAAA-MM-DD.', 'danger')
                    return None
            else:
                tarefa.data_entrega = None

            db.session.commit()
            flash('Tarefa alterada com sucesso!', 'success')
            return tarefa
        flash('Tarefa não encontrada.', 'danger')
        return None

    @staticmethod
    def excluir_tarefa(tarefa_id):
        tarefa = Tarefa.query.get(tarefa_id)
        if tarefa:
            db.session.delete(tarefa)
            db.session.commit()
            flash('Tarefa excluída com sucesso!', 'success')
            return True
        flash('Tarefa não encontrada.', 'danger')
        return False


class ControlePermissoes:
    @staticmethod
    def verificar_permissao_projeto(projeto_id):
        projeto = Projeto.query.filter_by(id=projeto_id, usuario_id=session['usuario_id']).first()
        if not projeto:
            flash('Você não tem permissão para acessar este projeto.', 'danger')
            return False
        return True

    @staticmethod
    def verificar_permissao_tarefa(tarefa_id):
        tarefa = Tarefa.query.get(tarefa_id)
        if not tarefa or tarefa.projeto.usuario_id != session['usuario_id']:
            flash('Você não tem permissão para acessar esta tarefa.', 'danger')
            return False
        return True


# Routes
@app.route('/')
def index():
    if 'usuario_id' in session:
        projetos = Projeto.query.filter_by(usuario_id=session['usuario_id']).all()
        return render_template('index.html', projetos=projetos)
    return render_template('index.html')


@app.route('/registrar', methods=['POST'])
def registrar():
    nome = request.form['nome']
    email = request.form['email']
    senha = request.form['senha']
    if ControleUsuario.verificar_email_nome(email, nome):
        ControleUsuario.cadastrar_usuario(nome, email, senha)
        return redirect(url_for('index'))
    return redirect(url_for('index'))


@app.route('/entrar', methods=['POST'])
def entrar():
    email = request.form['email']
    senha = request.form['senha']
    ControleUsuario.logar_usuario(email, senha)
    return redirect(url_for('index'))


@app.route('/sair')
def sair():
    ControleUsuario.deslogar_usuario()
    return redirect(url_for('index'))


@app.route('/mudar_tema_claro')
def mudar_tema_claro():
    session['tema'] = 'light'
    return redirect(url_for('index'))


@app.route('/mudar_tema_escuro')
def mudar_tema_escuro():
    session['tema'] = 'dark'
    return redirect(url_for('index'))


@app.route('/projeto/<int:projeto_id>', methods=['GET'])
def projeto_especifico(projeto_id):
    if not ('usuario_id' in session):
        flash('Você precisa estar logado para acessar esta página', 'warning')
        return redirect(url_for('index'))

    if not ControlePermissoes.verificar_permissao_projeto(projeto_id):
        return redirect(url_for('index'))

    projeto = Projeto.query.get(projeto_id)
    if not projeto:
        flash('O projeto especificado não foi encontrado', 'danger')
        return redirect(url_for('index'))
    return render_template('projeto_especifico.html', projeto=projeto)


@app.route('/criar_projeto', methods=['POST'])
def criar_projeto():
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para criar um projeto', 'warning')
        return redirect(url_for('index'))

    nome_projeto = request.form['nome_projeto']
    descricao_projeto = request.form['descricao_projeto']
    usuario_id = session['usuario_id']
    projeto = ControleProjeto.criar_projeto(nome_projeto, usuario_id)
    if projeto:
        if descricao_projeto:
            projeto.set_descricao_projeto(descricao_projeto)
        return redirect(url_for('index'))
    return redirect(url_for('index'))


@app.route('/alterar_projeto/<int:projeto_id>', methods=['POST'])
def alterar_projeto(projeto_id):
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para alterar um projeto', 'warning')
        return redirect(url_for('index'))

    if not ControlePermissoes.verificar_permissao_projeto(projeto_id):
        return redirect(url_for('index'))

    novo_nome_projeto = request.form['nome_projeto']
    nova_descricao_projeto = request.form['descricao_projeto']

    ControleProjeto.alterar_projeto(projeto_id, novo_nome_projeto, nova_descricao_projeto)

    return redirect(url_for('index'))


@app.route('/excluir_projeto/<int:projeto_id>', methods=['POST'])
def excluir_projeto(projeto_id):
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para excluir um projeto', 'warning')
        return redirect(url_for('index'))

    if not ControlePermissoes.verificar_permissao_projeto(projeto_id):
        return redirect(url_for('index'))

    ControleProjeto.excluir_projeto(projeto_id)
    return redirect(url_for('index'))


@app.route('/criar_tarefa', methods=['POST'])
def criar_tarefa():
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para criar uma tarefa', 'warning')
        return redirect(url_for('index'))

    projeto_id = request.form['projeto_id']
    if not ControlePermissoes.verificar_permissao_projeto(projeto_id):
        return redirect(url_for('index'))

    nome_tarefa = request.form['nome_tarefa']
    ControleTarefa.criar_tarefa(nome_tarefa, projeto_id)

    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/alterar_tarefa/<int:tarefa_id>', methods=['POST'])
def alterar_tarefa(tarefa_id):
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para alterar uma tarefa', 'warning')
        return redirect(url_for('index'))

    if not ControlePermissoes.verificar_permissao_tarefa(tarefa_id):
        return redirect(url_for('index'))

    novo_nome_tarefa = request.form['novo_nome_tarefa']
    novo_status = request.form['novo_status']
    nova_data_entrega = request.form['nova_data_entrega']

    if not nova_data_entrega:
        nova_data_entrega = None

    ControleTarefa.alterar_tarefa(tarefa_id, novo_nome_tarefa, novo_status, nova_data_entrega)
    tarefa = Tarefa.query.get(tarefa_id)
    return redirect(url_for('projeto_especifico', projeto_id=tarefa.projeto_id))


@app.route('/excluir_tarefa/<int:tarefa_id>', methods=['POST'])
def excluir_tarefa(tarefa_id):
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para excluir uma tarefa', 'warning')
        return redirect(url_for('index'))

    if not ControlePermissoes.verificar_permissao_tarefa(tarefa_id):
        return redirect(url_for('index'))

    tarefa = Tarefa.query.get(tarefa_id)
    projeto_id = tarefa.projeto_id
    ControleTarefa.excluir_tarefa(tarefa_id)

    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/sugerir_descricao/<nome_projeto>', methods=['POST'])
def sugerir_descricao(nome_projeto):
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para sugerir melhorias', 'warning')
        return redirect(url_for('index'))

    melhoria = ChatGPTService.sugerir_descricao(nome_projeto)
    flash(melhoria, 'info')
    return redirect(url_for('index'))


# Inicializar a base de dados
with app.app_context():
    db.create_all()

# Executar a aplicação
if __name__ == '__main__':
    app.run(debug=True)
