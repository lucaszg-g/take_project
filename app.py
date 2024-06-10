from abc import ABC, abstractmethod
from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from openai import OpenAI
import os

# Configurações
app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///teste9.db'


# Classe Singleton para o Banco de Dados
class Database:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls, *args, **kwargs)
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self):
        if self.__initialized:
            return
        self.__initialized = True
        self.db = SQLAlchemy()

    def init_app(self, app):
        self.db.init_app(app)


# Cria uma única instância do banco de dados
database = Database()
database.init_app(app)
db = database.db

# Chave API OpenAI
key = os.environ['OPENAI_API_KEY']


# Serviço OpenAI
class OpenAIService:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)

    def create_completion(self, model, messages):
        response = self.client.chat.completions.create(model=model, messages=messages)
        return response.choices[0].message.content


# Padrão Singleton para ChatGPTService
class ChatGPTService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ChatGPTService, cls).__new__(cls, *args, **kwargs)
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self):
        if self.__initialized:
            return
        self.__initialized = True
        self.facade = OpenAIService(api_key=os.environ['OPENAI_API_KEY'])

    @staticmethod
    def _criar_mensagem(conteudo_sistema, conteudo_usuario):
        return [
            {"role": "system", "content": conteudo_sistema},
            {"role": "user", "content": conteudo_usuario}
        ]

    def sugerir_descricao(self, descricao_projeto, nome_projeto):
        mensagens = self._criar_mensagem(
            "Responda como um professor",
            f'Crie uma nova descrição para o projeto ({nome_projeto}). Lembre-se de manter a escrita breve '
            f'e direta para destacar os principais pontos do projeto. O projeto já possui uma descrição. Retorne apenas'
            f' a descrição que você criou. ({descricao_projeto}). Use-a de base para desenvolver a sua nova descrição.'
        )
        return self.facade.create_completion(model="gpt-3.5-turbo-0125", messages=mensagens)

    def sugerir_titulo(self, breve_descricao):
        mensagens = self._criar_mensagem(
            "Aja como um professor de português.",
            f'Qual seria um bom título com base na seguinte descrição ({breve_descricao}). Limite seu '
            f'título a apenas algumas palavras para garantir a concisão.'
        )
        return self.facade.create_completion(model="gpt-3.5-turbo-0125", messages=mensagens)

    def sugerir_tarefas(self, nome_projeto, descricao_projeto, tarefas_projeto):
        tarefas_projeto_string = ', '.join(tarefas_projeto) if tarefas_projeto else None
        mensagens = self._criar_mensagem(
            "Aja como um professor",
            f'Quais tarefas seriam boas para se definir no projeto ({nome_projeto}) que tem a seguinte '
            f'descrição ({descricao_projeto}). Limite suas sugestões a apenas títulos para garantir a concisão. Envie '
            f'sua resposta separando os títulos com (;). Exemplo, abelha; mel; urso. O projeto já tem as seguintes '
            f'tarefas ({tarefas_projeto_string}).'
        )
        return self.facade.create_completion(model="gpt-3.5-turbo-0125", messages=mensagens)

    def avaliar_projeto(self, nome_projeto, descricao_projeto, tarefas_projeto):
        tarefas_projeto_string = ', '.join(tarefas_projeto) if tarefas_projeto else None
        descricao_projeto = descricao_projeto or None
        mensagens = self._criar_mensagem(
            "Aja como um gerente de projetos experiente na área",
            f'Avalie o projeto ({nome_projeto}) que tem a descrição ({descricao_projeto}) e as tarefas '
            f'({tarefas_projeto_string}). Se necessário aponte pontos do projeto que possam precisar de melhorias, '
            f'como um novo título, uma descrição mais concisa ou a criação de possíveis tarefas que seriam úteis para '
            f'o projeto. Faça essa avaliação de forma objetiva e resumida, evite textos longos. Divida sua avaliação '
            f'da seguinte forma: Avaliação sobre o nome do projeto; Avaliação da descrição do projeto; Avaliação sobre '
            f'as tarefas.'
        )
        return self.formatar_avaliacao(self.facade.create_completion(model="gpt-3.5-turbo-0125", messages=mensagens))

    def formatar_avaliacao(self, prompt):
        mensagens = self._criar_mensagem(
            "Aja como um formatador de texto.",
            f'Formate a avaliação do projeto da seguinte forma. Avaliação sobre o nome do projeto: '
            f'(coloque aqui a avaliação acerca do nome do projeto); Avaliação da descrição do projeto: (coloque aqui a '
            f'avaliação sobre a descrição do projeto); Avaliação sobre as tarefas: (coloque aqui a avaliação sobre as '
            f'tarefas do projeto). Avaliação final: (coloque aqui a avaliação final do projeto). Aqui está a avaliação '
            f'do projeto para você deve formatar ({prompt}).'
        )
        return self.facade.create_completion(model="gpt-3.5-turbo-0125", messages=mensagens)

    def filtrar_titulo(self, novo_nome_projeto):
        mensagens = self._criar_mensagem(
            "Aja como um filtro de textos.",
            f'Se o texto ({novo_nome_projeto}) estiver entre aspas, retire-as para mim. Se não tiver, '
            f'apenas repasse o texto para mim. Retorne apenas a versão final da sua resposta. Não é necessário '
            f'realizar comparações nem nada do tipo, apenas a versão final.'
        )
        return self.facade.create_completion(model="gpt-3.5-turbo-0125", messages=mensagens)


