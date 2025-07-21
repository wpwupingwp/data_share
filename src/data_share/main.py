import csv
import textwrap
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path
from matplotlib import pyplot as plt

app = Flask(__name__)
app.secret_key = 'labelimage'
table_file = 'user_init_table.csv'

data = dict()
with open(table_file, encoding='utf-8', newline='') as file:
    reader = csv.DictReader(file)
    # username is first column
    assert 'username' in reader.fieldnames
    for row in reader:
        data[row['username']] = dict(row)
print(app.root_path)


def get_pdf_list():
    pdf_dir = Path(app.root_path) / 'pdf'
    if not pdf_dir.exists():
        return []
    else:
        pdf_files =  list(pdf_dir.glob('*.pdf'))
        pdf_files = [i for i in pdf_files if not i.name.startswith('new-')]
        return pdf_files


@app.route('/logout')
def logout():
    """用户登出"""
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in data and data[username]['password'] == password:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="用户名或密码错误")
    return render_template('login.html')

def check_login():
    if 'username' not in session or session['username'] not in data:
        session.pop('username', None)
        return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    check_login()
    return render_template('dashboard.html', 
                           username=session['username'], 
                           userdata=data[session['username']],
                           pdf_files=get_pdf_list())


@app.route('/download_pdf')
def download_pdf():
    check_login()
    username = request.args['username']
    filename = request.args['filename']
    pdf = Path(filename).resolve()

    watermarked_pdf = add_watermark(pdf, username)
    return send_file(
        watermarked_pdf,
        download_name=f"watermarked_{filename}",
        as_attachment=True,
        mimetype='application/pdf'
        )


def generate_watermark(text: str) -> Path:
    wm_file = Path('rl_watermark.pdf').absolute()
    # a4
    fig = plt.figure(1, figsize=(8.27, 11.69), dpi=300)
    wrap_text = textwrap.fill(text, width=60)
    fig.text(0.05, 0.05, wrap_text, rotation=45, alpha=0.2, color=(0, 0.5, 1),
             rasterized=True, font={'size': 100, 'family': 'SimHei'})
    plt.savefig(wm_file, transparent=True)
    return wm_file


def add_watermark(pdf: Path, mark: 'Path or str'):
    # print('Usage: python3 add_watermark.py original.pdf watermark.pdf')
    # print('Or:')
    # print('Usage: python3 add_watermark.py original.pdf watermark_text')
    original = Path(pdf).resolve()
    output = original.parent / ('new-'+original.name)
    if isinstance(mark, Path):
        pass
    else:
        watermark = generate_watermark(mark)

    wm_obj = PdfReader(str(watermark))
    wm_page = wm_obj.pages[0]

    reader = PdfReader(str(original))
    writer = PdfWriter()

    for index in range(len(reader.pages)):
        page = reader.pages[index]
        page.merge_page(wm_page)
        writer.add_page(page)

    with open(output, 'wb') as out:
        writer.write(out)
    watermark.unlink()
    return output


if __name__ == '__main__':
    app.run(debug=True)
