from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from openai import OpenAI
import os

# Configurações
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///teste9.db'

db = SQLAlchemy(app)

client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])


# ChatGPT
class ChatGPTService:
    __instance = None

    def __new__(cls):  # Instancia única
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    @staticmethod
    def sugerir_descricao(descricao_projeto, nome_projeto):
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "text"},
            messages=[
                {"role": "system", "content": "Responda como um professor"},
                {"role": "user", "content": f'Crie uma nova descrição para projeto ({nome_projeto}). Observação, '
                                            f'Lembre-se de manter a escrita breve e direta para destacar os principais'
                                            f' pontos do projeto. Observação 2, o projeto ja possui uma descrição. '
                                            f'Observação 3, retorne apenas a descrição que você criou, nada mais alem '
                                            f'disso. '
                                            f'({descricao_projeto}). Use-a de base para a desenvolver a sua nova '
                                            f'descrição.'}
            ]
        )
        return response.choices[0].message.content

    @staticmethod
    def sugerir_titulo(breve_descricao):
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "text"},
            messages=[
                {"role": "system", "content": "Aja como um professor de português."},
                {"role": "user",
                 "content": f'Qual seria um bom título com base na seguinte descrição ({breve_descricao}). Observação, '
                            f'limite seu título a apenas algumas palavras para garantir a concisão'}
            ]
        )
        return resposta.choices[0].message.content

    @staticmethod
    def sugerir_taferas(nome_projeto, descricao_projeto, tarefas_projeto):
        if len(tarefas_projeto) >= 0:
            tarefas_projeto_string = ', '.join(tarefas_projeto)
        else:
            tarefas_projeto_string = None

        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "text"},
            messages=[
                {"role": "system", "content": "Aja como um professor"},
                {"role": "user", "content": f'Quais tarefas seriam boas para se definir no projeto ({nome_projeto}) que'
                                            f' tem a seguinte descrição ({descricao_projeto}). Observação, limite suas '
                                            f'sugestões em apenas títulos para garantir a concisão. Observação 2, envie'
                                            f' sua resposta separando os títulos com (;). Exemplo, abelha; mel; urso.'
                                            f' Observação 3, o projeto ja tem as seguintes tarefas '
                                            f'({tarefas_projeto_string})'}
            ]
        )
        return resposta.choices[0].message.content

    @staticmethod
    def avaliar_projeto(nome_projeto, descricao_projeto, tarefas_projeto):
        if len(tarefas_projeto) >= 0:
            tarefas_projeto_string = ', '.join(tarefas_projeto)
        else:
            tarefas_projeto_string = None

        if not descricao_projeto:
            descricao_projeto = None

        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "text"},
            messages=[
                {"role": "system", "content": "Aja como um gerente de projetos experiente na área"},
                {"role": "user",
                 "content": f'Avalie o projeto ({nome_projeto}) que tem a descrição ({descricao_projeto}) e as tarefas '
                            f'({tarefas_projeto_string}). Se necessário aponte pontos do projeto que possam precisar de'
                            f' melhorias, como um novo titúlo, uma descrição mais concisa ou a criação de possíveis '
                            f'tarefas que seriam uteis para o projeto. Observação, faça essa avaliação de forma'
                            f' objetiva e resumida, evite de passar textos grandes. Observação 2, tenha dividido na sua'
                            f'avaliação a seguinte estrutura; Avaliação acerca do nome do projeto, Avaliação acerca a'
                            f'descrição do projeto e Avaliação acerca as tarefas.'}
            ]
        )
        return ChatGPTService.fomatar_avaliacao(resposta.choices[0].message.content)

    @staticmethod
    def fomatar_avaliacao(prompt):
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "text"},
            messages=[
                {"role": "system", "content": "Aja como um formatador de texto."},
                {"role": "user", "content": f'Formate a avaliação do projeto da seguinte forma. Avaliação sobre o nome'
                                            f' do projeto: (coloque aqui a avaliação acerca do nome do projeto); '
                                            f'Avaliação da descrição do projeto: (coloque aqui a avaliação sobre a '
                                            f'descrição do projeto);nAvaliação sobre as tarefas: (coloque aqui a '
                                            f'avaliação sobre as tarefas do projeto). Avaliação final: (coloque aqui '
                                            f'a avaliação final do projeto). Aqui esta a avaliação do projeto para você'
                                            f' deve formatar ({prompt})'}
            ]
        )
        return resposta.choices[0].message.content

    @staticmethod
    def filtrar_titulo(novo_nome_projeto):
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "Aja como um filtro de textos."},
                {"role": "user",
                 "content": f'Se o texto ({novo_nome_projeto}) estiver entre aspas, retire-as para mim. Se não tiver, '
                            f'apenas repasse o texto para mim. Observação: retorne apenas e versão final da sua '
                            f'resposta. Não e necessário realizar comparações e nem nada do tipo, '
                            f'apenas a versão final'}
            ]
        )
        return resposta.choices[0].message.content


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