# Classes de Modelo
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

    def __init__(self, nome_projeto, usuario_id, descricao_projeto=''):
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
    data_criacao = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    data_entrega = db.Column(db.DateTime)

    projeto_id = db.Column(db.Integer, db.ForeignKey('projeto.id'), nullable=False)
    projeto = db.relationship('Projeto', backref=db.backref('projeto_rel', lazy=True))

    def __init__(self, nome_tarefa, projeto_id, status='Não Iniciado', data_entrega=None):
        self.nome_tarefa = nome_tarefa
        self.projeto_id = projeto_id
        self.status = status
        self.data_criacao = datetime.now(timezone.utc)
        self.data_entrega = data_entrega

    def set_status_tarefa(self, status_tarefa):
        self.status = status_tarefa

    def set_data_entrega(self, data_entrega):
        self.data_entrega = data_entrega


# Gerenciadores
class GerenciadorUsuario:
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
        flash('Algo deu errado. Verifique se o email ou senha estão corretos', 'warning')
        return False

    @staticmethod
    def verificar_senha(usuario_id, senha):
        usuario_senha = Usuario.query.filter_by(id=usuario_id, senha=senha).first()
        if usuario_senha:
            return True
        flash('Algo deu errado. Verifique se a senha está correta', 'warning')
        return False

    @staticmethod
    def deslogar_usuario():
        session.pop('usuario_id', None)
        flash('Você desconectou com sucesso! Sentiremos sua falta por aqui...', 'success')


