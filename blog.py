from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

# Kullanıcı kayıt formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.Length(min=5,max=25,message="5-25 karakter olmalı.")])
    email = StringField("Email",validators=[validators.Email(message="Lütfen geçerli bir email adresi giriniz.")])
    username = StringField("Kullanıcı Adı",validators=[validators.Length(min=5,max=15,message="5-15 karakter olmalı.")])
    password = PasswordField("Şifre",validators=[
        validators.DataRequired(message="Şifre alanı boş geçilemez."),
        validators.EqualTo(fieldname="confirm",message="Şifreniz uyuşmuyor.")
        ])
    confirm = PasswordField("Şifre tekrar")

class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Şifre")

class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.Length(min=5,max=100)])
    content = TextAreaField("Makale İçeriği",validators=[validators.Length(min=10)])


app = Flask(__name__)

app.secret_key = "blog" # flash mesajları için

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "blog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)


@app.route("/")
def index():    
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

# decorator ile kullanıcı giriş kontrolü (sayfa görüntüleme yetkisi)
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın !","danger")
            return redirect(url_for("login"))
    return decorated_function

@app.route("/dashboard")
@login_required # kullanıcı giriş yaptıysa görüntülensin  yerine session da yazabilirdik. 
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "select * from articles where author=%s"
    sonuc = cursor.execute(sorgu,(session["username"],))
    if sonuc>0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles=articles)
    else:
        return render_template("dashboard.html")

@app.route("/addarticle",methods=["GET","POST"])
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        sorgu = "insert into articles(title,author,content) values(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()

        flash("Makale başarıyla eklendi !","success")
        return redirect(url_for("dashboard"))

    return render_template("addarticle.html",form=form)

@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "select * from articles where author=%s and id=%s"
    sonuc = cursor.execute(sorgu,(session["username"],id))
    if sonuc>0:
        sorgu2 = "delete from articles where id=%s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya bu makaleyi silme yetkiniz yok !","danger")
        return redirect(url_for("index"))   

@app.route("/edit/<string:id>",methods=["GET","POST"])
@login_required
def edit(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "select * from articles where id=%s and author=%s"
        sonuc = cursor.execute(sorgu,(id,session["username"]))
        if sonuc==0:
            flash("Böyle bir makale yok veya bu makaleyi düzenleme yetkiniz yok !","danger")
            return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form = ArticleForm()

            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form=form)
    else:
        # POST request
        form = ArticleForm(request.form)
        newTitle=form.title.data
        newContent=form.content.data

        sorgu2="update articles set title=%s,content=%s where id=%s"
        cursor=mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()

        flash("Makale başarıyla güncellendi","success")
        return redirect(url_for("dashboard"))

@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "select * from articles"
    sonuc = cursor.execute(sorgu)
    if sonuc>0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles=articles)
    else:
        return render_template("articles.html")

# makale detay
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "select * from articles where id=%s"
    sonuc = cursor.execute(sorgu,(id,))
    if sonuc>0:
        article = cursor.fetchone()
        return render_template("article.html",article=article)
    else:
        return render_template("article.html")

@app.route("/search",methods=["GET","POST"])
def search():
    if request.method=="GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()
        sorgu = "select * from articles where title like '%"+keyword+"%'"
        sonuc = cursor.execute(sorgu)
        if sonuc == 0:
            flash("Aranan kelimeye uygun makale bulunamadı !","danger")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles=articles)

@app.route("/register",methods=["GET","POST"])
def register():
    form = RegisterForm(request.form) # içindeki verileri al

    if request.method == "POST" and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        sorgu = "insert into users(name,email,username,password) values(%s,%s,%s,%s)"
        cursor.execute(sorgu,(name,email,username,password))
        mysql.connection.commit() # select dışındakiler için
        cursor.close()
        flash("Başarıyla kayıt oldunuz !","success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html",form=form)

@app.route("/login",methods=["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        entered_password = form.password.data

        cursor = mysql.connection.cursor()
        sorgu = "select * from users where username= %s"
        sonuc = cursor.execute(sorgu,(username,))

        if sonuc>0:
            data = cursor.fetchone() # tüm datayı aldık
            real_password = data["password"] # dictteki password alanını real_password e attık
            if sha256_crypt.verify(entered_password,real_password): # realle girilen arasında karşılaştırma, doğrulama
                flash("Başarıyla giriş yaptınız !","success")

                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                flash("Şifrenizi yanlış girdiniz !","danger")
                return redirect(url_for("login"))

        else:
            flash("Böyle bir kullanıcı bulunmuyor !","danger")
            return redirect(url_for("login"))

    return render_template("login.html",form = form)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)