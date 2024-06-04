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
        if ChatGPTService.__instance is None:
            ChatGPTService.__instance = super().__new__(cls)
        return ChatGPTService.__instance

    @staticmethod
    def reescrever_descricao(descricao_projeto, nome_projeto):
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "text"},
            messages=[
                {"role": "system", "content": "Responda como um professor"},
                {"role": "user", "content": 'Crie uma nova descrição para projeto (' + nome_projeto + '). Observação, '
                                            'Lembre-se de manter a escrita breve e direta para destacar os principais '
                                            'pontos do projeto. Observação 2, o projeto ja possui uma descrição ('
                                            + descricao_projeto + '). A use de pase para a sua nova descrição.'}
            ]
        )
        return response.choices[0].message.content

    @staticmethod
    def sugerir_titulo(prompt):
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "text"},
            messages=[
                {"role": "system", "content": "Aja como um professor de português."},
                {"role": "user", "content": 'Qual seria um bom título com base na seguinte descrição. '
                                            'Observação,  limite seu título a apenas algumas palavras'
                                            ' para garantir a concisão:  ' + prompt}
            ]
        )

        return resposta.choices[0].message.content

    @staticmethod
    def sugerir_taferas(nome_projeto, descricao_projeto, tarefas_projeto):
        if len(tarefas_projeto) >= 0:
            tarefas_projeto_string = ', '.join(tarefas_projeto)
        else:
            tarefas_projeto_string = 'None'
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "text"},
            messages=[
                {"role": "system", "content": "Aja como um professor"},
                {"role": "user", "content": 'Quais tarefas seriam boas para se definir no projeto ' + nome_projeto +
                                            ' que tem a seguinte descrição ' + descricao_projeto + '. Observação,'
                                            ' limite suas sugestões em apenas títulos para garantir a concisão.'
                                            ' Observação 2, envie sua resposta separando os títulos com (;). Exemplo, '
                                            ' abelha; mel; urso; .... . Observação 3, o projeto ja tem as seguintes '
                                            'tarefas' + tarefas_projeto_string}
            ]
        )

        return resposta.choices[0].message.content

    @staticmethod
    def avaliar_projeto(nome_projeto, descricao_projeto, tarefas_projeto):
        if len(tarefas_projeto) >= 0:
            tarefas_projeto_string = ', '.join(tarefas_projeto)
        else:
            tarefas_projeto_string = 'None'
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "text"},
            messages=[
                {"role": "system", "content": "Aja como um avaliador de projetos"},
                {"role": "user", "content": 'Avalie o projeto (' + nome_projeto + ') que tem a descrição ('
                                            + descricao_projeto + ') e as tarefas (' + tarefas_projeto_string + ') '
                                            'Se necessário aponte pontos do projeto que possam precisar de melhorias, '
                                            'como um novo titúlo, uma descrição mais concisa ou a criação de possíveis '
                                            'tarefas que seriam uteis para o projeto. Observação, faça essa avaliação'
                                            'de forma objetiva e resumida, evite de passar textos grandes.'}
            ]
        )

        return resposta.choices[0].message.content

    @staticmethod
    def fomatar_avaliacao(prompt):
        resposta = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            response_format={"type": "text"},
            messages=[
                {"role": "system", "content": "Aja como um professor."},
                {"role": "user", "content": 'Formate a avaliação do projeto da seguinte forma. '
                                            'Avaliação sobre o nome do projeto: (coloque aqui a avaliação acerca do '
                                            'nome do projeto);'
                                            ' // Avaliação da descrição do projeto: (coloque aqui a '
                                            'avaliação sobre a descrição do projeto);'
                                            ' // Avaliação sobre as tarefas: (coloque aqui a avaliação'
                                            'sobre as tarefas do projeto).'
                                            ' // Avaliação final: (coloque aqui a avaliação final do projeto)'
                                            ' Aqui esta a avaliação do projeto para você formatar (' + prompt + ')'}
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
        flash('Você se desconectou com sucesso!', 'success')


class ComandosProjeto:
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


class ComandosTarefa:
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


class VerificarPermissoes:
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


@app.route('/sair', methods=['POST'])
def sair():
    ComandosUsuario.deslogar_usuario()
    return redirect(url_for('index'))


@app.route('/mudar_tema_claro', methods=['POST'])
def mudar_tema_claro():
    session['tema'] = 'light'
    proxima_url = request.referrer
    return redirect(proxima_url or url_for('index'))


@app.route('/mudar_tema_escuro', methods=['POST'])
def mudar_tema_escuro():
    session['tema'] = 'dark'
    proxima_url = request.referrer
    return redirect(proxima_url or url_for('index'))


@app.route('/projeto/<int:projeto_id>')
def projeto_especifico(projeto_id):
    if not ('usuario_id' in session):
        flash('Você precisa estar logado para acessar esta página', 'warning')
        return redirect(url_for('index'))

    if not VerificarPermissoes.verificar_permissao_projeto(projeto_id):
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
    projeto = ComandosProjeto.criar_projeto(nome_projeto, usuario_id)
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

    if not VerificarPermissoes.verificar_permissao_projeto(projeto_id):
        return redirect(url_for('index'))

    novo_nome_projeto = request.form['nome_projeto']
    nova_descricao_projeto = request.form['descricao_projeto']

    ComandosProjeto.alterar_projeto(projeto_id, novo_nome_projeto, nova_descricao_projeto)
    proxima_url = request.referrer
    return redirect(proxima_url or url_for('index'))


@app.route('/excluir_projeto/<int:projeto_id>', methods=['POST'])
def excluir_projeto(projeto_id):
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para excluir um projeto', 'warning')
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


@app.route('/criar_tarefa', methods=['POST'])
def criar_tarefa():
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para criar uma tarefa', 'warning')
        return redirect(url_for('index'))

    projeto_id = request.form['projeto_id']
    if not VerificarPermissoes.verificar_permissao_projeto(projeto_id):
        return redirect(url_for('index'))

    nome_tarefa = request.form['nome_tarefa']
    ComandosTarefa.criar_tarefa(nome_tarefa, projeto_id)

    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/alterar_tarefa/<int:tarefa_id>', methods=['POST'])
def alterar_tarefa(tarefa_id):
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para alterar uma tarefa', 'warning')
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
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para excluir uma tarefa', 'warning')
        return redirect(url_for('index'))

    if not VerificarPermissoes.verificar_permissao_tarefa(tarefa_id):
        return redirect(url_for('index'))

    tarefa = Tarefa.query.get(tarefa_id)
    projeto_id = tarefa.projeto_id

    ComandosTarefa.excluir_tarefa(tarefa_id)

    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/projeto/<int:projeto_id>/excluir_tarefas_selecionadas', methods=['POST'])
def excluir_tarefas_selecionadas(projeto_id):
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para excluir tarefas', 'warning')
        return redirect(url_for('index'))

    tarefas_selecionadas = request.form.getlist('tarefas_selecionadas[]')

    if len(tarefas_selecionadas) > 0:
        for tarefa_id in tarefas_selecionadas:
            ComandosTarefa.excluir_tarefa(tarefa_id)
        flash('Tarefas selecionadas excluídas com sucesso!', 'success')
    else:
        flash('Selecione pelo menos uma tarefa', 'warning')
    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/projeto/<int:projeto_id>/reescrever_descricao/<descricao_projeto>/<nome_projeto>', methods=['POST'])
def reescrever_descricao(projeto_id, descricao_projeto, nome_projeto):
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para completar esta ação', 'warning')
        return redirect(url_for('index'))

    nova_descricao_sugerida = ChatGPTService.reescrever_descricao(descricao_projeto, nome_projeto)
    flash(nova_descricao_sugerida, 'info')
    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/projeto/<int:projeto_id>/sugerir_titulo', methods=['POST'])
def sugerir_titulo(projeto_id):
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para completar esta ação', 'warning')
        return redirect(url_for('index'))

    breve_drescricao = request.form['nova_descricao_modelo']
    novo_titulo = ChatGPTService.sugerir_titulo(breve_drescricao)
    flash(novo_titulo, 'info')
    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/projeto/<int:projeto_id>/sugerir_taferas', methods=['POST'])
def sugerir_taferas(projeto_id):
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para completar esta ação', 'warning')
        return redirect(url_for('index'))

    nome_projeto, descricao_projeto, projeto_tarefas = ComandosProjeto.coletar_dados(projeto_id)

    sugestao_tarefas = ChatGPTService.sugerir_taferas(nome_projeto, descricao_projeto, projeto_tarefas)
    flash(sugestao_tarefas, 'info')

    sugestao_tarefas = sugestao_tarefas.split(';')

    return render_template('projeto_especifico.html', projeto=Projeto.query.get(projeto_id),
                           sugestao_tarefas=sugestao_tarefas)


@app.route('/projeto/<int:projeto_id>/adicionar_tarefas_sugeridas', methods=['POST'])
def adicionar_tarefas_sugeridas(projeto_id):
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para adicionar tarefas', 'warning')
        return redirect(url_for('index'))

    tarefas_selecionadas = request.form.getlist('tarefas_sugeridas[]')

    # Adicione as tarefas selecionadas ao projeto
    for tarefa in tarefas_selecionadas:
        ComandosTarefa.criar_tarefa(tarefa, projeto_id)

    flash('Tarefas sugeridas adicionadas com sucesso!', 'success')
    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


@app.route('/projeto/<int:projeto_id>/avaliar_projeto', methods=['POST'])
def avaliar_projeto(projeto_id):
    if 'usuario_id' not in session:
        flash('Você precisa estar logado para completar esta ação', 'warning')
        return redirect(url_for('index'))

    nome_projeto, descricao_projeto, projeto_tarefas = ComandosProjeto.coletar_dados(projeto_id)

    for tarefa in projeto_tarefas:
        projeto_tarefas.append(tarefa.nome_tarefa)

    avaliacao_projeto = ChatGPTService.avaliar_projeto(nome_projeto, descricao_projeto, projeto_tarefas)
    avaliacao_formatada = ChatGPTService.fomatar_avaliacao(avaliacao_projeto)

    flash(avaliacao_formatada, 'info')
    return redirect(url_for('projeto_especifico', projeto_id=projeto_id))


# Inicializar a base de dados
with app.app_context():
    db.create_all()

# Executar a aplicação
if __name__ == '__main__':
    app.run(debug=True)