class GerenciadorProjeto:
    @staticmethod
    def criar_projeto(nome_projeto, usuario_id):
        projeto_existente = Projeto.query.filter_by(nome_projeto=nome_projeto, usuario_id=usuario_id).first()
        if projeto_existente:
            flash(f'Já existe um projeto com o nome "{nome_projeto}".', 'warning')
            return None
        novo_projeto = Projeto(nome_projeto, usuario_id)
        db.session.add(novo_projeto)
        db.session.commit()
        flash(f'O projeto "{novo_projeto.nome_projeto}" foi criado com sucesso!', 'success')
        return novo_projeto

    @staticmethod
    def alterar_projeto(projeto_id, novo_nome_projeto, nova_descricao_projeto):
        projeto = Projeto.query.get(projeto_id)
        if projeto:
            projeto.nome_projeto = novo_nome_projeto
            projeto.descricao_projeto = nova_descricao_projeto
            db.session.commit()
            flash('O projeto foi alterado com sucesso!', 'success')
            return projeto
        flash('O projeto não existe ou não foi encontrado.', 'warning')
        return None

    @staticmethod
    def alterar_nome_projeto(projeto_id, novo_nome_projeto):
        projeto = Projeto.query.get(projeto_id)
        if projeto:
            projeto.nome_projeto = ChatGPTService().filtrar_titulo(novo_nome_projeto)
            db.session.commit()
            flash(f'O título do projeto foi alterado com sucesso para "{projeto.nome_projeto}"!', 'success')
            return projeto
        flash('O projeto não existe ou não foi encontrado.', 'warning')
        return None

    @staticmethod
    def alterar_descricao_projeto(projeto_id, nova_descricao_projeto):
        projeto = Projeto.query.get(projeto_id)
        if projeto:
            projeto.descricao_projeto = nova_descricao_projeto
            db.session.commit()
            flash('O projeto foi alterado com sucesso!', 'success')
            return projeto
        flash('O projeto não existe ou não foi encontrado.', 'warning')
        return None

    @staticmethod
    def excluir_projeto(projeto_id):
        projeto = Projeto.query.get(projeto_id)
        nome_projeto = projeto.nome_projeto if projeto else None
        if projeto:
            db.session.delete(projeto)
            db.session.commit()
            flash(f'O projeto "{nome_projeto}" foi excluído com sucesso!', 'success')
            return True
        flash(f'O projeto "{nome_projeto}" não existe ou não foi encontrado.', 'warning')
        return False

    @staticmethod
    def coletar_dados(projeto_id):
        projeto = Projeto.query.get(projeto_id)
        if projeto:
            nome_projeto = projeto.nome_projeto
            descricao_projeto = projeto.descricao_projeto
            lista_tarefas = [tarefa.nome_tarefa for tarefa in projeto.tarefas]
            return nome_projeto, descricao_projeto, lista_tarefas
        flash('Algo deu errado', 'danger')
        return False


class GerenciadorTarefa:
    @staticmethod
    def criar_tarefa(nome_tarefa, projeto_id):
        nova_tarefa = Tarefa(nome_tarefa, projeto_id)
        db.session.add(nova_tarefa)
        db.session.commit()
        if not VerificadorLoop.verificar_loop():
            flash(f'A Tarefa "{nova_tarefa.nome_tarefa}" foi criada com sucesso!', 'success')
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
                    flash('Formato de data inválido.', 'danger')
                    return None
            else:
                tarefa.data_entrega = None
            db.session.commit()
            if not VerificadorLoop.verificar_loop():
                flash(f'A tarefa "{tarefa.nome_tarefa}" foi alterada com sucesso!', 'success')
            return tarefa
        flash(f'A tarefa "{tarefa.nome_tarefa}" não foi encontrada ou não existe.', 'warning')
        return None

    @staticmethod
    def excluir_tarefa(tarefa_id):
        tarefa = Tarefa.query.get(tarefa_id)
        nome_tarefa = tarefa.nome_tarefa if tarefa else None
        if tarefa:
            db.session.delete(tarefa)
            db.session.commit()
            if not VerificadorLoop.verificar_loop():
                flash(f'A tarefa "{nome_tarefa}" foi excluída com sucesso!', 'success')
            return True
        flash(f'A tarefa "{nome_tarefa}" não foi encontrada.', 'warning')
        return False


class Verificador:
    @staticmethod
    def verificar_permissao_projeto(projeto_id):
        projeto = Projeto.query.get(projeto_id)
        if not projeto or projeto.usuario_id != session['usuario_id']:
            flash('Você não tem permissão para acessar este projeto.', 'warning')
            return False
        return True

    @staticmethod
    def verificar_permissao_tarefa(tarefa_id):
        tarefa = Tarefa.query.get(tarefa_id)
        if not tarefa or tarefa.projeto.usuario_id != session['usuario_id']:
            flash('Você não tem permissão para acessar esta tarefa.', 'warning')
            return False
        return True

    @staticmethod
    def verificar_sessao():
        if 'usuario_id' in session:
            return True
        flash('Você não tem permissão para executar essa ação.', 'warning')
        return False


class VerificadorLoop:
    status_loop = False

    @classmethod
    def iniciar_loop(cls):
        cls.status_loop = True

    @classmethod
    def finalizar_loop(cls):
        cls.status_loop = False

    @classmethod
    def verificar_loop(cls):
        return cls.status_loop