class ComandosUsuario:
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
    def verificar_senha(usuario_id, senha):
        usuario_senha = Usuario.query.filter_by(id=usuario_id, senha=senha).first()
        if usuario_senha:
            return True
        else:
            flash('Algo deu errado. Verifique se a senha esta correta', 'warning')
            return False

    @staticmethod
    def deslogar_usuario():
        session.pop('usuario_id', None)
        flash('Você desconectou com sucesso! Sentiremos sua falta por aqui...', 'success')


class ComandosProjeto:
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
            # Alterar so o título
            if novo_nome_projeto and not nova_descricao_projeto:
                projeto.nome_projeto = ChatGPTService.filtrar_titulo(novo_nome_projeto)
                db.session.commit()
                flash(f'O título do projeto foi alterado com sucesso para "{projeto.nome_projeto}"!', 'success')
                return projeto

            # Alterar so a descrição
            elif nova_descricao_projeto and not novo_nome_projeto:
                projeto.descricao_projeto = nova_descricao_projeto
                db.session.commit()
                flash('A descrição do projeto foi alterada com sucesso!', 'success')
                return projeto

            # Altera ambos
            projeto.nome_projeto = novo_nome_projeto
            projeto.descricao_projeto = nova_descricao_projeto
            db.session.commit()
            flash('O projeto foi alterado com sucesso!', 'success')
            return projeto

        else:
            # Erro: projeto não existe ou não foi encontrado
            flash('O projeto não existe ou não foi encontrado.', 'warning')
            return None

    @staticmethod
    def excluir_projeto(projeto_id):
        projeto = Projeto.query.get(projeto_id)
        nome_projeto = projeto.nome_projeto

        if projeto:
            db.session.delete(projeto)
            db.session.commit()
            flash(f'O projeto "{nome_projeto}" foi excluído com sucesso!', 'success')
            return True

        else:
            # Erro: projeto não existe ou não foi encontrado
            flash(f'O projeto "{nome_projeto}" não existe ou não foi encontrado.', 'warning')
            return False

    @staticmethod
    def coletar_dados(projeto_id):
        projeto = Projeto.query.get(projeto_id)

        if projeto:
            nome_projeto = projeto.nome_projeto
            descricao_projeto = projeto.descricao_projeto
            lista_tarefas = []

            for tarefa in projeto.tarefas:
                lista_tarefas.append(tarefa.nome_tarefa)

            return nome_projeto, descricao_projeto, lista_tarefas
        else:
            flash('Algo deu errado', 'danger')
            return False


class ComandosTarefa:
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
        nome_tarefa = tarefa.nome_tarefa

        if tarefa:
            db.session.delete(tarefa)
            db.session.commit()
            if not VerificadorLoop.verificar_loop():
                flash(f'A tarefa "{nome_tarefa}" foi excluída com sucesso!', 'success')
            return True
        else:
            flash(f'A tarefa "{nome_tarefa}" não foi encontrada.', 'warning')
            return False


class VerificarPermissoes:
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
        else:
            flash('Você não tem permissão para executar essa ação.', 'warning')
            return False


class VerificadorLoop:
    __instance = None
    status_loop = False

    def __new__(cls):  # Instancia única
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

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
            return redirect(proxima_url)
        else:
            return redirect(url_for('index'))


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

    if ComandosUsuario.verificar_email_nome(email, nome):
        ComandosUsuario.cadastrar_usuario(nome, email, senha)
        return redirect(url_for('index'))

    return redirect(url_for('index'))


@app.route('/entrar', methods=['POST'])
def entrar():
    email = request.form['email']
    senha = request.form['senha']

    ComandosUsuario.logar_usuario(email, senha)

    return redirect(url_for('index'))


@app.route('/sair')
def sair():
    ComandosUsuario.deslogar_usuario()
    return redirect(url_for('index'))


@app.route('/mudar_tema_claro')
def mudar_tema_claro():
    return MudarTema.mudar('light')


@app.route('/mudar_tema_escuro')
def mudar_tema_escuro():
    return MudarTema.mudar('dark')


@app.route('/projeto/<int:projeto_id>')
def projeto_especifico(projeto_id):
    if not VerificarPermissoes.verificar_sessao():
        return redirect(url_for('index'))

    if not VerificarPermissoes.verificar_permissao_projeto(projeto_id):
        return redirect(url_for('index'))

    projeto = Projeto.query.get(projeto_id)

    if not projeto:
        flash('O projeto especificado não foi encontrado', 'warning')
        return redirect(url_for('index'))

    return render_template('projeto_especifico.html', projeto=projeto)


