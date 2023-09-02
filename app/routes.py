from datetime import datetime
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from app import app, db
from app.forms import EditProfileForm, EmptyForm, LoginForm, PostForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm
from app.models import Post, User
from werkzeug.urls import url_parse

from app.email import send_password_reset_email

@app.route('/')
@app.route('/index')
@login_required
def index() -> str:
    
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(user_id=current_user.id).paginate(page=page, per_page=app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for(endpoint='index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for(endpoint='index', page=posts.prev_num) if posts.has_prev else None
    
    form = PostForm()
    if form.validate_on_submit():
        return redirect(location=url_for("new_post"))
    return render_template('index.html', title='Home', posts=posts.items, form=form, next_url=next_url, prev_url=prev_url)

@app.before_request
def before_request() -> None:
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/register', methods=['GET', 'POST'])
def register() -> str:
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit(): 
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(message=f'Congratulations, {user.username} | {user.email} is now a registered user!')
        return redirect(url_for(endpoint='login'))
    return render_template(template_name_or_list='register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login() -> str:
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout() -> str:
    logout_user()
    return redirect(url_for('index'))

@app.route('/user/<username>')
@login_required
def user(username: str) -> str:
    user = User.query.filter_by(username=username).first_or_404()
    if user is None:
        flash(message=f"User {username} does not exist!")
        redirect(location=url_for(endpoint='index'))
        
    posts = Post.query.filter_by(user_id=user.id).all()
    follow_unfollow_form = EmptyForm()
    return render_template(template_name_or_list='user.html', user=user, posts=posts, form=follow_unfollow_form)

@app.route('/user/<username>/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile(username: str) -> str:
    user = User.query.filter_by(username=username).first_or_404()
    
    if (user != current_user):
        flash(message=f'You are not authorized to edit this profile!')
        return redirect(url_for(endpoint='user', username=user.username))
    
    form = EditProfileForm(user=user)
    
    if form.validate_on_submit():
        user.about_me = form.about_me.data
        user.username = form.username.data
        db.session.commit()
        flash(message=f'{user.username} | {user.email} - Profile now Updated!')
        return redirect(url_for(endpoint='user', username=user.username))
    elif request.method == 'GET':
        form.username.data = user.username
        form.about_me.data = user.about_me
    return render_template(template_name_or_list='edit_profile.html', form=form)

@app.route('/user/<username>/follow', methods=['POST'])
@login_required
def follow_user(username: str) -> str:
    form = EmptyForm()
    if form.validate_on_submit():
        followeduser = User.query.filter_by(username=username).first_or_404()
        if followeduser is None:
            flash('User {} not found, nothing to follow.'.format(username))
            return redirect(url_for('index'))
        if followeduser == current_user:
            flash('User {} is you, dummy :-)'.format(username))
            return redirect(url_for('user', username=username))
        current_user.follow(followeduser)
        db.session.commit()
        flash('You are following {}!'.format(username))
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))
    
@app.route('/user/<username>/unfollow', methods=['POST'])
@login_required
def unfollow_user(username: str) -> str:
    form = EmptyForm()
    if form.validate_on_submit():
        unfolloweduser = User.query.filter_by(username=username).first_or_404()
        if unfolloweduser is None:
            flash('User {} not found, nothing to unfollow.'.format(username))
            return redirect(url_for('index'))
        if unfolloweduser == current_user:
            flash('User {} is you, dummy :-)'.format(username))
            return redirect(url_for('user', username=username))
        current_user.unfollow(unfolloweduser)
        db.session.commit()
        flash('You have unfollowed user: {} :-('.format(username))
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/post/<int:id>', methods=['GET'])
@login_required
def view_post(id: int) -> str:
    post = Post.query.filter_by(id=id).first_or_404()
    if post is None:
        flash(message=f'Post with {id} does not exist!')
        return redirect(location=url_for(endpoint='index'))
    user = User.query.filter_by(id=post.user_id).first_or_404()
    if user is None:
        flash(message=f'Post with id:{id} does not seem to have a valid user!!!')
        return redirect(location=url_for(endpoint='index'))
    return render_template(template_name_or_list='post_view.html', post=post, user=user)
        
@app.route('/post/new_post', methods=['POST'])
@login_required
def new_post() -> str:
    postbody = request.form['post']
    if postbody == "":
        return redirect(location=url_for(endpoint='index'))
    else:
        post = Post(body=postbody, user_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        return redirect(location=url_for(endpoint='view_post', id=post.id))
    
@app.route('/explore', methods=['GET'])
@login_required
def explore() -> str:
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(page=page, per_page=app.config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for(endpoint='explore', page=posts.next_num) if posts.has_next else None
    prev_url = url_for(endpoint='explore', page=posts.prev_num) if posts.has_prev else None
    return render_template(template_name_or_list="explore.html", posts=posts.items, next_url=next_url, prev_url=prev_url)

@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for(endpoint='index'))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if (user is not None):
            send_password_reset_email(user)
            flash(message=f'An email has been sent to {user.email} with instructions to reset your password.')
            return redirect(url_for(endpoint='login'))
    return render_template('reset_password_request.html', title='Reset Password', form=form)

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token: str):
    if current_user.is_authenticated:
        return redirect(url_for(endpoint='index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for(endpoint='index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(password=form.password.data)
        db.session.commit()
        flash(message=f'Your password has been reset.')
        return redirect(url_for(endpoint='login'))
    return render_template('reset_password.html', form=form)