class MudarTema:
    @staticmethod
    def mudar(tema):
        session['tema'] = tema
        proxima_url = request.referrer
        if proxima_url and request.method == 'GET':
            return redirect(proxima_url or url_for('index'))
        return redirect(url_for('index'))


# Padrão Command para Projetos e Tarefas
class Command(ABC):
    @abstractmethod
    def execute(self):
        pass


class CriarProjetoCommand(Command):
    def __init__(self, nome_projeto, usuario_id, descricao_projeto=None):
        self.nome_projeto = nome_projeto
        self.usuario_id = usuario_id
        self.descricao_projeto = descricao_projeto

    def execute(self):
        projeto = GerenciadorProjeto.criar_projeto(self.nome_projeto, self.usuario_id)
        if projeto and self.descricao_projeto:
            projeto.set_descricao_projeto(self.descricao_projeto)
        return projeto


class AlterarProjetoCommand(Command):
    def __init__(self, projeto_id, novo_nome_projeto, nova_descricao_projeto):
        self.projeto_id = projeto_id
        self.novo_nome_projeto = novo_nome_projeto
        self.nova_descricao_projeto = nova_descricao_projeto

    def execute(self):
        return GerenciadorProjeto.alterar_projeto(self.projeto_id, self.novo_nome_projeto, self.nova_descricao_projeto)


class ExcluirProjetoCommand(Command):
    def __init__(self, projeto_id):
        self.projeto_id = projeto_id

    def execute(self):
        return GerenciadorProjeto.excluir_projeto(self.projeto_id)


class CriarTarefaCommand(Command):
    def __init__(self, nome_tarefa, projeto_id):
        self.nome_tarefa = nome_tarefa
        self.projeto_id = projeto_id

    def execute(self):
        return GerenciadorTarefa.criar_tarefa(self.nome_tarefa, self.projeto_id)


class AlterarTarefaCommand(Command):
    def __init__(self, tarefa_id, novo_nome_tarefa, novo_status, nova_data_entrega):
        self.tarefa_id = tarefa_id
        self.novo_nome_tarefa = novo_nome_tarefa
        self.novo_status = novo_status
        self.nova_data_entrega = nova_data_entrega

    def execute(self):
        return GerenciadorTarefa.alterar_tarefa(self.tarefa_id, self.novo_nome_tarefa, self.novo_status,
                                                self.nova_data_entrega)


class ExcluirTarefaCommand(Command):
    def __init__(self, tarefa_id):
        self.tarefa_id = tarefa_id

    def execute(self):
        return GerenciadorTarefa.excluir_tarefa(self.tarefa_id)


# Rotas do Flask
@app.route('/')
def index():
    if 'tema' not in session:
        session['tema'] = 'light'
    if 'usuario_id' in session:
        projetos = Projeto.query.filter_by(usuario_id=session['usuario_id']).all()
        return render_template('index.html', projetos=projetos)
    return render_template('index.html')


@app.route('/registrar', methods=['POST'])
def registrar():
    if GerenciadorUsuario.verificar_email_nome(request.form['email'], request.form['nome']):
        GerenciadorUsuario.cadastrar_usuario(request.form['nome'], request.form['email'], request.form['senha'])
    return redirect(url_for('index'))


@app.route('/entrar', methods=['POST'])
def entrar():
    GerenciadorUsuario.logar_usuario(request.form['email'], request.form['senha'])
    return redirect(url_for('index'))


@app.route('/sair')
def sair():
    GerenciadorUsuario.deslogar_usuario()
    return redirect(url_for('index'))


@app.route('/mudar_tema_claro')
def mudar_tema_claro():
    return MudarTema.mudar('light')


@app.route('/mudar_tema_escuro')
def mudar_tema_escuro():
    return MudarTema.mudar('dark')


@app.route('/projeto/<int:projeto_id>')
def projeto_especifico(projeto_id):
    if not Verificador.verificar_sessao() or not Verificador.verificar_permissao_projeto(projeto_id):
        return redirect(url_for('index'))

    projeto = Projeto.query.get(projeto_id)

    if not projeto:
        flash('O projeto especificado não foi encontrado', 'warning')
        return redirect(url_for('index'))
    return render_template('projeto_especifico.html', projeto=projeto)


