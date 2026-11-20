import os
import sqlite3
from pathlib import Path
from flask import Flask, abort, current_app, g, redirect, render_template, request, url_for

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
    return book, errors

def create_app(test_config=None):
    app = Flask(__name__)
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
                return redirect(url_for('view_book', book_id=cursor.lastrowid))
        return render_template('form.html', book=book, errors=errors, editing=False, genres=GENRES, statuses=STATUSES), (400 if errors else 200)

    @app.get('/books/<int:book_id>')
    def view_book(book_id):
        return render_template('detail.html', book=get_book(book_id))

    return app

app = create_app()
if __name__ == '__main__':
    app.run(host=os.environ.get('HOST', '127.0.0.1'),
            port=int(os.environ.get('PORT', '8000')), debug=False)