@app.route('/criar_projeto', methods=['POST'])
def criar_projeto():
    if not VerificarPermissoes.verificar_sessao():
        return redirect(url_for('index'))

    nome_projeto = request.form['nome_projeto']
    descricao_projeto = request.form['descricao_projeto']
    usuario_id = session['usuario_id']

    projeto = ComandosProjeto.criar_projeto(nome_projeto, usuario_id)

    if projeto:
        if descricao_projeto:
            projeto.set_descricao_projeto(descricao_projeto)
        return redirect(url_for('index'))
    return redirect(url_for('index'))


@app.route('/alterar_projeto/<int:projeto_id>', methods=['POST'])
def alterar_projeto(projeto_id):
    if not VerificarPermissoes.verificar_sessao():
        return redirect(url_for('index'))

    if not VerificarPermissoes.verificar_permissao_projeto(projeto_id):
        return redirect(url_for('index'))

    novo_nome_projeto = request.form['nome_projeto']
    nova_descricao_projeto = request.form['descricao_projeto']

    ComandosProjeto.alterar_projeto(projeto_id, novo_nome_projeto, nova_descricao_projeto)

    proxima_url = request.referrer
    return redirect(proxima_url or url_for('index'))


@app.route('/excluir_projeto/<int:projeto_id>', methods=['POST'])
def excluir_projeto(projeto_id):
    if not VerificarPermissoes.verificar_sessao():
        return redirect(url_for('index'))

    if not VerificarPermissoes.verificar_permissao_projeto(projeto_id):
        return redirect(url_for('index'))

    usuario_id = session['usuario_id']
    senha_usuario = request.form['senha_usuario']

    if ComandosUsuario.verificar_senha(usuario_id, senha_usuario):
        ComandosProjeto.excluir_projeto(projeto_id)
        return redirect(url_for('index'))

    proxima_url = request.referrer
    return redirect(proxima_url or url_for('index'))


@app.route('/criar_tarefa/<int:projeto_id>', methods=['POST'])
def criar_tarefa(projeto_id):
    if not VerificarPermissoes.verificar_sessao():
        return redirect(url_for('index'))

    if not VerificarPermissoes.verificar_permissao_projeto(projeto_id):
        return redirect(url_for('index'))

    nome_tarefa = request.form['nome_tarefa']
    ComandosTarefa.criar_tarefa(nome_tarefa, projeto_id)

    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/alterar_tarefa/<int:tarefa_id>', methods=['POST'])
def alterar_tarefa(tarefa_id):
    if not VerificarPermissoes.verificar_sessao():
        return redirect(url_for('index'))

    if not VerificarPermissoes.verificar_permissao_tarefa(tarefa_id):
        return redirect(url_for('index'))

    novo_nome_tarefa = request.form['novo_nome_tarefa']
    novo_status = request.form['novo_status']
    nova_data_entrega = request.form['nova_data_entrega']

    if not nova_data_entrega:
        nova_data_entrega = None

    ComandosTarefa.alterar_tarefa(tarefa_id, novo_nome_tarefa, novo_status, nova_data_entrega)
    tarefa = Tarefa.query.get(tarefa_id)
    return redirect(url_for('projeto_especifico', projeto_id=tarefa.projeto_id))


@app.route('/excluir_tarefa/<int:tarefa_id>', methods=['POST'])
def excluir_tarefa(tarefa_id):
    if not VerificarPermissoes.verificar_sessao():
        return redirect(url_for('index'))

    if not VerificarPermissoes.verificar_permissao_tarefa(tarefa_id):
        return redirect(url_for('index'))

    tarefa = Tarefa.query.get(tarefa_id)

    ComandosTarefa.excluir_tarefa(tarefa_id)
    return redirect(url_for('projeto_especifico', projeto_id=tarefa.projeto_id))


@app.route('/projeto/<int:projeto_id>/excluir_tarefas_selecionadas', methods=['POST'])
def excluir_tarefas_selecionadas(projeto_id):
    if not VerificarPermissoes.verificar_sessao():
        return redirect(url_for('index'))

    tarefas_selecionadas = request.form.getlist('tarefas_selecionadas[]')

    if len(tarefas_selecionadas) > 0:
        # Instancia do objeto modo_loop
        modo_loop = VerificadorLoop()

        # Inicia o 'modo loop' para evitar passar vários flashes por conta do FOR
        modo_loop.iniciar_loop()

        for tarefa_id in tarefas_selecionadas:
            ComandosTarefa.excluir_tarefa(tarefa_id)
        flash('Tarefas selecionadas excluídas com sucesso!', 'success')

        # Finaliza o modo loop
        modo_loop.finalizar_loop()
    else:
        flash('Algo deu errado', 'warning')
    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/projeto/<int:projeto_id>/reescrever_descricao', methods=['GET', 'POST'])