@app.route('/criar_projeto', methods=['POST'])
def criar_projeto():
    if not Verificador.verificar_sessao():
        return redirect(url_for('index'))

    command = CriarProjetoCommand(request.form['nome_projeto'], session['usuario_id'],
                                  request.form.get('descricao_projeto'))
    command.execute()
    return redirect(url_for('index'))


@app.route('/alterar_projeto/<int:projeto_id>', methods=['POST'])
def alterar_projeto(projeto_id):
    if not Verificador.verificar_sessao() or not Verificador.verificar_permissao_projeto(projeto_id):
        return redirect(url_for('index'))

    command = AlterarProjetoCommand(projeto_id, request.form['nome_projeto'], request.form['descricao_projeto'])
    command.execute()
    return redirect(request.referrer or url_for('index'))


@app.route('/excluir_projeto/<int:projeto_id>', methods=['POST'])
def excluir_projeto(projeto_id):
    if not Verificador.verificar_sessao() or not Verificador.verificar_permissao_projeto(projeto_id):
        return redirect(url_for('index'))

    if GerenciadorUsuario.verificar_senha(session['usuario_id'], request.form['senha_usuario']):
        command = ExcluirProjetoCommand(projeto_id)
        command.execute()
    return redirect(request.referrer or url_for('index'))


@app.route('/criar_tarefa/<int:projeto_id>', methods=['POST'])
def criar_tarefa(projeto_id):
    if not Verificador.verificar_sessao() or not Verificador.verificar_permissao_projeto(projeto_id):
        return redirect(url_for('index'))

    command = CriarTarefaCommand(request.form['nome_tarefa'], projeto_id)
    command.execute()
    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/alterar_tarefa/<int:tarefa_id>', methods=['POST'])
def alterar_tarefa(tarefa_id):
    if not Verificador.verificar_sessao() or not Verificador.verificar_permissao_tarefa(tarefa_id):
        return redirect(url_for('index'))

    tarefa = Tarefa.query.get(tarefa_id)

    command = AlterarTarefaCommand(tarefa_id, request.form['novo_nome_tarefa'],
                                   request.form['novo_status'], request.form['nova_data_entrega'] or None)
    command.execute()
    return redirect(request.referrer or url_for('projeto_especifico', projeto_id=tarefa.projeto_id))


@app.route('/excluir_tarefa/<int:tarefa_id>', methods=['POST'])
def excluir_tarefa(tarefa_id):
    if not Verificador.verificar_sessao() or not Verificador.verificar_permissao_tarefa(tarefa_id):
        return redirect(url_for('index'))

    tarefa = Tarefa.query.get(tarefa_id)
    command = ExcluirTarefaCommand(tarefa_id)
    command.execute()

    return redirect(request.referrer or url_for('projeto_especifico', projeto_id=tarefa.projeto_id))


@app.route('/projeto/<int:projeto_id>/excluir_tarefas_selecionadas', methods=['POST'])
def excluir_tarefas_selecionadas(projeto_id):
    if not Verificador.verificar_sessao():
        return redirect(url_for('index'))

    tarefas_selecionadas = request.form.getlist('tarefas_selecionadas[]')

    if tarefas_selecionadas:
        VerificadorLoop.iniciar_loop()
        for tarefa_id in tarefas_selecionadas:
            ExcluirTarefaCommand(tarefa_id).execute()
        VerificadorLoop.finalizar_loop()
        flash('Tarefas selecionadas excluídas com sucesso!', 'success')
    else:
        flash('Algo deu errado', 'warning')
    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/projeto/<int:projeto_id>/reescrever_descricao', methods=['GET', 'POST'])
def reescrever_descricao(projeto_id):
    if request.method == 'POST':
        if not Verificador.verificar_sessao():
            return redirect(url_for('index'))

        nome_projeto, descricao_projeto, _ = GerenciadorProjeto.coletar_dados(projeto_id)
        nova_descricao_sugerida = ChatGPTService().sugerir_descricao(descricao_projeto, nome_projeto)

        flash(nova_descricao_sugerida, 'info')
        return render_template('projeto_especifico.html', projeto=Projeto.query.get(projeto_id),
                               nova_descricao_sugerida=nova_descricao_sugerida)
    flash('Algo deu errado ao carregar a pagina!', 'danger')
    return redirect(url_for('index'))


