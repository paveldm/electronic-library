import os
import sqlite3
from pathlib import Path
from flask import Flask, g, render_template

GENRES = ('Роман', 'Фантастика', 'Детектив', 'Научная литература', 'Учебная литература', 'Другое')
STATUSES = ('Не прочитана', 'Читаю', 'Прочитана')

def get_db():
    if 'db' not in g:
        from flask import current_app
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

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

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host=os.environ.get('HOST', '127.0.0.1'),
            port=int(os.environ.get('PORT', '8000')), debug=False)