def reescrever_descricao(projeto_id):
    if request.method == 'POST':
        if not VerificarPermissoes.verificar_sessao():
            return redirect(url_for('index'))

        nome_projeto, descricao_projeto, lista_tarefas = ComandosProjeto.coletar_dados(projeto_id)

        nova_descricao_sugerida = ChatGPTService.sugerir_descricao(descricao_projeto, nome_projeto)

        flash(nova_descricao_sugerida, 'info')
        return render_template('projeto_especifico.html', projeto=Projeto.query.get(projeto_id),
                               nova_descricao_sugerida=nova_descricao_sugerida)
    else:
        flash('Algo deu errado ao carregar a pagina!', 'danger')
        return redirect(url_for('index'))


@app.route('/projeto/<int:projeto_id>/adicionar_descricao_sugerida/<string:nova_descricao_sugerida>', methods=['POST'])
def adicionar_descricao_sugerida(projeto_id, nova_descricao_sugerida):
    if not VerificarPermissoes.verificar_sessao():
        return redirect(url_for('index'))

    ComandosProjeto.alterar_projeto(projeto_id, None, nova_descricao_sugerida)
    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/projeto/<int:projeto_id>/sugerir_titulo', methods=['GET', 'POST'])
def sugerir_titulo(projeto_id):
    if request.method == 'POST':
        if not VerificarPermissoes.verificar_sessao():
            return redirect(url_for('index'))

        breve_drescricao = request.form['nova_descricao_modelo']

        if not breve_drescricao:
            flash('Algo deu errado!', 'warning')
            return redirect(url_for('projeto_especifico', projeto_id=projeto_id))

        novo_titulo = ChatGPTService.sugerir_titulo(breve_drescricao)

        flash(novo_titulo, 'info')
        return render_template('projeto_especifico.html', projeto=Projeto.query.get(projeto_id),
                               novo_titulo_sugerido=novo_titulo)
    else:
        flash('Algo deu errado ao carregar a pagina!', 'danger')
        return redirect(url_for('index'))


@app.route('/projeto/<int:projeto_id>/adicionar_titulo_sugerido/<string:novo_titulo_sugerido>', methods=['POST'])
def adicionar_titulo_sugerido(projeto_id, novo_titulo_sugerido):
    if not VerificarPermissoes.verificar_sessao():
        return redirect(url_for('index'))

    ComandosProjeto.alterar_projeto(projeto_id, novo_titulo_sugerido, None)

    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/projeto/<int:projeto_id>/sugerir_taferas', methods=['GET', 'POST'])
def sugerir_taferas(projeto_id):
    if request.method == 'POST':
        if not VerificarPermissoes.verificar_sessao():
            return redirect(url_for('index'))

        nome_projeto, descricao_projeto, projeto_tarefas = ComandosProjeto.coletar_dados(projeto_id)

        sugestao_tarefas = ChatGPTService.sugerir_taferas(nome_projeto, descricao_projeto, projeto_tarefas)

        flash(sugestao_tarefas, 'info')

        sugestao_tarefas = sugestao_tarefas.split(';')

        return render_template('projeto_especifico.html', projeto=Projeto.query.get(projeto_id),
                               sugestao_tarefas=sugestao_tarefas)
    else:
        flash('Algo deu errado ao carregar a pagina!', 'danger')
        return redirect(url_for('index'))


@app.route('/projeto/<int:projeto_id>/adicionar_tarefas_sugeridas', methods=['POST'])
def adicionar_tarefas_sugeridas(projeto_id):
    if not VerificarPermissoes.verificar_sessao():
        return redirect(url_for('index'))

    tarefas_selecionadas = request.form.getlist('tarefas_sugeridas[]')

    # Instancia do objeto modo_loop
    modo_loop = VerificadorLoop()

    # Inicia o 'modo loop' para evitar passar vários flashes por conta do FOR
    modo_loop.iniciar_loop()

    # Adicione as tarefas selecionadas ao projeto
    for tarefa in tarefas_selecionadas:
        ComandosTarefa.criar_tarefa(tarefa, projeto_id)

    # Finaliza o 'modo loop'
    modo_loop.finalizar_loop()

    flash('As tarefas sugeridas foram adicionadas com sucesso!', 'success')
    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/projeto/<int:projeto_id>/avaliar_projeto', methods=['POST'])
def avaliar_projeto(projeto_id):
    if not VerificarPermissoes.verificar_sessao():
        return redirect(url_for('index'))

    nome_projeto, descricao_projeto, projeto_tarefas = ComandosProjeto.coletar_dados(projeto_id)

    avaliacao_projeto = ChatGPTService.avaliar_projeto(nome_projeto, descricao_projeto, projeto_tarefas)

    flash(avaliacao_projeto, 'info')
    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


# Inicializar a base de dados
with app.app_context():
    db.create_all()

# Executar a aplicação
if __name__ == '__main__':
    app.run(debug=True)