@app.route('/projeto/<int:projeto_id>/adicionar_descricao_sugerida/<string:nova_descricao_sugerida>', methods=['POST'])
def adicionar_descricao_sugerida(projeto_id, nova_descricao_sugerida):
    if not Verificador.verificar_sessao():
        return redirect(url_for('index'))

    GerenciadorProjeto.alterar_descricao_projeto(projeto_id, nova_descricao_sugerida)
    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/projeto/<int:projeto_id>/sugerir_titulo', methods=['GET', 'POST'])
def sugerir_titulo(projeto_id):
    if request.method == 'POST':
        if not Verificador.verificar_sessao():
            return redirect(url_for('index'))

        breve_descricao = request.form['nova_descricao_modelo']
        if not breve_descricao:
            flash('Algo deu errado!', 'warning')
            return redirect(url_for('projeto_especifico', projeto_id=projeto_id))
        novo_titulo = ChatGPTService().sugerir_titulo(breve_descricao)
        flash(novo_titulo, 'info')
        return render_template('projeto_especifico.html', projeto=Projeto.query.get(projeto_id),
                               novo_titulo_sugerido=novo_titulo)
    flash('Algo deu errado ao carregar a pagina!', 'danger')
    return redirect(url_for('index'))


@app.route('/projeto/<int:projeto_id>/adicionar_titulo_sugerido/<string:novo_titulo_sugerido>', methods=['POST'])
def adicionar_titulo_sugerido(projeto_id, novo_titulo_sugerido):
    if not Verificador.verificar_sessao():
        return redirect(url_for('index'))

    GerenciadorProjeto.alterar_nome_projeto(projeto_id, novo_titulo_sugerido)
    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/projeto/<int:projeto_id>/sugerir_tarefas', methods=['GET', 'POST'])
def sugerir_tarefas(projeto_id):
    if request.method == 'POST':
        if not Verificador.verificar_sessao():
            return redirect(url_for('index'))

        nome_projeto, descricao_projeto, projeto_tarefas = GerenciadorProjeto.coletar_dados(projeto_id)
        sugestao_tarefas = ChatGPTService().sugerir_tarefas(nome_projeto, descricao_projeto, projeto_tarefas)
        flash(sugestao_tarefas, 'info')
        sugestao_tarefas = sugestao_tarefas.split(';')
        return render_template('projeto_especifico.html', projeto=Projeto.query.get(projeto_id),
                               sugestao_tarefas=sugestao_tarefas)
    flash('Algo deu errado ao carregar a pagina!', 'danger')
    return redirect(url_for('index'))


@app.route('/projeto/<int:projeto_id>/adicionar_tarefas_sugeridas', methods=['POST'])
def adicionar_tarefas_sugeridas(projeto_id):
    if not Verificador.verificar_sessao():
        return redirect(url_for('index'))

    tarefas_selecionadas = request.form.getlist('tarefas_sugeridas[]')
    VerificadorLoop.iniciar_loop()
    for tarefa in tarefas_selecionadas:
        CriarTarefaCommand(tarefa, projeto_id).execute()
    VerificadorLoop.finalizar_loop()
    flash('As tarefas sugeridas foram adicionadas com sucesso!', 'success')
    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/projeto/<int:projeto_id>/avaliar_projeto', methods=['POST'])
def avaliar_projeto(projeto_id):
    if not Verificador.verificar_sessao():
        return redirect(url_for('index'))

    nome_projeto, descricao_projeto, projeto_tarefas = GerenciadorProjeto.coletar_dados(projeto_id)
    avaliacao_projeto = ChatGPTService().avaliar_projeto(nome_projeto, descricao_projeto, projeto_tarefas)
    flash(avaliacao_projeto, 'info')
    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


# Inicializar a base de dados
with app.app_context():
    db.create_all()


# Executar a aplicação
if __name__ == '__main__':
    app.run(debug=True)
