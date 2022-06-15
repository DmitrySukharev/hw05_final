from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User

LIST_LIMIT = 10


def get_page_obj_paginated(request, post_list, page_list_limit):
    paginator = Paginator(post_list, page_list_limit)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


@cache_page(20, key_prefix='index_page')
def index(request):
    """Главная страница со всеми постами."""
    template = 'posts/index.html'
    title = 'Последние обновления на сайте'
    post_list = Post.objects.select_related('author', 'group').all()
    page_obj = get_page_obj_paginated(request, post_list, LIST_LIMIT)
    context = {
        'title': title,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    """Страница группы со всеми постами."""
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.select_related('author').all()
    page_obj = get_page_obj_paginated(request, post_list, LIST_LIMIT)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    """Страница пользователя с его постами."""
    template = 'posts/profile.html'
    author = User.objects.get(username=username)
    author_post_list = author.posts.select_related('group').all()
    page_obj = get_page_obj_paginated(request, author_post_list, LIST_LIMIT)
    if request.user.is_authenticated:
        following = Follow.objects.filter(
            user=request.user, author=author).exists()
    else:
        following = False
    context = {
        'author': author,
        'page_obj': page_obj,
        'following': following,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    """Страница поста с полной информацией."""
    template = 'posts/post_detail.html'
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm()
    comments = post.comments.select_related('author').all()
    context = {
        'post': post,
        'form': form,
        'comments': comments,
    }
    return render(request, template, context)


@login_required
def post_create(request):
    """Форма создания нового поста."""
    template = 'posts/create_post.html'
    if request.method == 'POST':
        form = PostForm(request.POST, files=request.FILES or None)
        if form.is_valid():
            new_post = form.save(commit=False)
            new_post.author = request.user
            new_post.save()
            return redirect('posts:profile', request.user.username)
        return render(request, template, {'form': form})
    form = PostForm()
    context = {
        'form': form,
    }
    return render(request, template, context)


def post_edit(request, post_id):
    """Форма редактирования существующего поста."""
    template = 'posts/create_post.html'
    post = get_object_or_404(Post, pk=post_id)
    form = PostForm(instance=post)
    context = {
        'form': form,
        'is_edit': True,
        'post_id': post_id,
    }
    if request.method == 'POST':
        form = PostForm(
            request.POST,
            files=request.FILES or None,
            instance=post)
        if form.is_valid():
            form.save()
            return redirect('posts:post_detail', post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id)
    return render(request, template, context)  # if invalid form OR not POST


@login_required
def add_comment(request, post_id):
    """Добавление комментария в POST запросе."""
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = Post.objects.get(id=post_id)
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    """Лента постов авторов, на которых подписан пользователь."""
    template = 'posts/follow.html'
    title = 'Лента постов избранных авторов'
    follows = request.user.follower.all().values_list('author')
    authors = User.objects.filter(id__in=follows)
    post_list = Post.objects.filter(author__in=authors)
    page_obj = get_page_obj_paginated(request, post_list, LIST_LIMIT)
    context = {
        'title': title,
        'page_obj': page_obj,
    }
    return render(request, template, context)


@login_required
def profile_follow(request, username):
    """Подписка на автора."""
    author = User.objects.get(username=username)
    if author == request.user:
        return redirect('posts:profile', username=username)
    following = Follow.objects.filter(
        user=request.user, author=author).exists()
    if not following:
        Follow.objects.create(user=request.user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    """Дизлайк, отписка от автора."""
    author = User.objects.get(username=username)
    follow_object = Follow.objects.get(user=request.user, author=author)
    if follow_object:
        follow_object.delete()
    return redirect('posts:profile', username=username)
