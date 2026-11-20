import os
import secrets
import sqlite3
from pathlib import Path
from flask import Flask, abort, current_app, flash, g, redirect, render_template, request, session, url_for

GENRES = ('Роман', 'Фантастика', 'Детектив', 'Научная литература', 'Учебная литература', 'Другое')
STATUSES = ('Не прочитана', 'Читаю', 'Прочитана')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def get_book(book_id):
    book = get_db().execute('SELECT * FROM books WHERE id = ?', (book_id,)).fetchone()
    if book is None:
        abort(404)
    return book

def read_form():
    fields = ('title', 'author', 'publisher', 'year', 'genre', 'status', 'description')
    book = {name: request.form.get(name, '').strip() for name in fields}
    errors = []
    if not book['title'] or not book['author']:
        errors.append('Заполните название книги и имя автора.')
    if book['genre'] not in GENRES or book['status'] not in STATUSES:
        errors.append('Выберите жанр и статус из списка.')
    if book['year']:
        try:
            year = int(book['year'])
            if not 1 <= year <= 2100:
                raise ValueError
        except ValueError:
            errors.append('Год должен быть целым числом от 1 до 2100.')
    for name, label, limit in (
        ('title', 'Название', 200), ('author', 'Автор', 150),
        ('publisher', 'Издательство', 150), ('description', 'Описание', 3000),
    ):
        if len(book[name]) > limit:
            errors.append(f'{label}: допустимо не более {limit} символов.')
    return book, errors

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY') or secrets.token_hex(32),
        MAX_CONTENT_LENGTH=64 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )
    app.config['DATABASE'] = os.environ.get(
        'DATABASE_PATH', str(Path(app.instance_path) / 'library.db')
    )
    if test_config:
        app.config.update(test_config)
    Path(app.config['DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)

    with app.app_context():
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            publisher TEXT NOT NULL DEFAULT '',
            year INTEGER,
            genre TEXT NOT NULL,
            status TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT ''
        )''')
        db.commit()

    @app.context_processor
    def form_token():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
        return {'csrf_token': session['csrf_token']}

    @app.before_request
    def check_form_token():
        if request.method == 'POST':
            expected = session.get('csrf_token', '')
            received = request.form.get('csrf_token', '')
            if not expected or not secrets.compare_digest(expected.encode(), received.encode()):
                abort(400)

    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', title='Книга или страница не найдена',
                               message='Возможно, запись уже удалена. Вернитесь к списку книг.'), 404

    @app.errorhandler(400)
    def bad_request(error):
        return render_template('error.html', title='Не удалось отправить форму',
                               message='Откройте форму заново и повторите действие.'), 400

    @app.errorhandler(413)
    def too_large(error):
        return render_template('error.html', title='Слишком большой запрос',
                               message='Сократите текст и отправьте форму ещё раз.'), 413

    @app.get('/')
    def index():
        books = get_db().execute('SELECT * FROM books ORDER BY id DESC').fetchall()
        return render_template('index.html', books=books)

    @app.route('/books/new', methods=['GET', 'POST'])
    def create_book():
        book = {'genre': GENRES[0], 'status': STATUSES[0]}
        errors = []
        if request.method == 'POST':
            book, errors = read_form()
            if not errors:
                db = get_db()
                cursor = db.execute(
                    'INSERT INTO books (title, author, publisher, year, genre, status, description) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (book['title'], book['author'], book['publisher'],
                     int(book['year']) if book['year'] else None,
                     book['genre'], book['status'], book['description']),
                )
                db.commit()
                flash('Книга добавлена в библиотеку.')
                return redirect(url_for('view_book', book_id=cursor.lastrowid))
        return render_template('form.html', book=book, errors=errors, editing=False,
                               genres=GENRES, statuses=STATUSES), (400 if errors else 200)

    @app.get('/books/<int:book_id>')
    def view_book(book_id):
        return render_template('detail.html', book=get_book(book_id))

    @app.route('/books/<int:book_id>/edit', methods=['GET', 'POST'])
    def edit_book(book_id):
        book = dict(get_book(book_id))
        errors = []
        if request.method == 'POST':
            book, errors = read_form()
            book['id'] = book_id
            if not errors:
                db = get_db()
                db.execute(
                    'UPDATE books SET title=?, author=?, publisher=?, year=?, genre=?, '
                    'status=?, description=? WHERE id=?',
                    (book['title'], book['author'], book['publisher'],
                     int(book['year']) if book['year'] else None,
                     book['genre'], book['status'], book['description'], book_id),
                )
                db.commit()
                flash('Изменения сохранены.')
                return redirect(url_for('view_book', book_id=book_id))
        return render_template('form.html', book=book, errors=errors, editing=True,
                               genres=GENRES, statuses=STATUSES), (400 if errors else 200)

    @app.route('/books/<int:book_id>/delete', methods=['GET', 'POST'])
    def delete_book(book_id):
        book = get_book(book_id)
        if request.method == 'POST':
            db = get_db()
            db.execute('DELETE FROM books WHERE id=?', (book_id,))
            db.commit()
            flash('Книга удалена из библиотеки.')
            return redirect(url_for('index'))
        return render_template('delete.html', book=book)

    return app

app = create_app()
if __name__ == '__main__':
    app.run(host=os.environ.get('HOST', '127.0.0.1'),
            port=int(os.environ.get('PORT', '8000')), debug=False)